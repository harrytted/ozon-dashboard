from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from . import db
from .ai_normalizer import normalize_with_ai
from .alibaba1688_client import fetch_product_from_url, sellable_skus
from .image_service import ImageSyncError, sync_source_images, upload_source_image_payloads
from .models import (
    BundleProductsRequest,
    Import1688Request,
    NormalizeProductsRequest,
    OzonBindRequest,
    OzonBulkBindRequest,
    PublishProductsRequest,
    Rematch1688CategoriesRequest,
    Update1688SourceRequest,
    UpdateInventoryRequest,
    UpdateProductNameRequest,
    UpdateProductPriceRequest,
    UpdateStoreNameRequest,
)
from .ozon_category_matcher import flatten_ozon_category_tree, match_ozon_category
from .ozon_client import (
    bind_ozon_store,
    create_bound_store_response,
    get_product_import_info,
    import_product_pictures,
    list_warehouses,
    list_product_info,
    list_description_category_tree,
    list_product_prices,
    list_product_stocks,
    list_store_products,
    mask_client_id,
    submit_product_import,
    update_product_attributes,
    update_product_name,
    update_product_prices,
    update_product_stocks,
    validate_bind_payload,
    validate_product_for_publish,
)
from .pricing import calculate_price
from .sku import generate_offer_id


app = FastAPI(title="Ozon Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8088",
        "http://127.0.0.1:8088",
    ],
    allow_credentials=False,
    allow_methods=["POST", "GET", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def create_operation_task(
    *,
    kind: str,
    total_steps: int,
    store_id: str = "",
    store_name: str = "",
    message: str = "排队中",
) -> dict[str, Any]:
    task_id = db.make_id("task")
    now = db.now_stamp()
    with db.connect() as connection:
        connection.execute(
            """
            INSERT INTO operation_tasks
            (id, kind, status, progress, current_step, total_steps, completed_steps,
             store_id, store_name, message, error, result_json, created_at, updated_at)
            VALUES (?, ?, 'queued', 0, '', ?, 0, ?, ?, ?, '', '{}', ?, ?)
            """,
            (task_id, kind, total_steps, store_id, store_name, message, now, now),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM operation_tasks WHERE id = ?", (task_id,)).fetchone()
    return db.row_to_operation_task(row)


def update_operation_task(
    task_id: str,
    *,
    status: str = "running",
    completed_steps: int | None = None,
    total_steps: int | None = None,
    current_step: str | None = None,
    message: str | None = None,
    error: str | None = None,
    result: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    with db.connect() as connection:
        row = connection.execute("SELECT * FROM operation_tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        next_total = int(total_steps if total_steps is not None else row["total_steps"])
        next_completed = int(completed_steps if completed_steps is not None else row["completed_steps"])
        if status == "done":
            progress = 100
        elif next_total > 0:
            progress = min(99, max(int(row["progress"]), int(next_completed / next_total * 100)))
        else:
            progress = int(row["progress"])
        connection.execute(
            """
            UPDATE operation_tasks
            SET status=?, progress=?, current_step=?, total_steps=?, completed_steps=?,
                message=?, error=?, result_json=?, updated_at=?
            WHERE id=?
            """,
            (
                status,
                progress,
                current_step if current_step is not None else row["current_step"],
                next_total,
                next_completed,
                message if message is not None else row["message"],
                error if error is not None else row["error"],
                db.encode_json(result) if result is not None else row["result_json"],
                db.now_stamp(),
                task_id,
            ),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM operation_tasks WHERE id = ?", (task_id,)).fetchone()
    return db.row_to_operation_task(updated)


def fail_operation_task(task_id: str, error: Exception | str) -> dict[str, Any] | None:
    return update_operation_task(
        task_id,
        status="failed",
        message="任务失败",
        error=str(error) or "任务执行失败",
    )


def blocking_publish_errors(errors: list[str] | None) -> list[str]:
    return [
        error for error in (errors or [])
        if "缺少商品图片" not in str(error)
        and "Ozon 会隐藏无图商品" not in str(error)
    ]


def save_store(
    connection: sqlite3.Connection,
    *,
    name: str,
    client_id: str,
    api_key: str,
    owner: str = "真实 API",
    status: str = "active",
    real_bound: bool = True,
    verification_error: str = "",
    warehouses_count: int | None = None,
) -> dict[str, Any]:
    store_id = db.make_id("store")
    if warehouses_count is None:
        suffix = "已保存" if not verification_error else "待验证"
    else:
        suffix = f"{warehouses_count} 个仓库"
    auth_label = f"Client ID: {mask_client_id(client_id)} · {suffix}"
    connection.execute(
        """
        INSERT INTO stores
        (id, name, client_id, api_key, platform, status, owner, auth_label, created_at, real_bound, verification_error)
        VALUES (?, ?, ?, ?, 'Ozon', ?, ?, ?, ?, ?, ?)
        """,
        (
            store_id,
            name,
            client_id,
            api_key,
            status,
            owner,
            auth_label,
            db.now_date(),
            1 if real_bound else 0,
            verification_error,
        ),
    )
    connection.commit()
    row = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
    return db.row_to_store(row)


def is_fallback_1688_title(title: str, offer_id: str) -> bool:
    value = str(title or "").strip()
    return not value or value == f"1688 商品 {offer_id}"


def duplicate_source_url(connection: sqlite3.Connection, url: str) -> str:
    base_url = str(url or "").split("#", 1)[0]
    index = 2
    while True:
        candidate = f"{base_url}#variant-{index}"
        exists = connection.execute("SELECT 1 FROM alibaba_sources WHERE url = ?", (candidate,)).fetchone()
        if not exists:
            return candidate
        index += 1


def ozon_tree_items(response: dict[str, Any]) -> list[dict[str, Any]]:
    result = response.get("result") if isinstance(response, dict) else None
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and isinstance(result.get("children"), list):
        return result["children"]
    if isinstance(response, dict) and isinstance(response.get("items"), list):
        return response["items"]
    return []


async def load_ozon_category_candidates(connection: sqlite3.Connection) -> list[dict[str, str]]:
    store = connection.execute(
        "SELECT * FROM stores WHERE real_bound=1 AND status='active' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if not store:
        return []
    try:
        response = await list_description_category_tree(store["client_id"], store["api_key"])
    except Exception:
        return []
    return flatten_ozon_category_tree(ozon_tree_items(response))


def source_to_match_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "title": row["title"],
        "shop_name": row["shop_name"],
        "shopName": row["shop_name"],
    }


def apply_source_category_match(connection: sqlite3.Connection, source_id: str, match: dict[str, Any]) -> None:
    connection.execute(
        """
        UPDATE alibaba_sources
        SET ozon_category=?, ozon_category_id=?, ozon_type_id=?, ozon_category_confidence=?, ozon_category_matched_by=?
        WHERE id=?
        """,
        (
            match.get("ozon_category", ""),
            str(match.get("ozon_category_id") or "0"),
            str(match.get("ozon_type_id") or "0"),
            float(match.get("ozon_category_confidence") or 0),
            match.get("ozon_category_matched_by", ""),
            source_id,
        ),
    )
    product_rows = connection.execute("SELECT * FROM products WHERE source_id = ?", (source_id,)).fetchall()
    for product_row in product_rows:
        product = db.row_to_product(product_row)
        product.update(
            {
                "category": match.get("ozon_category", product.get("category")),
                "categoryId": str(match.get("ozon_category_id") or "0"),
                "typeId": str(match.get("ozon_type_id") or "0"),
            }
        )
        errors = validate_product_for_publish(product)
        connection.execute(
            """
            UPDATE products
            SET category=?, category_id=?, type_id=?, validation_status=?, validation_errors_json=?
            WHERE id=?
            """,
            (
                product["category"],
                product["categoryId"],
                product["typeId"],
                "ready" if not errors else "needs_review",
                db.encode_json(errors),
                product["id"],
            ),
        )


def save_source(connection: sqlite3.Connection, parsed: dict[str, Any]) -> dict[str, Any]:
    source_id = db.make_id("src")
    source_url = parsed["url"]
    if parsed.get("allow_duplicate_source"):
        source_url = duplicate_source_url(connection, source_url)
    try:
        connection.execute(
            """
            INSERT INTO alibaba_sources
            (id, url, offer_id, title, shop_name, ozon_category, ozon_category_id, ozon_type_id,
             ozon_category_confidence, ozon_category_matched_by, price_min, price_max, images_json, skus_json, status, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                source_url,
                parsed["offer_id"],
                parsed["title"],
                parsed.get("shop_name", ""),
                parsed.get("ozon_category", ""),
                str(parsed.get("ozon_category_id") or "0"),
                str(parsed.get("ozon_type_id") or "0"),
                float(parsed.get("ozon_category_confidence") or 0),
                parsed.get("ozon_category_matched_by", ""),
                float(parsed.get("price_min") or 0),
                float(parsed.get("price_max") or 0),
                db.encode_json(parsed.get("images") or []),
                db.encode_json(parsed.get("skus") or []),
                parsed.get("status") or "parsed",
                parsed.get("error") or "",
                db.now_stamp(),
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        row = connection.execute("SELECT * FROM alibaba_sources WHERE url = ?", (parsed["url"],)).fetchone()
        if row and not is_fallback_1688_title(parsed.get("title", ""), parsed["offer_id"]):
            connection.execute(
                """
                UPDATE alibaba_sources
                SET offer_id = ?, title = ?, shop_name = ?, ozon_category = ?, ozon_category_id = ?, ozon_type_id = ?,
                    ozon_category_confidence = ?, ozon_category_matched_by = ?, price_min = ?, price_max = ?,
                    images_json = ?, skus_json = ?, status = ?, error = ?
                WHERE url = ?
                """,
                (
                    parsed["offer_id"],
                    parsed["title"],
                    parsed.get("shop_name", ""),
                    parsed.get("ozon_category", ""),
                    str(parsed.get("ozon_category_id") or "0"),
                    str(parsed.get("ozon_type_id") or "0"),
                    float(parsed.get("ozon_category_confidence") or 0),
                    parsed.get("ozon_category_matched_by", ""),
                    float(parsed.get("price_min") or 0),
                    float(parsed.get("price_max") or 0),
                    db.encode_json(parsed.get("images") or []),
                    db.encode_json(parsed.get("skus") or []),
                    parsed.get("status") or "parsed",
                    parsed.get("error") or "",
                    parsed["url"],
                ),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM alibaba_sources WHERE url = ?", (parsed["url"],)).fetchone()
        return db.row_to_source(row)
    row = connection.execute("SELECT * FROM alibaba_sources WHERE id = ?", (source_id,)).fetchone()
    return db.row_to_source(row)


def load_source(connection: sqlite3.Connection, source_id: str) -> dict[str, Any] | None:
    row = connection.execute("SELECT * FROM alibaba_sources WHERE id = ?", (source_id,)).fetchone()
    return db.row_to_source(row) if row else None


def save_product(connection: sqlite3.Connection, source: dict[str, Any], normalized: Any, request: NormalizeProductsRequest) -> dict[str, Any]:
    existing_row = connection.execute(
        "SELECT * FROM products WHERE source_id = ? ORDER BY created_at, id LIMIT 1",
        (source["id"],),
    ).fetchone()
    product_id = existing_row["id"] if existing_row else db.make_id("prod")
    source_skus = sellable_skus(source.get("skus") or [])
    if source_skus != (source.get("skus") or []):
        connection.execute(
            "UPDATE alibaba_sources SET skus_json=? WHERE id=?",
            (db.encode_json(source_skus), source["id"]),
        )
    sku_spec = source_skus[0] if source_skus else {"name": "默认规格", "price": source.get("priceMin") or 0, "stock": 0}
    base_cost = float(source.get("priceMin") or 0)
    if base_cost <= 0:
        base_cost = float(sku_spec.get("price") or 10)
    full_cost_cny = (
        base_cost
        + request.domesticShippingCny
        + request.packagingCny
        + request.warehouseHandlingCny
        + request.crossBorderShippingCny
        + request.bufferCny
    )
    quote = calculate_price(
        cost_cny=full_cost_cny,
        exchange_rate=request.exchangeRate,
        commission_rate=request.commissionRate,
        payment_rate=request.paymentRate,
        ad_rate=request.adRate,
        return_loss_rate=request.returnLossRate,
        target_margin=request.targetMargin,
    )
    sku_value = generate_offer_id("GLOBAL", source["offerId"], sku_spec)
    product_attributes = {**normalized.attributes, "source_sku": sku_spec}
    validation_errors: list[str] = []
    publish_candidate = {
        "ruTitle": normalized.ruTitle,
        "sku": sku_value,
        "suggestedPriceRub": quote.price_cny,
        "category": source.get("ozonCategory") or normalized.category,
        "categoryId": source.get("ozonCategoryId") or normalized.categoryId,
        "typeId": source.get("ozonTypeId") or normalized.typeId,
    }
    validation_errors.extend(validate_product_for_publish(publish_candidate))
    validation_status = "ready" if not validation_errors else "needs_review"
    product_values = (
        source["title"],
        normalized.ruTitle,
        normalized.description,
        sku_value,
        source.get("ozonCategory") or normalized.category,
        source.get("ozonCategoryId") or normalized.categoryId,
        source.get("ozonTypeId") or normalized.typeId,
        db.encode_json(product_attributes),
        full_cost_cny,
        round(quote.price_cny, 2),
        request.targetMargin,
        validation_status,
        db.encode_json(validation_errors),
    )
    if existing_row:
        connection.execute(
            """
            UPDATE products
            SET title=?, ru_title=?, description=?, sku=?, category=?, category_id=?, type_id=?, attributes_json=?,
                cost_cny=?, suggested_price_rub=?, target_margin=?, validation_status=?, validation_errors_json=?
            WHERE id=?
            """,
            (*product_values, product_id),
        )
    else:
        connection.execute(
            """
            INSERT INTO products
            (id, source_id, title, ru_title, description, sku, category, category_id, type_id, attributes_json,
             cost_cny, suggested_price_rub, target_margin, validation_status, validation_errors_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (product_id, source["id"], *product_values, db.now_stamp()),
        )
    connection.commit()
    row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return db.row_to_product(row)


def first_sellable_sku(source: dict[str, Any]) -> dict[str, Any]:
    source_skus = sellable_skus(source.get("skus") or [])
    return source_skus[0] if source_skus else {"name": "默认规格", "price": source.get("priceMin") or 0, "stock": 0}


def source_unit_cost(source: dict[str, Any]) -> float:
    sku_spec = first_sellable_sku(source)
    value = float(source.get("priceMin") or 0)
    if value <= 0:
        value = float(sku_spec.get("price") or 0)
    return value if value > 0 else 10.0


def bundle_category_source(sources: list[dict[str, Any]]) -> dict[str, Any]:
    for source in sources:
        if int(source.get("ozonCategoryId") or 0) > 0 and int(source.get("ozonTypeId") or 0) > 0:
            return source
    return sources[0]


def unique_images(sources: list[dict[str, Any]], limit: int = 8) -> list[str]:
    images: list[str] = []
    seen: set[str] = set()
    for source in sources:
        for image in source.get("images") or []:
            value = str(image or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            images.append(value)
            if len(images) >= limit:
                return images
    return images


def save_bundle_product(
    connection: sqlite3.Connection,
    sources: list[dict[str, Any]],
    request: BundleProductsRequest,
    ozon_candidates: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    if not sources:
        raise ValueError("请先选择 1688 商品源")
    pieces_count = max(1, int(request.piecesCount or len(sources)))
    primary_source = sources[0]
    category_source = bundle_category_source(sources)
    base_goods_cost = sum(source_unit_cost(source) for source in sources)
    if len(sources) == 1 and pieces_count > 1:
        base_goods_cost *= pieces_count
    full_cost_cny = (
        base_goods_cost
        + request.domesticShippingCny
        + request.packagingCny
        + request.warehouseHandlingCny
        + request.crossBorderShippingCny
        + request.bufferCny
    )
    quote = calculate_price(
        cost_cny=full_cost_cny,
        exchange_rate=request.exchangeRate,
        commission_rate=request.commissionRate,
        payment_rate=request.paymentRate,
        ad_rate=request.adRate,
        return_loss_rate=request.returnLossRate,
        target_margin=request.targetMargin,
    )
    bundle_name = str(request.bundleName or "").strip() or f"{pieces_count}件套"
    ru_title = str(request.ruTitle or "").strip() or f"Набор женских платков {pieces_count} шт"
    bundle_match = match_ozon_category({"title": bundle_name, "shop_name": "", "category": ru_title}, ozon_candidates or [])
    category_name = bundle_match.get("ozon_category") or category_source.get("ozonCategory") or "1688采集商品"
    category_id = str(bundle_match.get("ozon_category_id") or category_source.get("ozonCategoryId") or "0")
    type_id = str(bundle_match.get("ozon_type_id") or category_source.get("ozonTypeId") or "0")
    source_summaries = [
        {
            "sourceId": source["id"],
            "offerId": source["offerId"],
            "title": source["title"],
            "url": source["url"],
            "sku": first_sellable_sku(source),
            "unitCostCny": source_unit_cost(source),
        }
        for source in sources
    ]
    bundle_images = unique_images(sources)
    sku_value = generate_offer_id(
        "GLOBAL",
        "BUNDLE-" + "-".join(str(source["offerId"]) for source in sources),
        {"name": bundle_name, "pieces": pieces_count, "sources": [source["offerId"] for source in sources]},
    )
    product_attributes = {
        "bundle": True,
        "bundle_name": bundle_name,
        "bundle_pieces": pieces_count,
        "bundle_sources": source_summaries,
        "bundle_images": bundle_images,
        "source_sku": first_sellable_sku(primary_source),
    }
    description = (
        f"Комплект из {pieces_count} предметов. "
        f"Состав набора: {bundle_name}. "
        "Подходит как платок на голову, шейный платок или аксессуар для сумки. "
        "Перед публикацией проверьте фото комплекта, размеры и состав материала."
    )
    validation_errors: list[str] = []
    publish_candidate = {
        "ruTitle": ru_title,
        "sku": sku_value,
        "suggestedPriceRub": quote.price_cny,
        "category": category_name,
        "categoryId": category_id,
        "typeId": type_id,
    }
    validation_errors.extend(validate_product_for_publish(publish_candidate))
    validation_status = "ready" if not validation_errors else "needs_review"
    product_id = db.make_id("prod")
    connection.execute(
        """
        INSERT INTO products
        (id, source_id, title, ru_title, description, sku, category, category_id, type_id, attributes_json,
         cost_cny, suggested_price_rub, target_margin, validation_status, validation_errors_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_id,
            primary_source["id"],
            bundle_name,
            ru_title,
            description,
            sku_value,
            category_name,
            category_id,
            type_id,
            db.encode_json(product_attributes),
            full_cost_cny,
            round(quote.price_cny, 2),
            request.targetMargin,
            validation_status,
            db.encode_json(validation_errors),
            db.now_stamp(),
        ),
    )
    connection.commit()
    row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return db.row_to_product(row)


def load_product_with_source(connection: sqlite3.Connection, product_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT p.*, s.url AS source_url, s.offer_id AS source_offer_id, s.images_json AS source_images_json
        FROM products p
        JOIN alibaba_sources s ON s.id = p.source_id
        WHERE p.id = ?
        """,
        (product_id,),
    ).fetchone()
    if not row:
        return None
    product = db.row_to_product(row)
    product["sourceUrl"] = row["source_url"]
    product["sourceOfferId"] = row["source_offer_id"]
    product["images"] = product.get("attributes", {}).get("bundle_images") or db.decode_json(row["source_images_json"], [])
    product["ozonAttributes"] = []
    return product


def publish_job_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT pp.*, p.title, s.name AS store_name
        FROM published_products pp
        JOIN products p ON p.id = pp.product_id
        JOIN stores s ON s.id = pp.store_id
        ORDER BY pp.created_at DESC
        """
    ).fetchall()


def row_to_publish_job(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "storeId": row["store_id"],
        "storeName": row["store_name"],
        "productId": row["product_id"],
        "ozonProductId": row["ozon_product_id"],
        "title": row["title"],
        "offerId": row["offer_id"],
        "status": row["status"],
        "importTaskId": row["import_task_id"],
        "error": row["error"],
        "sourceUrl": row["source_url"],
        "priceCny": row["price_rub"],
        "priceRub": row["price_rub"],
        "createdAt": row["created_at"],
    }


def clear_image_errors(error: str) -> str:
    image_markers = ["нет фотографии", "изображ", "фото", "image_absent", "pictures"]
    parts = [part.strip() for part in str(error or "").split("；") if part.strip()]
    kept = [part for part in parts if not any(marker in part.lower() for marker in image_markers)]
    return "；".join(kept)


def has_only_image_errors(error: str) -> bool:
    text = str(error or "").strip()
    if not text:
        return False
    return not clear_image_errors(text)


def resolve_import_status(import_info: dict[str, Any], offer_id: str) -> tuple[str, str]:
    result = import_info.get("result") or import_info
    items = result.get("items") or result.get("products") or []
    matched: dict[str, Any] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        if not item.get("offer_id") or str(item.get("offer_id")) == str(offer_id):
            matched = item
            break
    status_value = str(
        matched.get("status")
        or matched.get("import_status")
        or result.get("status")
        or import_info.get("status")
        or ""
    ).lower()
    error_value = matched.get("error") or matched.get("errors") or result.get("error") or ""
    if isinstance(error_value, list):
        error_value = "；".join(
            (
                f"{item.get('attribute_name')}: {item.get('message') or item.get('description')}"
                if isinstance(item, dict) and item.get("attribute_name")
                else str(item.get("message") or item.get("description") or item.get("code") or item)
                if isinstance(item, dict)
                else str(item)
            )
            for item in error_value
            if item
        )
    error = str(error_value or "")
    if error:
        if has_only_image_errors(error):
            return "needs_images", error
        return "failed", error
    if any(marker in status_value for marker in ["fail", "error", "reject", "declin"]):
        return "failed", error or "Ozon 导入失败"
    if "skip" in status_value:
        if matched.get("product_id") or matched.get("productId") or matched.get("id"):
            return "done", ""
        return "failed", "Ozon 跳过导入且未返回商品 ID"
    if any(marker in status_value for marker in ["success", "imported", "done", "processed", "created"]):
        return "done", ""
    if any(marker in status_value for marker in ["process", "pending", "submitted", "running", "progress"]):
        return "processing", error
    return "submitted", error


def import_info_product_id(import_info: dict[str, Any], offer_id: str) -> str:
    result = import_info.get("result") or import_info
    items = result.get("items") or result.get("products") or []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_offer_id = item.get("offer_id") or item.get("offerId")
        if item_offer_id and str(item_offer_id) != str(offer_id):
            continue
        raw = item.get("product_id") or item.get("productId") or item.get("id") or ""
        return str(raw or "").strip()
    return ""


def ozon_detail_warnings(detail: dict[str, Any]) -> str:
    warnings: list[str] = []
    errors = detail.get("errors") if isinstance(detail, dict) else []
    if isinstance(errors, list):
        for item in errors:
            if not isinstance(item, dict):
                continue
            texts = item.get("texts") if isinstance(item.get("texts"), dict) else {}
            message = texts.get("message") or texts.get("description") or item.get("message") or item.get("code")
            if message:
                warnings.append(str(message))
    stocks = detail.get("stocks") if isinstance(detail, dict) else {}
    has_stock = bool(stocks.get("has_stock")) if isinstance(stocks, dict) else False
    if not has_stock:
        warnings.append("Ozon 当前无库存，商品不会展示销售")
    statuses = detail.get("statuses") if isinstance(detail, dict) else {}
    if isinstance(statuses, dict):
        status_name = statuses.get("status_name") or statuses.get("status_description")
        if status_name:
            warnings.append(str(status_name))
    return "；".join(dict.fromkeys(warnings))


def stable_external_id(prefix: str, *parts: str) -> str:
    encoded = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha1(encoded.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def ozon_items_from_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    result = response.get("result") if isinstance(response, dict) else {}
    if isinstance(result, dict) and isinstance(result.get("items"), list):
        return result["items"]
    if isinstance(response, dict) and isinstance(response.get("items"), list):
        return response["items"]
    return []


def item_key(item: dict[str, Any]) -> str:
    return str(item.get("offer_id") or item.get("offerId") or item.get("product_id") or item.get("productId") or item.get("id") or "").strip()


def int_product_id(item: dict[str, Any]) -> int | None:
    raw = item.get("product_id") or item.get("productId") or item.get("id")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def numeric_price(value: Any) -> float:
    if isinstance(value, dict):
        for key in ("price", "marketing_price", "marketing_seller_price", "old_price"):
            parsed = numeric_price(value.get(key))
            if parsed > 0:
                return parsed
        return 0.0
    try:
        return float(str(value or "0").replace(",", "."))
    except ValueError:
        return 0.0


def stock_total(item: dict[str, Any]) -> int:
    if isinstance(item.get("stocks"), list):
        total = 0
        for stock in item["stocks"]:
            if isinstance(stock, dict):
                total += int(stock.get("present") or stock.get("stock") or 0)
        return total
    try:
        return int(item.get("stock") or item.get("present") or 0)
    except (TypeError, ValueError):
        return 0


def first_warehouse_id(response: dict[str, Any]) -> int | None:
    warehouses = response.get("result") or response.get("warehouses") or []
    if isinstance(warehouses, dict):
        warehouses = warehouses.get("warehouses") or warehouses.get("items") or []
    if not isinstance(warehouses, list):
        return None
    for warehouse in warehouses:
        if not isinstance(warehouse, dict):
            continue
        raw_id = warehouse.get("warehouse_id") or warehouse.get("warehouseId") or warehouse.get("id")
        try:
            warehouse_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if warehouse_id > 0:
            return warehouse_id
    return None


def enrich_ozon_items(base_items: list[dict[str, Any]], detail_items: list[dict[str, Any]], price_items: list[dict[str, Any]], stock_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in base_items:
        key = item_key(item)
        if key:
            merged[key] = dict(item)
    for group in (detail_items, price_items, stock_items):
        for item in group:
            key = item_key(item)
            if not key:
                continue
            merged.setdefault(key, {}).update(item)
    return list(merged.values())


def row_to_store_product(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "storeId": row["store_id"],
        "productId": row["product_id"],
        "ozonProductId": row["ozon_product_id"],
        "title": row["title"],
        "ruTitle": row["ru_title"],
        "category": row["category"],
        "sku": row["sku"],
        "offerId": row["offer_id"],
        "status": row["status"],
        "sourceUrl": row["source_url"],
        "priceCny": row["price_rub"],
        "priceRub": row["price_rub"],
        "stock": row["stock"],
        "importTaskId": row["import_task_id"],
        "error": row["error"],
    }


def save_existing_ozon_product(connection: sqlite3.Connection, *, store_id: str, item: dict[str, Any]) -> dict[str, Any] | None:
    offer_id = str(item.get("offer_id") or item.get("offerId") or item.get("sku") or "").strip()
    ozon_product_id = str(item.get("product_id") or item.get("productId") or "").strip()
    if not offer_id and not ozon_product_id:
        return None
    if not offer_id:
        offer_id = ozon_product_id
    title = str(item.get("name") or item.get("title") or f"Ozon 已有商品 {offer_id}").strip()
    price_cny = numeric_price(item.get("price") or item.get("marketing_price") or item.get("marketing_seller_price"))
    stock = stock_total(item)
    source_id = stable_external_id("ozon-src", store_id, offer_id, ozon_product_id)
    product_id = stable_external_id("ozon-prod", store_id, offer_id, ozon_product_id)
    published_id = stable_external_id("pub", store_id, offer_id)
    now = db.now_stamp()

    connection.execute(
        """
        INSERT OR IGNORE INTO alibaba_sources
        (id, url, offer_id, title, shop_name, price_min, price_max, images_json, skus_json, status, error, created_at)
        VALUES (?, ?, ?, ?, '', 0, 0, '[]', '[]', 'parsed', ?, ?)
        """,
        (source_id, f"ozon://{store_id}/{offer_id}", offer_id, title, "Ozon 已有商品，尚未绑定 1688 来源链接", now),
    )
    connection.execute(
        """
        INSERT INTO products
        (id, source_id, title, ru_title, description, sku, category, category_id, type_id, attributes_json,
         cost_cny, suggested_price_rub, target_margin, validation_status, validation_errors_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Ozon existing', '0', '0', '{}', 0, ?, 0, 'synced', '[]', ?)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            ru_title=excluded.ru_title,
            sku=excluded.sku,
            suggested_price_rub=excluded.suggested_price_rub
        """,
        (product_id, source_id, title, title, "从 Ozon 店铺同步的已有商品。", offer_id, price_cny, now),
    )
    connection.execute(
        """
        INSERT INTO published_products
        (id, store_id, product_id, offer_id, ozon_product_id, source_url, status, import_task_id, error, price_rub, stock, created_at)
        VALUES (?, ?, ?, ?, ?, '', 'synced', '', '', ?, ?, ?)
        ON CONFLICT(store_id, offer_id) DO UPDATE SET
            product_id=excluded.product_id,
            ozon_product_id=excluded.ozon_product_id,
            status='synced',
            error='',
            price_rub=excluded.price_rub,
            stock=excluded.stock,
            created_at=excluded.created_at
        """,
        (published_id, store_id, product_id, offer_id, ozon_product_id, price_cny, stock, now),
    )
    row = connection.execute(
        """
        SELECT pp.*, p.title, p.ru_title, p.category, p.sku
        FROM published_products pp
        JOIN products p ON p.id = pp.product_id
        WHERE pp.store_id = ? AND pp.offer_id = ?
        """,
        (store_id, offer_id),
    ).fetchone()
    return row_to_store_product(row) if row else None


def save_pending_store_from_bind_error(request: OzonBindRequest, message: str) -> dict[str, Any] | JSONResponse:
    try:
        validated = validate_bind_payload(request.model_dump())
    except ValueError as validation_error:
        return JSONResponse(status_code=400, content={"error": str(validation_error)})
    with db.connect() as connection:
        store = save_store(
            connection,
            name=validated["name"],
            client_id=validated["client_id"],
            api_key=validated["api_key"],
            owner="待验证",
            status="warning",
            real_bound=False,
            verification_error=message,
        )
    return {
        "store": store,
        "warehousesCount": 0,
        "warning": f"Ozon 实时验证失败，已保存为待验证店铺：{message}",
    }


def warehouse_count(response: dict[str, Any]) -> int:
    warehouses = response.get("result") or response.get("warehouses") or []
    return len(warehouses) if isinstance(warehouses, list) else 0


async def run_bind_store_task(task_id: str, payload: dict[str, Any]) -> None:
    try:
        update_operation_task(task_id, status="running", completed_steps=0, current_step="校验参数", message="正在校验店铺凭证")
        validated = validate_bind_payload(payload)
        update_operation_task(task_id, completed_steps=1, current_step="验证 Ozon", message=f"正在验证 {validated['name']} 的 Ozon API")
        warehouses = await list_warehouses(validated["client_id"], validated["api_key"])
        with db.connect() as connection:
            update_operation_task(task_id, completed_steps=2, current_step="保存店铺", message="正在保存店铺")
            store = save_store(
                connection,
                name=validated["name"],
                client_id=validated["client_id"],
                api_key=validated["api_key"],
                warehouses_count=warehouse_count(warehouses),
            )
        update_operation_task(
            task_id,
            completed_steps=3,
            current_step="同步商品",
            message="店铺已绑定，正在同步商品",
        )
        with db.connect() as connection:
            connection.execute(
                "UPDATE operation_tasks SET store_id=?, store_name=? WHERE id=?",
                (store["id"], store["name"], task_id),
            )
            connection.commit()
        sync_result = await sync_store_products_data(
            store["id"],
            task_id=task_id,
            progress_offset=3,
            total_steps=8,
        )
        update_operation_task(
            task_id,
            status="done",
            completed_steps=8,
            total_steps=8,
            current_step="完成",
            message=f"店铺已绑定，已同步 {sync_result['synced']} 个商品",
            result={"store": store, "synced": sync_result["synced"], "warnings": sync_result["warnings"]},
        )
    except Exception as error:
        fail_operation_task(task_id, error)


async def run_bulk_bind_task(task_id: str, payload: dict[str, Any]) -> None:
    stores = payload.get("stores") or []
    auto_sync = bool(payload.get("autoSyncProducts"))
    per_store_steps = 8 if auto_sync else 3
    total_steps = max(1, len(stores) * per_store_steps)
    successes: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    completed = 0
    update_operation_task(task_id, status="running", total_steps=total_steps, current_step="开始绑定", message="正在批量绑定 Ozon 店铺")
    for store_input in stores:
        name = str(store_input.get("name") or "").strip()
        try:
            update_operation_task(task_id, completed_steps=completed, current_step="校验参数", message=f"正在校验 {name or 'Ozon 店铺'}")
            validated = validate_bind_payload(store_input)
            completed += 1
            warehouses_count = None
            if payload.get("validateWithOzon"):
                update_operation_task(task_id, completed_steps=completed, current_step="验证 Ozon", message=f"正在验证 {validated['name']}")
                warehouses_count = warehouse_count(await list_warehouses(validated["client_id"], validated["api_key"]))
            completed += 1
            update_operation_task(task_id, completed_steps=completed, current_step="保存店铺", message=f"正在保存 {validated['name']}")
            with db.connect() as connection:
                store = save_store(
                    connection,
                    name=validated["name"],
                    client_id=validated["client_id"],
                    api_key=validated["api_key"],
                    owner=store_input.get("owner") or "真实 API",
                    warehouses_count=warehouses_count,
                )
            completed += 1
            synced = 0
            if auto_sync:
                sync_result = await sync_store_products_data(
                    store["id"],
                    task_id=task_id,
                    progress_offset=completed,
                    total_steps=total_steps,
                )
                synced = sync_result["synced"]
                completed += 5
            successes.append({"store": store, "synced": synced})
            update_operation_task(task_id, completed_steps=completed, current_step="继续下一店铺", message=f"{validated['name']} 已处理")
        except Exception as error:
            failures.append({"storeName": name, "error": str(error)})
            completed += per_store_steps
            update_operation_task(task_id, completed_steps=completed, current_step="继续下一店铺", message=f"{name or '店铺'} 处理失败", error=str(error))
    final_status = "failed" if failures else "done"
    update_operation_task(
        task_id,
        status=final_status,
        completed_steps=completed,
        total_steps=total_steps,
        current_step="完成" if not failures else "部分失败",
        message=f"已绑定 {len(successes)} 个店铺" if not failures else f"已绑定 {len(successes)} 个店铺，{len(failures)} 个失败",
        error="；".join(item["error"] for item in failures),
        result={"stores": successes, "failures": failures, "autoSyncProducts": auto_sync},
    )


async def run_sync_store_products_task(task_id: str, store_id: str) -> None:
    try:
        result = await sync_store_products_data(store_id, task_id=task_id, progress_offset=0, total_steps=5)
        update_operation_task(
            task_id,
            status="done",
            completed_steps=5,
            total_steps=5,
            current_step="完成",
            message=f"已同步 {result['synced']} 个 Ozon 商品",
            result={"store": result["store"], "synced": result["synced"], "warnings": result["warnings"]},
        )
    except Exception as error:
        fail_operation_task(task_id, error)


@app.get("/api/health")
async def health() -> dict[str, str]:
    with db.connect():
        pass
    return {"status": "ok"}


@app.post("/api/ozon/bind", response_model=None)
async def bind_ozon(request: OzonBindRequest) -> Any:
    try:
        result = await bind_ozon_store(request.model_dump())
        with db.connect() as connection:
            store = save_store(
                connection,
                name=result["store"]["name"],
                client_id=request.clientId,
                api_key=request.apiKey,
                warehouses_count=result.get("warehousesCount", 0),
            )
        return {**result, "store": store}
    except ValueError as error:
        return JSONResponse(status_code=400, content={"error": str(error)})
    except RuntimeError as error:
        return save_pending_store_from_bind_error(request, str(error))
    except Exception as error:
        return save_pending_store_from_bind_error(request, str(error) or "Ozon 绑定失败")


@app.post("/api/ozon/bind-task")
async def bind_ozon_task(request: OzonBindRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    task = create_operation_task(
        kind="ozon_bind",
        total_steps=8,
        store_name=request.name,
        message="店铺绑定任务已创建",
    )
    background_tasks.add_task(run_bind_store_task, task["id"], request.model_dump())
    return {"taskId": task["id"], "task": task}


@app.get("/api/ozon/stores")
async def list_ozon_stores() -> dict[str, Any]:
    with db.connect() as connection:
        rows = connection.execute("SELECT * FROM stores ORDER BY created_at DESC, id DESC").fetchall()
    return {"stores": [db.row_to_store(row) for row in rows]}


@app.delete("/api/ozon/stores/{store_id}")
async def delete_ozon_store(store_id: str) -> Any:
    with db.connect() as connection:
        store = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        if not store:
            return JSONResponse(status_code=404, content={"error": "店铺不存在"})
        source_rows = connection.execute(
            "SELECT id FROM alibaba_sources WHERE url LIKE ?",
            (f"ozon://{store_id}/%",),
        ).fetchall()
        source_ids = [row["id"] for row in source_rows]
        if source_ids:
            placeholders = ",".join("?" for _ in source_ids)
            connection.execute(f"DELETE FROM products WHERE source_id IN ({placeholders})", source_ids)
            connection.execute(f"DELETE FROM alibaba_sources WHERE id IN ({placeholders})", source_ids)
        connection.execute("DELETE FROM published_products WHERE store_id = ?", (store_id,))
        connection.execute("DELETE FROM orders WHERE store_id = ?", (store_id,))
        connection.execute("DELETE FROM stores WHERE id = ?", (store_id,))
        connection.commit()
    return {"deleted": True, "storeId": store_id}


@app.post("/api/ozon/stores/{store_id}/name")
async def update_ozon_store_name(store_id: str, request: UpdateStoreNameRequest) -> Any:
    name = str(request.name or "").strip()
    if not name:
        return JSONResponse(status_code=400, content={"error": "请填写店铺名称"})
    if len(name) > 120:
        return JSONResponse(status_code=400, content={"error": "店铺名称不能超过 120 个字符"})
    with db.connect() as connection:
        store = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        if not store:
            return JSONResponse(status_code=404, content={"error": "店铺不存在"})
        connection.execute("UPDATE stores SET name=? WHERE id=?", (name, store_id))
        connection.execute("UPDATE operation_tasks SET store_name=? WHERE store_id=?", (name, store_id))
        connection.commit()
        updated = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
    return {"store": db.row_to_store(updated), "updated": True}


@app.post("/api/ozon/bind-bulk")
async def bind_ozon_bulk(request: OzonBulkBindRequest) -> dict[str, Any]:
    stores = []
    with db.connect() as connection:
        for store_input in request.stores:
            validated = validate_bind_payload(
                {"name": store_input.name, "clientId": store_input.clientId, "apiKey": store_input.apiKey}
            )
            if request.validateWithOzon:
                await bind_ozon_store(
                    {"name": validated["name"], "clientId": validated["client_id"], "apiKey": validated["api_key"]}
                )
            stores.append(
                save_store(
                    connection,
                    name=validated["name"],
                    client_id=validated["client_id"],
                    api_key=validated["api_key"],
                    owner=store_input.owner,
                )
            )
    return {"stores": stores, "bound": len(stores)}


@app.post("/api/ozon/bind-bulk-task")
async def bind_ozon_bulk_task(request: OzonBulkBindRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    per_store_steps = 8 if request.autoSyncProducts else 3
    task = create_operation_task(
        kind="ozon_bind_bulk",
        total_steps=max(1, len(request.stores) * per_store_steps),
        message=f"批量绑定 {len(request.stores)} 个 Ozon 店铺",
    )
    background_tasks.add_task(run_bulk_bind_task, task["id"], request.model_dump())
    return {"taskId": task["id"], "task": task}


@app.get("/api/tasks")
async def list_operation_tasks(limit: int = 30) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit or 30), 100))
    with db.connect() as connection:
        rows = connection.execute(
            "SELECT * FROM operation_tasks ORDER BY updated_at DESC, created_at DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    return {"tasks": [db.row_to_operation_task(row) for row in rows]}


@app.get("/api/tasks/{task_id}")
async def get_operation_task(task_id: str) -> Any:
    with db.connect() as connection:
        row = connection.execute("SELECT * FROM operation_tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "任务不存在"})
    return {"task": db.row_to_operation_task(row)}


@app.post("/api/1688/import-url")
async def import_1688_urls(request: Import1688Request) -> dict[str, Any]:
    sources = []
    with db.connect() as connection:
        ozon_candidates = await load_ozon_category_candidates(connection)
        for url in request.urls:
            try:
                parsed = await fetch_product_from_url(url)
                existing = connection.execute("SELECT 1 FROM alibaba_sources WHERE url = ?", (parsed["url"],)).fetchone()
                if existing:
                    parsed["allow_duplicate_source"] = True
                parsed.update(match_ozon_category(parsed, ozon_candidates))
                source = save_source(connection, parsed)
                if parsed.get("images"):
                    try:
                        source = await sync_source_images(connection, source["id"], manual_urls=parsed.get("images") or [])
                    except ImageSyncError as image_error:
                        connection.execute(
                            "UPDATE alibaba_sources SET images_json='[]', error=? WHERE id=?",
                            (f"图片上传失败：{image_error}", source["id"]),
                        )
                        connection.commit()
                        updated = connection.execute("SELECT * FROM alibaba_sources WHERE id = ?", (source["id"],)).fetchone()
                        source = db.row_to_source(updated)
                sources.append(source)
            except ValueError as error:
                sources.append({"url": url, "status": "failed", "error": str(error)})
    return {"sources": sources, "imported": len([source for source in sources if source.get("status") != "failed"])}


@app.get("/api/1688/sources")
async def list_1688_sources() -> dict[str, Any]:
    with db.connect() as connection:
        rows = connection.execute(
            """
            SELECT * FROM alibaba_sources
            WHERE url LIKE 'http%1688.com%'
            ORDER BY created_at DESC
            """
        ).fetchall()
    return {"sources": [db.row_to_source(row) for row in rows]}


@app.post("/api/1688/rematch-categories")
async def rematch_1688_categories(request: Rematch1688CategoriesRequest) -> dict[str, Any]:
    with db.connect() as connection:
        ozon_candidates = await load_ozon_category_candidates(connection)
        if request.sourceIds:
            placeholders = ",".join("?" for _ in request.sourceIds)
            rows = connection.execute(
                f"SELECT * FROM alibaba_sources WHERE id IN ({placeholders})",
                request.sourceIds,
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM alibaba_sources WHERE url LIKE 'http%' ORDER BY created_at DESC"
            ).fetchall()
        sources = []
        for row in rows:
            match = match_ozon_category(source_to_match_dict(row), ozon_candidates)
            apply_source_category_match(connection, row["id"], match)
            updated = connection.execute("SELECT * FROM alibaba_sources WHERE id = ?", (row["id"],)).fetchone()
            sources.append(db.row_to_source(updated))
        connection.commit()
    matched = len([source for source in sources if int(source.get("ozonTypeId") or 0) > 0])
    return {"sources": sources, "matched": matched, "checked": len(sources)}


@app.post("/api/1688/sources/{source_id}")
async def update_1688_source(source_id: str, request: Update1688SourceRequest) -> Any:
    title = str(request.title or "").strip()
    if not title:
        return JSONResponse(status_code=400, content={"error": "请填写 1688 商品名称"})
    shop_name = str(request.shopName or "").strip()
    price_min = float(request.priceMin or 0)
    price_max = float(request.priceMax or price_min or 0)
    if price_max and price_min and price_max < price_min:
        price_min, price_max = price_max, price_min
    with db.connect() as connection:
        row = connection.execute("SELECT * FROM alibaba_sources WHERE id = ?", (source_id,)).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "1688 采集商品不存在"})
        current = db.row_to_source(row)
        next_price_min = price_min if price_min > 0 else float(current.get("priceMin") or 0)
        next_price_max = price_max if price_max > 0 else float(current.get("priceMax") or next_price_min)
        connection.execute(
            """
            UPDATE alibaba_sources
            SET title=?, shop_name=?, price_min=?, price_max=?, status='parsed', error=''
            WHERE id=?
            """,
            (title, shop_name, next_price_min, next_price_max, source_id),
        )
        connection.execute(
            """
            UPDATE products
            SET title=?
            WHERE source_id=?
              AND id NOT IN (SELECT product_id FROM published_products)
            """,
            (title, source_id),
        )
        try:
            next_images: list[str] = []
            if request.images:
                uploaded_source = await sync_source_images(connection, source_id, manual_urls=request.images[:8])
                next_images.extend(uploaded_source.get("images") or [])
            if request.uploadedImages:
                local_images = await upload_source_image_payloads(
                    request.uploadedImages,
                    current.get("offerId") or source_id,
                    source_id,
                    start_index=len(next_images) + 1,
                )
                next_images.extend(local_images)
            if request.images or request.uploadedImages:
                connection.execute(
                    "UPDATE alibaba_sources SET images_json=?, status='parsed', error='' WHERE id=?",
                    (db.encode_json(next_images[:8]), source_id),
                )
            else:
                connection.execute("UPDATE alibaba_sources SET images_json='[]' WHERE id=?", (source_id,))
        except ImageSyncError as image_error:
            return JSONResponse(status_code=400, content={"error": f"图片上传失败：{image_error}"})
        connection.commit()
        updated = connection.execute("SELECT * FROM alibaba_sources WHERE id = ?", (source_id,)).fetchone()
    return {"source": db.row_to_source(updated)}


@app.post("/api/1688/sources/{source_id}/images/refresh")
async def refresh_1688_source_images(source_id: str) -> Any:
    try:
        with db.connect() as connection:
            source = await sync_source_images(connection, source_id)
        return {"source": source}
    except ImageSyncError as error:
        return JSONResponse(status_code=400, content={"error": f"图片采集/上传失败：{error}"})


@app.get("/api/products")
async def list_products() -> dict[str, Any]:
    with db.connect() as connection:
        rows = connection.execute(
            """
            SELECT p.*, s.url AS source_url, s.offer_id AS source_offer_id
            FROM products p
            JOIN alibaba_sources s ON s.id = p.source_id
            WHERE s.url LIKE 'http%1688.com%'
            ORDER BY p.created_at DESC, p.id DESC
            """
        ).fetchall()
    products: list[dict[str, Any]] = []
    for row in rows:
        product = db.row_to_product(row)
        product["validationErrors"] = blocking_publish_errors(product.get("validationErrors"))
        if not product["validationErrors"] and product.get("validationStatus") == "needs_review":
            product["validationStatus"] = "ready"
        product["sourceUrl"] = row["source_url"]
        product["sourceOfferId"] = row["source_offer_id"]
        products.append(product)
    return {"products": products}


@app.post("/api/products/{product_id}/price")
async def update_catalog_product_price(product_id: str, request: UpdateProductPriceRequest) -> Any:
    price_cny = request.priceCny if request.priceCny is not None else request.priceRub
    if price_cny is None or price_cny <= 0:
        return JSONResponse(status_code=400, content={"error": "请填写大于 0 的价格"})
    with db.connect() as connection:
        row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "商品不存在"})
        remaining_errors = [
            error
            for error in db.decode_json(row["validation_errors_json"], [])
            if "售价" not in str(error)
        ]
        connection.execute(
            """
            UPDATE products
            SET suggested_price_rub=?, validation_status=?, validation_errors_json=?
            WHERE id=?
            """,
            (
                price_cny,
                "ready" if not remaining_errors else "needs_review",
                db.encode_json(remaining_errors),
                product_id,
            ),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return {"product": db.row_to_product(updated)}


@app.delete("/api/1688/sources/{source_id}")
async def delete_1688_source(source_id: str) -> Any:
    with db.connect() as connection:
        source = connection.execute("SELECT * FROM alibaba_sources WHERE id = ?", (source_id,)).fetchone()
        if not source:
            return JSONResponse(status_code=404, content={"error": "1688 采集商品不存在"})
        published_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM published_products pp
            JOIN products p ON p.id = pp.product_id
            WHERE p.source_id = ?
            """,
            (source_id,),
        ).fetchone()["count"]
        if published_count:
            return JSONResponse(status_code=409, content={"error": "该采集商品已有上架记录，请先删除对应上架商品"})
        product_rows = connection.execute("SELECT id FROM products WHERE source_id = ?", (source_id,)).fetchall()
        product_ids = [row["id"] for row in product_rows]
        connection.execute("DELETE FROM products WHERE source_id = ?", (source_id,))
        connection.execute("DELETE FROM alibaba_sources WHERE id = ?", (source_id,))
        connection.commit()
    return {"deleted": True, "sourceId": source_id, "productIds": product_ids}


@app.post("/api/products/normalize")
async def normalize_products(request: NormalizeProductsRequest) -> dict[str, Any]:
    products = []
    with db.connect() as connection:
        for source_id in request.sourceIds:
            source = load_source(connection, source_id)
            if not source:
                continue
            normalized = await normalize_with_ai(source["title"], source)
            products.append(save_product(connection, source, normalized, request))
    return {"products": products, "normalized": len(products)}


@app.post("/api/products/bundle")
async def bundle_products(request: BundleProductsRequest) -> dict[str, Any]:
    with db.connect() as connection:
        sources = [source for source_id in request.sourceIds if (source := load_source(connection, source_id))]
        if not sources:
            return JSONResponse(status_code=400, content={"error": "请先选择 1688 商品源"})
        ozon_candidates = await load_ozon_category_candidates(connection)
        product = save_bundle_product(connection, sources, request, ozon_candidates)
    return {"product": product, "bundled": len(sources)}


@app.post("/api/products/publish")
async def publish_products(request: PublishProductsRequest) -> dict[str, Any]:
    results = []
    submitted = 0
    skipped = 0
    total_steps = max(1, len(request.productIds) * len(request.storeIds))
    task = create_operation_task(
        kind="ozon_product_publish",
        total_steps=total_steps,
        message="发布商品到 Ozon",
    )
    completed_steps = 0
    with db.connect() as connection:
        for product_id in request.productIds:
            product = load_product_with_source(connection, product_id)
            if not product:
                skipped += len(request.storeIds)
                completed_steps += len(request.storeIds)
                update_operation_task(task["id"], completed_steps=completed_steps, current_step="商品不存在，已跳过")
                continue
            for store_id in request.storeIds:
                store_row = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
                if not store_row:
                    skipped += 1
                    results.append({"productId": product_id, "storeId": store_id, "status": "skipped", "error": "店铺不存在"})
                    completed_steps += 1
                    update_operation_task(task["id"], completed_steps=completed_steps, current_step="店铺不存在，已跳过")
                    continue
                offer_id = product["sku"]
                errors = validate_product_for_publish(product)
                if product["validationStatus"] != "ready":
                    errors.extend(blocking_publish_errors(product["validationErrors"]))
                if errors:
                    skipped += 1
                    result = {"productId": product_id, "storeId": store_id, "offerId": offer_id, "status": "skipped", "error": "；".join(errors)}
                    results.append(result)
                    completed_steps += 1
                    update_operation_task(task["id"], completed_steps=completed_steps, current_step=f"{product['title']} 校验未通过")
                    continue
                try:
                    update_operation_task(task["id"], current_step=f"提交 {product['title']} 到 Ozon")
                    ozon_response = await submit_product_import(
                        client_id=store_row["client_id"],
                        api_key=store_row["api_key"],
                        product=product,
                        offer_id=offer_id,
                        price_cny=product.get("suggestedPriceCny") or product["suggestedPriceRub"],
                        stock=request.stock,
                    )
                    import_task_id = str((ozon_response.get("result") or {}).get("task_id") or "")
                    status = "submitted"
                    error = ""
                    submitted += 1
                except Exception as exc:
                    import_task_id = ""
                    status = "failed"
                    error = str(exc)
                    skipped += 1
                published_id = db.make_id("pub")
                connection.execute(
                    """
                    INSERT OR REPLACE INTO published_products
                    (id, store_id, product_id, offer_id, ozon_product_id, source_url, status, import_task_id, error, price_rub, stock, created_at)
                    VALUES (?, ?, ?, ?, COALESCE((SELECT ozon_product_id FROM published_products WHERE store_id=? AND offer_id=?), ''), ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        published_id,
                        store_id,
                        product_id,
                        offer_id,
                        store_id,
                        offer_id,
                        product["sourceUrl"],
                        status,
                        import_task_id,
                        error,
                        product.get("suggestedPriceCny") or product["suggestedPriceRub"],
                        request.stock,
                        db.now_stamp(),
                    ),
                )
                connection.commit()
                completed_steps += 1
                update_operation_task(
                    task["id"],
                    completed_steps=completed_steps,
                    current_step=f"{product['title']} 已提交" if status == "submitted" else f"{product['title']} 发布失败",
                )
                results.append(
                    {
                        "productId": product_id,
                        "storeId": store_id,
                        "offerId": offer_id,
                        "status": status,
                        "importTaskId": import_task_id,
                        "error": error,
                    }
                )
    final_status = "done" if submitted else "failed"
    final_message = f"已提交 {submitted} 个上架任务，跳过 {skipped} 个" if submitted else f"发布失败，跳过 {skipped} 个"
    task = update_operation_task(
        task["id"],
        status=final_status,
        completed_steps=total_steps,
        message=final_message,
        current_step=final_message,
        error="" if submitted else "没有商品提交到 Ozon",
        result={"results": results, "summary": {"submitted": submitted, "skipped": skipped}},
    ) or task
    return {"results": results, "summary": {"submitted": submitted, "skipped": skipped}, "task": task}


@app.get("/api/products/publish-jobs")
async def list_publish_jobs() -> dict[str, Any]:
    with db.connect() as connection:
        rows = publish_job_rows(connection)
    return {"jobs": [row_to_publish_job(row) for row in rows]}


@app.post("/api/products/publish-jobs/sync")
async def sync_publish_jobs() -> dict[str, Any]:
    checked = 0
    updated = 0
    with db.connect() as connection:
        rows = connection.execute(
            """
            SELECT pp.*, s.client_id, s.api_key
            FROM published_products pp
            JOIN stores s ON s.id = pp.store_id
            WHERE pp.import_task_id <> ''
              AND pp.status IN ('submitted', 'processing', 'needs_images', 'failed')
            ORDER BY pp.created_at DESC
            """
        ).fetchall()
        for row in rows:
            checked += 1
            try:
                import_info = await get_product_import_info(
                    row["client_id"],
                    row["api_key"],
                    row["import_task_id"],
                )
                status, error = resolve_import_status(import_info, row["offer_id"])
                ozon_product_id = import_info_product_id(import_info, row["offer_id"]) or row["ozon_product_id"]
                if status == "done" and int(row["stock"] or 0) > 0:
                    try:
                        if not str(ozon_product_id or "").strip():
                            error = "库存同步跳过：商品还未完成 Ozon 打标/审核，暂不能同步库存"
                        else:
                            warehouses = await list_warehouses(row["client_id"], row["api_key"])
                            warehouse_id = first_warehouse_id(warehouses)
                            if warehouse_id is None:
                                error = "库存同步失败：未找到可用 Ozon 仓库"
                            else:
                                await update_product_stocks(
                                    row["client_id"],
                                    row["api_key"],
                                    offer_id=row["offer_id"],
                                    stock=int(row["stock"]),
                                    warehouse_id=warehouse_id,
                                )
                    except Exception as stock_error:
                        error = f"库存同步失败：{stock_error}"
                if status == "done":
                    try:
                        lookup_product_ids = [int(ozon_product_id)] if str(ozon_product_id).isdigit() else []
                        detail_response = await list_product_info(
                            row["client_id"],
                            row["api_key"],
                            offer_ids=[] if lookup_product_ids else [row["offer_id"]],
                            product_ids=lookup_product_ids,
                        )
                        details = ozon_items_from_response(detail_response)
                        detail = details[0] if details else {}
                        detail_product_id = str(detail.get("id") or detail.get("product_id") or detail.get("productId") or "").strip()
                        if detail_product_id:
                            ozon_product_id = detail_product_id
                        detail_warning = ozon_detail_warnings(detail)
                        if detail_warning:
                            error = detail_warning
                    except Exception as detail_error:
                        error = error or f"Ozon 商品已创建，详情读取失败：{detail_error}"
            except Exception as exc:
                status = "processing"
                error = str(exc)
                ozon_product_id = row["ozon_product_id"]
            if status != row["status"] or error != row["error"] or ozon_product_id != row["ozon_product_id"]:
                updated += 1
                connection.execute(
                    """
                    UPDATE published_products
                    SET status = ?, error = ?, ozon_product_id = ?
                    WHERE id = ?
                    """,
                    (status, error, ozon_product_id, row["id"]),
                )
        connection.commit()
        refreshed = publish_job_rows(connection)
    return {"jobs": [row_to_publish_job(row) for row in refreshed], "checked": checked, "updated": updated}


@app.post("/api/products/publish-jobs/{job_id}/images/sync")
async def sync_publish_job_images(job_id: str) -> Any:
    with db.connect() as connection:
        row = connection.execute(
            """
            SELECT pp.*, s.client_id, s.api_key, s.name AS store_name, p.title
            FROM published_products pp
            JOIN stores s ON s.id = pp.store_id
            JOIN products p ON p.id = pp.product_id
            WHERE pp.id = ?
            """,
            (job_id,),
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "上架记录不存在"})
        product = load_product_with_source(connection, row["product_id"])
        images = (product or {}).get("images") or []
        if not images:
            error = "补图失败：本地商品没有图片，请先在 1688 采集商品里补图"
            connection.execute("UPDATE published_products SET error=? WHERE id=?", (error, job_id))
            connection.commit()
            return JSONResponse(status_code=400, content={"error": error})
        ozon_product_id = str(row["ozon_product_id"] or "").strip()
        if not ozon_product_id and row["import_task_id"]:
            try:
                import_info = await get_product_import_info(row["client_id"], row["api_key"], row["import_task_id"])
                ozon_product_id = import_info_product_id(import_info, row["offer_id"])
            except Exception as exc:
                error = f"补图失败：读取 Ozon 商品 ID 失败：{exc}"
                connection.execute("UPDATE published_products SET error=? WHERE id=?", (error, job_id))
                connection.commit()
                return JSONResponse(status_code=400, content={"error": error})
        if not ozon_product_id:
            error = "补图失败：缺少 Ozon 商品 ID，请先同步任务状态"
            connection.execute("UPDATE published_products SET error=? WHERE id=?", (error, job_id))
            connection.commit()
            return JSONResponse(status_code=400, content={"error": error})
        try:
            await import_product_pictures(row["client_id"], row["api_key"], product_id=ozon_product_id, images=images)
        except Exception as exc:
            error = f"补图失败：{exc}"
            connection.execute("UPDATE published_products SET error=?, ozon_product_id=? WHERE id=?", (error, ozon_product_id, job_id))
            connection.commit()
            return JSONResponse(status_code=400, content={"error": error})
        next_error = clear_image_errors(row["error"])
        connection.execute(
            """
            UPDATE published_products
            SET error=?, ozon_product_id=?, status='done'
            WHERE id=?
            """,
            (next_error, ozon_product_id, job_id),
        )
        connection.commit()
        updated = connection.execute(
            """
            SELECT pp.*, s.name AS store_name, p.title
            FROM published_products pp
            JOIN stores s ON s.id = pp.store_id
            JOIN products p ON p.id = pp.product_id
            WHERE pp.id=?
            """,
            (job_id,),
        ).fetchone()
    return {"job": row_to_publish_job(updated)}


@app.post("/api/products/publish-jobs/{job_id}/attributes/sync")
async def sync_publish_job_attributes(job_id: str) -> Any:
    with db.connect() as connection:
        row = connection.execute(
            """
            SELECT pp.*, s.client_id, s.api_key, s.name AS store_name, p.title
            FROM published_products pp
            JOIN stores s ON s.id = pp.store_id
            JOIN products p ON p.id = pp.product_id
            WHERE pp.id = ?
            """,
            (job_id,),
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "上架记录不存在"})
        product = load_product_with_source(connection, row["product_id"])
        if not product:
            error = "补特征失败：本地商品资料不存在"
            connection.execute("UPDATE published_products SET error=? WHERE id=?", (error, job_id))
            connection.commit()
            return JSONResponse(status_code=400, content={"error": error})
        try:
            ozon_response = await update_product_attributes(
                row["client_id"],
                row["api_key"],
                offer_id=row["offer_id"],
                product=product,
            )
        except Exception as exc:
            error = f"补特征失败：{exc}"
            connection.execute("UPDATE published_products SET error=? WHERE id=?", (error, job_id))
            connection.commit()
            return JSONResponse(status_code=400, content={"error": error})
        result = ozon_response.get("result") if isinstance(ozon_response.get("result"), dict) else {}
        import_task_id = str(ozon_response.get("task_id") or result.get("task_id") or row["import_task_id"] or "")
        connection.execute(
            """
            UPDATE published_products
            SET error='', status='submitted', import_task_id=?
            WHERE id=?
            """,
            (import_task_id, job_id),
        )
        connection.commit()
        updated = connection.execute(
            """
            SELECT pp.*, s.name AS store_name, p.title
            FROM published_products pp
            JOIN stores s ON s.id = pp.store_id
            JOIN products p ON p.id = pp.product_id
            WHERE pp.id=?
            """,
            (job_id,),
        ).fetchone()
    return {"job": row_to_publish_job(updated)}


@app.get("/api/stores/{store_id}/products")
async def list_store_published_products(store_id: str) -> dict[str, Any]:
    with db.connect() as connection:
        rows = connection.execute(
            """
            SELECT pp.*, p.title, p.ru_title, p.category, p.sku
            FROM published_products pp
            JOIN products p ON p.id = pp.product_id
            WHERE pp.store_id = ?
            ORDER BY pp.created_at DESC
            """,
            (store_id,),
        ).fetchall()
    return {"products": [row_to_store_product(row) for row in rows]}


@app.delete("/api/stores/{store_id}/products/{offer_id:path}")
async def delete_store_product(store_id: str, offer_id: str) -> Any:
    with db.connect() as connection:
        store = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        if not store:
            return JSONResponse(status_code=404, content={"error": "店铺不存在"})
        row = connection.execute(
            """
            SELECT pp.product_id, p.source_id, s.url AS source_url
            FROM published_products pp
            JOIN products p ON p.id = pp.product_id
            LEFT JOIN alibaba_sources s ON s.id = p.source_id
            WHERE pp.store_id = ? AND pp.offer_id = ?
            """,
            (store_id, offer_id),
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "商品不存在"})
        product_id = row["product_id"]
        source_id = row["source_id"]
        source_url = row["source_url"] or ""
        connection.execute(
            "DELETE FROM published_products WHERE store_id = ? AND offer_id = ?",
            (store_id, offer_id),
        )
        remaining_refs = connection.execute(
            "SELECT COUNT(*) AS count FROM published_products WHERE product_id = ?",
            (product_id,),
        ).fetchone()["count"]
        if remaining_refs == 0:
            connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
            if source_url.startswith(f"ozon://{store_id}/"):
                connection.execute("DELETE FROM alibaba_sources WHERE id = ?", (source_id,))
        connection.commit()
    return {"deleted": True, "storeId": store_id, "offerId": offer_id, "productId": product_id}


async def sync_store_products_data(
    store_id: str,
    *,
    task_id: str | None = None,
    progress_offset: int = 0,
    total_steps: int = 5,
) -> dict[str, Any]:
    def tick(local_step: int, label: str, message: str) -> None:
        if task_id:
            update_operation_task(
                task_id,
                status="running",
                completed_steps=progress_offset + local_step,
                total_steps=total_steps,
                current_step=label,
                message=message,
            )

    with db.connect() as connection:
        store = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        if not store:
            raise ValueError("店铺不存在")
    try:
        tick(0, "读取商品列表", "正在拉取 Ozon 商品列表")
        response = await list_store_products(store["client_id"], store["api_key"])
    except Exception as error:
        message = str(error) or "Ozon 商品同步失败"
        with db.connect() as connection:
            connection.execute(
                "UPDATE stores SET status='warning', verification_error=? WHERE id=?",
                (message, store_id),
            )
            connection.commit()
        raise RuntimeError(message)

    base_items = ozon_items_from_response(response)
    offer_ids = [str(item.get("offer_id") or item.get("offerId") or "").strip() for item in base_items if str(item.get("offer_id") or item.get("offerId") or "").strip()]
    product_ids = [product_id for product_id in (int_product_id(item) for item in base_items) if product_id is not None]
    detail_items: list[dict[str, Any]] = []
    price_items: list[dict[str, Any]] = []
    stock_items: list[dict[str, Any]] = []
    warnings: list[str] = []
    tick(1, "商品列表", f"已读取 {len(base_items)} 个 Ozon 商品")
    if offer_ids or product_ids:
        for step, label, loader in (
            (2, "商品详情", list_product_info),
            (3, "价格", list_product_prices),
            (4, "库存", list_product_stocks),
        ):
            try:
                tick(step - 1, label, f"正在同步{label}")
                detail_response = await loader(store["client_id"], store["api_key"], offer_ids=offer_ids, product_ids=product_ids)
                if label == "商品详情":
                    detail_items = ozon_items_from_response(detail_response)
                elif label == "价格":
                    price_items = ozon_items_from_response(detail_response)
                else:
                    stock_items = ozon_items_from_response(detail_response)
            except Exception as error:
                warnings.append(f"{label}同步失败：{str(error)}")
            tick(step, label, f"{label}同步完成")
    else:
        tick(4, "跳过详情", "店铺暂无商品，跳过详情/价格/库存同步")

    merged_items = enrich_ozon_items(base_items, detail_items, price_items, stock_items)
    synced_products = []
    tick(4, "保存商品", "正在保存同步结果")
    with db.connect() as connection:
        for item in merged_items:
            product = save_existing_ozon_product(connection, store_id=store_id, item=item)
            if product:
                synced_products.append(product)
        verification_error = "；".join(warnings)
        status = "warning" if warnings else "active"
        auth_label = f"Client ID: {mask_client_id(store['client_id'])} · 商品已同步"
        connection.execute(
            "UPDATE stores SET status=?, owner='真实 API', auth_label=?, real_bound=1, verification_error=? WHERE id=?",
            (status, auth_label, verification_error, store_id),
        )
        connection.commit()
        updated_store = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
    tick(5, "保存完成", f"已保存 {len(synced_products)} 个商品")
    return {"products": synced_products, "synced": len(synced_products), "store": db.row_to_store(updated_store), "warnings": warnings}


@app.post("/api/stores/{store_id}/products/sync")
async def sync_store_existing_products(store_id: str) -> Any:
    try:
        return await sync_store_products_data(store_id)
    except ValueError as error:
        return JSONResponse(status_code=404, content={"error": str(error)})
    except Exception as error:
        message = str(error) or "Ozon 商品同步失败"
        with db.connect() as connection:
            updated_store = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        content: dict[str, Any] = {"error": message}
        if updated_store:
            content["store"] = db.row_to_store(updated_store)
        return JSONResponse(status_code=502, content=content)


@app.post("/api/stores/{store_id}/products/sync-task")
async def sync_store_products_task(store_id: str, background_tasks: BackgroundTasks) -> Any:
    with db.connect() as connection:
        store = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not store:
        return JSONResponse(status_code=404, content={"error": "店铺不存在"})
    task = create_operation_task(
        kind="ozon_products_sync",
        total_steps=5,
        store_id=store_id,
        store_name=store["name"],
        message=f"{store['name']} 商品同步任务已创建",
    )
    background_tasks.add_task(run_sync_store_products_task, task["id"], store_id)
    return {"taskId": task["id"], "task": task}


@app.post("/api/stores/{store_id}/products/{offer_id:path}/price")
async def update_store_product_price(store_id: str, offer_id: str, request: UpdateProductPriceRequest) -> Any:
    price_cny = request.priceCny if request.priceCny is not None else request.priceRub
    old_price_cny = request.oldPriceCny if request.oldPriceCny is not None else request.oldPriceRub
    min_price_cny = request.minPriceCny if request.minPriceCny is not None else request.minPriceRub
    if price_cny is None or price_cny <= 0:
        return JSONResponse(status_code=400, content={"error": "价格必须大于 0"})
    with db.connect() as connection:
        store = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        if not store:
            return JSONResponse(status_code=404, content={"error": "店铺不存在"})
        row = connection.execute(
            """
            SELECT pp.*, p.title, p.ru_title, p.category, p.sku
            FROM published_products pp
            JOIN products p ON p.id = pp.product_id
            WHERE pp.store_id = ? AND pp.offer_id = ?
            """,
            (store_id, offer_id),
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "商品不存在"})

    try:
        await update_product_prices(
            store["client_id"],
            store["api_key"],
            offer_id=offer_id,
            price_cny=price_cny,
            old_price_cny=old_price_cny,
            min_price_cny=min_price_cny,
        )
    except Exception as error:
        return JSONResponse(status_code=502, content={"error": str(error) or "Ozon 改价失败"})

    with db.connect() as connection:
        connection.execute(
            "UPDATE published_products SET price_rub=?, error='' WHERE store_id=? AND offer_id=?",
            (price_cny, store_id, offer_id),
        )
        connection.execute(
            """
            UPDATE products
            SET suggested_price_rub=?
            WHERE id=(SELECT product_id FROM published_products WHERE store_id=? AND offer_id=?)
            """,
            (price_cny, store_id, offer_id),
        )
        connection.commit()
        updated = connection.execute(
            """
            SELECT pp.*, p.title, p.ru_title, p.category, p.sku
            FROM published_products pp
            JOIN products p ON p.id = pp.product_id
            WHERE pp.store_id = ? AND pp.offer_id = ?
            """,
            (store_id, offer_id),
        ).fetchone()
    return {"product": row_to_store_product(updated), "updated": True}


def next_stock_value(current_stock: int, mode: str, value: int) -> int:
    numeric_value = max(0, int(value))
    current = max(0, int(current_stock or 0))
    if mode == "set":
        return numeric_value
    if mode == "increase":
        return current + numeric_value
    if mode == "decrease":
        return max(0, current - numeric_value)
    raise ValueError("库存调整方式不正确")


@app.post("/api/products/inventory")
async def update_products_inventory(request: UpdateInventoryRequest) -> Any:
    product_ids = [str(product_id).strip() for product_id in request.productIds if str(product_id).strip()]
    targets = [
        {
            "product_id": str(target.get("productId") or target.get("product_id") or "").strip(),
            "store_id": str(target.get("storeId") or target.get("store_id") or "").strip(),
            "offer_id": str(target.get("offerId") or target.get("offer_id") or "").strip(),
        }
        for target in request.targets
        if isinstance(target, dict)
    ]
    targets = [target for target in targets if target["product_id"] or (target["store_id"] and target["offer_id"])]
    if not product_ids and not targets:
        return JSONResponse(status_code=400, content={"error": "请选择要修改库存的商品"})
    if request.value < 0:
        return JSONResponse(status_code=400, content={"error": "库存数量不能小于 0"})
    try:
        next_stock_value(0, request.mode, request.value)
    except ValueError as error:
        return JSONResponse(status_code=400, content={"error": str(error)})
    with db.connect() as connection:
        row_map: dict[str, sqlite3.Row] = {}
        base_query = """
            SELECT pp.*, p.title, p.ru_title, p.category, p.sku, s.client_id, s.api_key, s.name AS store_name
            FROM published_products pp
            JOIN products p ON p.id = pp.product_id
            JOIN stores s ON s.id = pp.store_id
        """
        for target in targets:
            if target["store_id"] and target["offer_id"]:
                row = connection.execute(
                    base_query + " WHERE pp.store_id=? AND pp.offer_id=?",
                    (target["store_id"], target["offer_id"]),
                ).fetchone()
                if row:
                    row_map[row["id"]] = row
                continue
            if target["product_id"]:
                for row in connection.execute(base_query + " WHERE pp.product_id=?", (target["product_id"],)).fetchall():
                    row_map[row["id"]] = row
        if product_ids and not row_map:
            placeholders = ",".join("?" for _ in product_ids)
            for row in connection.execute(base_query + f" WHERE pp.product_id IN ({placeholders})", product_ids).fetchall():
                row_map[row["id"]] = row
        rows = list(row_map.values())
    if not rows:
        return JSONResponse(status_code=404, content={"error": "未找到已上架的 Ozon 商品，请先同步或上架商品"})

    updated_rows = []
    failures = []
    warehouse_cache: dict[str, int] = {}
    with db.connect() as connection:
        for row in rows:
            stock = next_stock_value(int(row["stock"] or 0), request.mode, int(request.value))
            try:
                if not str(row["ozon_product_id"] or "").strip():
                    raise RuntimeError("商品还未完成 Ozon 打标/审核，暂不能同步库存；请先同步上架状态，待商品有 Ozon Product ID 后再改库存")
                if row["store_id"] not in warehouse_cache:
                    warehouses = await list_warehouses(row["client_id"], row["api_key"])
                    warehouse_id = first_warehouse_id(warehouses)
                    if warehouse_id is None:
                        raise RuntimeError("未找到可用 Ozon 仓库")
                    warehouse_cache[row["store_id"]] = warehouse_id
                await update_product_stocks(
                    row["client_id"],
                    row["api_key"],
                    offer_id=row["offer_id"],
                    stock=stock,
                    warehouse_id=warehouse_cache[row["store_id"]],
                )
                stock_response = await list_product_stocks(
                    row["client_id"],
                    row["api_key"],
                    offer_ids=[row["offer_id"]],
                    product_ids=[],
                )
                stock_items = ozon_items_from_response(stock_response)
                matched_stock_item = next(
                    (
                        item for item in stock_items
                        if str(item.get("offer_id") or item.get("offerId") or "") == str(row["offer_id"])
                    ),
                    stock_items[0] if stock_items else {},
                )
                actual_stock = stock_total(matched_stock_item)
                if actual_stock != stock:
                    raise RuntimeError(f"Ozon 库存读回为 {actual_stock}，目标库存为 {stock}")
                connection.execute(
                    "UPDATE published_products SET stock=?, error='' WHERE id=?",
                    (actual_stock, row["id"]),
                )
            except Exception as exc:
                message = f"库存同步失败：{exc}"
                failures.append({"productId": row["product_id"], "offerId": row["offer_id"], "error": message})
                connection.execute("UPDATE published_products SET error=? WHERE id=?", (message, row["id"]))
        connection.commit()
        refreshed = []
        if rows:
            row_ids = [row["id"] for row in rows]
            refreshed_placeholders = ",".join("?" for _ in row_ids)
            refreshed = connection.execute(
                f"""
            SELECT pp.*, p.title, p.ru_title, p.category, p.sku
            FROM published_products pp
            JOIN products p ON p.id = pp.product_id
            WHERE pp.id IN ({refreshed_placeholders})
            """,
                row_ids,
            ).fetchall()
        updated_rows = [row_to_store_product(row) for row in refreshed]
    status_code = 207 if failures and len(failures) < len(rows) else 200
    if failures and len(failures) == len(rows):
        return JSONResponse(status_code=502, content={"error": "库存同步到 Ozon 失败", "failures": failures, "products": updated_rows})
    return JSONResponse(
        status_code=status_code,
        content={"products": updated_rows, "updated": len(rows) - len(failures), "failed": len(failures), "failures": failures},
    )


@app.post("/api/stores/{store_id}/products/{offer_id:path}/name")
async def update_store_product_name(store_id: str, offer_id: str, request: UpdateProductNameRequest) -> Any:
    name = str(request.name or "").strip()
    if not name:
        return JSONResponse(status_code=400, content={"error": "请填写商品名称"})
    if len(name) > 500:
        return JSONResponse(status_code=400, content={"error": "商品名称不能超过 500 个字符"})
    with db.connect() as connection:
        store = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        if not store:
            return JSONResponse(status_code=404, content={"error": "店铺不存在"})
        row = connection.execute(
            """
            SELECT pp.*, p.title, p.ru_title, p.category, p.sku
            FROM published_products pp
            JOIN products p ON p.id = pp.product_id
            WHERE pp.store_id = ? AND pp.offer_id = ?
            """,
            (store_id, offer_id),
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "商品不存在"})
        product = load_product_with_source(connection, row["product_id"])
        if not product:
            return JSONResponse(status_code=404, content={"error": "本地商品资料不存在"})

    errors = validate_product_for_publish({**product, "ruTitle": name})
    if not product.get("images"):
        errors.append("缺少商品图片")
    if errors:
        return JSONResponse(
            status_code=400,
            content={"error": f"Ozon 改名需要完整商品资料：{'；'.join(errors)}。请先在通用商品库补齐类目、Type ID 和图片。"},
        )

    try:
        ozon_response = await update_product_name(
            client_id=store["client_id"],
            api_key=store["api_key"],
            product=product,
            offer_id=offer_id,
            name=name,
            price_cny=float(row["price_rub"] or product.get("suggestedPriceCny") or product.get("suggestedPriceRub") or 0),
            stock=int(row["stock"] or 0),
        )
    except Exception as error:
        return JSONResponse(status_code=502, content={"error": str(error) or "Ozon 改名失败"})

    import_task_id = str((ozon_response.get("result") or {}).get("task_id") or "")
    with db.connect() as connection:
        connection.execute(
            """
            UPDATE products
            SET title=?, ru_title=?
            WHERE id=(SELECT product_id FROM published_products WHERE store_id=? AND offer_id=?)
            """,
            (name, name, store_id, offer_id),
        )
        connection.execute(
            """
            UPDATE published_products
            SET status='submitted', import_task_id=?, error=''
            WHERE store_id=? AND offer_id=?
            """,
            (import_task_id, store_id, offer_id),
        )
        connection.commit()
        updated = connection.execute(
            """
            SELECT pp.*, p.title, p.ru_title, p.category, p.sku
            FROM published_products pp
            JOIN products p ON p.id = pp.product_id
            WHERE pp.store_id = ? AND pp.offer_id = ?
            """,
            (store_id, offer_id),
        ).fetchone()
    return {"product": row_to_store_product(updated), "updated": True, "importTaskId": import_task_id}


@app.get("/api/stores/{store_id}/orders")
async def list_store_orders(store_id: str) -> dict[str, Any]:
    with db.connect() as connection:
        store = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        if not store:
            return JSONResponse(status_code=404, content={"error": "店铺不存在"})
        rows = connection.execute("SELECT * FROM orders WHERE store_id = ? ORDER BY created_at DESC", (store_id,)).fetchall()
        if not rows:
            order_id = db.make_id("order")
            order_no = f"DEMO-{store_id[-6:]}"
            connection.execute(
                """
                INSERT OR IGNORE INTO orders (id, store_id, order_no, status, shipping_status, amount, items_json, source, created_at)
                VALUES (?, ?, ?, 'awaiting_packaging', 'pending', 0, '[]', 'demo', ?)
                """,
                (order_id, store_id, order_no, db.now_stamp()),
            )
            connection.commit()
            rows = connection.execute("SELECT * FROM orders WHERE store_id = ? ORDER BY created_at DESC", (store_id,)).fetchall()
    return {
        "orders": [
            {
                "id": row["id"],
                "storeId": row["store_id"],
                "orderNo": row["order_no"],
                "status": row["status"],
                "shippingStatus": row["shipping_status"],
                "amount": row["amount"],
                "items": db.decode_json(row["items_json"], []),
                "source": row["source"],
                "createdAt": row["created_at"],
            }
            for row in rows
        ]
    }
