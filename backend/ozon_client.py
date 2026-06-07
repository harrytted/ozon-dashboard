from __future__ import annotations

import time
from typing import Any

import httpx

OZON_API_HOST = "https://api-seller.ozon.ru"

credential_store: dict[str, dict[str, str]] = {}


def build_ozon_headers(client_id: str, api_key: str) -> dict[str, str]:
    return {
        "Client-Id": str(client_id or "").strip(),
        "Api-Key": str(api_key or "").strip(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def mask_client_id(client_id: str) -> str:
    value = str(client_id or "").strip()
    if len(value) <= 6:
        return value
    return f"{value[:4]}...{value[-4:]}"


def validate_bind_payload(payload: dict[str, Any]) -> dict[str, str]:
    name = str(payload.get("name") or "").strip()
    client_id = str(payload.get("clientId") or "").strip()
    api_key = str(payload.get("apiKey") or "").strip()
    if not name or not client_id or not api_key:
        raise ValueError("请填写店铺名称、Client ID 和 API Key")
    return {"name": name, "client_id": client_id, "api_key": api_key}


def create_bound_store_response(
    *,
    name: str,
    client_id: str,
    api_key: str,
    warehouses: list[dict[str, Any]],
) -> dict[str, Any]:
    warehouse_list = warehouses if isinstance(warehouses, list) else []
    store_id = f"ozon-real-{int(time.time() * 1000)}"
    credential_store[store_id] = {
        "client_id": str(client_id or "").strip(),
        "api_key": str(api_key or "").strip(),
    }
    return {
        "store": {
            "id": store_id,
            "name": str(name or "").strip(),
            "platform": "Ozon",
            "status": "active",
            "owner": "真实 API",
            "authLabel": f"Client ID: {mask_client_id(client_id)} · {len(warehouse_list)} 个仓库",
            "createdAt": time.strftime("%Y-%m-%d"),
            "realBound": True,
        },
        "warehousesCount": len(warehouse_list),
    }


async def call_ozon(client_id: str, api_key: str, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{OZON_API_HOST}{endpoint}",
            headers=build_ozon_headers(client_id, api_key),
            json=body,
        )
    try:
        data = response.json()
    except ValueError:
        data = {"raw": response.text}
    if response.status_code >= 400:
        message = data.get("message") or data.get("error") or f"Ozon API returned {response.status_code}"
        raise RuntimeError(message)
    return data


async def bind_ozon_store(payload: dict[str, Any]) -> dict[str, Any]:
    validated = validate_bind_payload(payload)
    warehouse_response = await list_warehouses(validated["client_id"], validated["api_key"])
    warehouses = warehouse_response.get("result") or warehouse_response.get("warehouses") or []
    return create_bound_store_response(
        name=validated["name"],
        client_id=validated["client_id"],
        api_key=validated["api_key"],
        warehouses=warehouses,
    )


async def list_warehouses(client_id: str, api_key: str) -> dict[str, Any]:
    if str(api_key).startswith("key-") or str(api_key).startswith("demo"):
        return {"warehouses": [{"warehouse_id": 1, "name": "Demo warehouse"}]}
    return await call_ozon(client_id, api_key, "/v2/warehouse/list", {})


async def list_description_category_tree(client_id: str, api_key: str) -> dict[str, Any]:
    if str(api_key).startswith("key-") or str(api_key).startswith("demo"):
        return {"result": []}
    return await call_ozon(client_id, api_key, "/v1/description-category/tree", {"language": "RU"})


OZON_PRICE_CURRENCY = "CNY"
OZON_BRAND_ATTRIBUTE_ID = 31
OZON_TYPE_ATTRIBUTE_ID = 8229
OZON_MODEL_NAME_ATTRIBUTE_ID = 9048
OZON_GENDER_ATTRIBUTE_ID = 9163
OZON_MERGE_CARD_ATTRIBUTE_ID = 8292
OZON_COLOR_ATTRIBUTE_ID = 10096
OZON_COLOR_NAME_ATTRIBUTE_ID = 10097
OZON_MATERIAL_COMPOSITION_ATTRIBUTE_ID = 4604
OZON_RUSSIAN_SIZE_ATTRIBUTE_ID = 4295
OZON_CLOTHING_PACKAGING_TYPE_ATTRIBUTE_ID = 4300
OZON_CARE_ATTRIBUTE_ID = 4655
OZON_HASHTAGS_ATTRIBUTE_ID = 23171
OZON_PACKAGE_QUANTITY_ATTRIBUTE_ID = 9661
OZON_ACCESSORY_SET_CONTENT_ATTRIBUTE_ID = 22272
OZON_COUNTRY_ATTRIBUTE_ID = 4389
OZON_NO_BRAND_VALUE_ID = 126745801
OZON_SCARF_TYPE_VALUE_ID = 93181
OZON_GENDER_FEMALE_VALUE_ID = 22881
OZON_COLOR_MULTICOLOR_VALUE_ID = 369939085
OZON_RUSSIAN_SIZE_UNIVERSAL_VALUE_ID = 35646
OZON_CLOTHING_PACKAGE_VALUE_ID = 44412
OZON_ACCESSORY_SET_SCARF_VALUE_ID = 971419670
OZON_COUNTRY_CHINA_VALUE_ID = 90296


def product_model_name(product: dict[str, Any]) -> str:
    return str(product.get("ruTitle") or product.get("title") or "Ozon product").strip()[:255]


def import_attributes(product: dict[str, Any]) -> list[dict[str, Any]]:
    attributes = list(product.get("ozonAttributes") or [])

    def has_attribute(attribute_id: int) -> bool:
        return any(
            int(attribute.get("id") or attribute.get("attribute_id") or 0) == attribute_id
            for attribute in attributes
            if isinstance(attribute, dict)
        )

    def add_dictionary_attribute(attribute_id: int, value_id: int, value: str) -> None:
        if not has_attribute(attribute_id):
            attributes.append({"id": attribute_id, "values": [{"dictionary_value_id": value_id, "value": value}]})

    def add_text_attribute(attribute_id: int, value: str) -> None:
        next_value = str(value or "").strip()
        if next_value and not has_attribute(attribute_id):
            attributes.append({"id": attribute_id, "values": [{"value": next_value}]})

    if not has_attribute(OZON_MODEL_NAME_ATTRIBUTE_ID):
        attributes.append(
            {
                "id": OZON_MODEL_NAME_ATTRIBUTE_ID,
                "values": [{"value": product_model_name(product)}],
            }
        )
    product_text = " ".join(
        str(product.get(key) or "").lower()
        for key in ("ruTitle", "title", "name", "category")
    )
    is_scarf = (
        str(product.get("typeId") or "") == "93181"
        or str(product.get("category") or "").lower() in {"платок", "шарф", "палантин"}
        or any(marker in product_text for marker in ("платок", "шарф", "косынк"))
    )
    if is_scarf:
        attributes_data = product.get("attributes") if isinstance(product.get("attributes"), dict) else {}
        pieces_count = int(attributes_data.get("bundle_pieces") or 1)
        add_dictionary_attribute(OZON_BRAND_ATTRIBUTE_ID, OZON_NO_BRAND_VALUE_ID, "Нет бренда")
        add_dictionary_attribute(OZON_TYPE_ATTRIBUTE_ID, OZON_SCARF_TYPE_VALUE_ID, "Платок")
        add_dictionary_attribute(OZON_GENDER_ATTRIBUTE_ID, OZON_GENDER_FEMALE_VALUE_ID, "Женский")
        add_dictionary_attribute(OZON_COLOR_ATTRIBUTE_ID, OZON_COLOR_MULTICOLOR_VALUE_ID, "разноцветный")
        add_text_attribute(OZON_COLOR_NAME_ATTRIBUTE_ID, "мультиколор")
        add_dictionary_attribute(OZON_RUSSIAN_SIZE_ATTRIBUTE_ID, OZON_RUSSIAN_SIZE_UNIVERSAL_VALUE_ID, "универсальный")
        add_text_attribute(OZON_MATERIAL_COMPOSITION_ATTRIBUTE_ID, "100% полиэстер")
        add_dictionary_attribute(OZON_CLOTHING_PACKAGING_TYPE_ATTRIBUTE_ID, OZON_CLOTHING_PACKAGE_VALUE_ID, "Пакет")
        add_text_attribute(OZON_PACKAGE_QUANTITY_ATTRIBUTE_ID, str(max(1, pieces_count)))
        add_dictionary_attribute(OZON_ACCESSORY_SET_CONTENT_ATTRIBUTE_ID, OZON_ACCESSORY_SET_SCARF_VALUE_ID, "шейный платок")
        add_text_attribute(
            OZON_CARE_ATTRIBUTE_ID,
            "Бережная ручная стирка при температуре до 30 градусов. Не отбеливать. Сушить в расправленном виде.",
        )
        add_text_attribute(OZON_HASHTAGS_ATTRIBUTE_ID, "#платок #женский_платок #аксессуар #винтаж")
        add_dictionary_attribute(OZON_COUNTRY_ATTRIBUTE_ID, OZON_COUNTRY_CHINA_VALUE_ID, "Китай")
    if is_scarf and not has_attribute(OZON_MERGE_CARD_ATTRIBUTE_ID):
        attributes.append(
            {
                "id": OZON_MERGE_CARD_ATTRIBUTE_ID,
                "values": [{"value": str(product.get("sku") or product.get("ruTitle") or product.get("title") or "unique-card")}],
            }
        )
    return attributes


async def update_product_attributes(
    client_id: str,
    api_key: str,
    *,
    offer_id: str,
    product: dict[str, Any],
) -> dict[str, Any]:
    next_offer_id = str(offer_id or "").strip()
    if not next_offer_id:
        raise ValueError("缺少 Ozon Offer ID")
    attributes = import_attributes(product)
    if not attributes:
        raise ValueError("没有可同步的商品特征")
    if str(api_key).startswith("key-") or str(api_key).startswith("demo"):
        return {"task_id": f"demo-attrs-{int(time.time() * 1000)}"}
    return await call_ozon(
        client_id,
        api_key,
        "/v1/product/attributes/update",
        {"items": [{"offer_id": next_offer_id, "attributes": attributes}]},
    )


def build_product_import_item(product: dict[str, Any], offer_id: str, price_cny: float, stock: int) -> dict[str, Any]:
    return {
        "offer_id": offer_id,
        "name": product["ruTitle"],
        "price": str(round(price_cny)),
        "old_price": str(round(price_cny * 1.18)),
        "currency_code": OZON_PRICE_CURRENCY,
        "description_category_id": int(product.get("categoryId") or 0),
        "type_id": int(product.get("typeId") or 0),
        "images": product.get("images") or [],
        "vat": "0",
        "height": 10,
        "depth": 10,
        "width": 10,
        "dimension_unit": "cm",
        "weight": 200,
        "weight_unit": "g",
        "attributes": import_attributes(product),
        "complex_attributes": [],
        "barcode": "",
        "stock": stock,
    }


def validate_product_for_publish(product: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not product.get("ruTitle"):
        errors.append("缺少俄语标题")
    if not product.get("sku"):
        errors.append("缺少系统 SKU")
    if float(product.get("suggestedPriceRub") or 0) <= 0:
        errors.append("售价必须大于 0")
    if not product.get("category"):
        errors.append("缺少 Ozon 类目")
    if int(product.get("categoryId") or 0) <= 0:
        errors.append("缺少 Ozon 类目 ID")
    if int(product.get("typeId") or 0) <= 0:
        errors.append("缺少 Ozon 类型 ID")
    return errors


async def submit_product_import(
    *,
    client_id: str,
    api_key: str,
    product: dict[str, Any],
    offer_id: str,
    price_cny: float,
    stock: int,
) -> dict[str, Any]:
    if str(api_key).startswith("key-") or str(api_key).startswith("demo"):
        return {
            "result": {
                "task_id": f"demo-import-{int(time.time() * 1000)}",
                "status": "submitted",
            }
        }
    item = build_product_import_item(product, offer_id, price_cny, stock)
    return await call_ozon(client_id, api_key, "/v3/product/import", {"items": [item]})


async def update_product_name(
    *,
    client_id: str,
    api_key: str,
    product: dict[str, Any],
    offer_id: str,
    name: str,
    price_cny: float,
    stock: int,
) -> dict[str, Any]:
    next_product = {**product, "ruTitle": str(name or "").strip()}
    if str(api_key).startswith("key-") or str(api_key).startswith("demo"):
        return {
            "result": {
                "task_id": f"demo-name-{int(time.time() * 1000)}",
                "status": "submitted",
            }
        }
    item = build_product_import_item(next_product, offer_id, price_cny, stock)
    return await call_ozon(client_id, api_key, "/v3/product/import", {"items": [item]})


async def import_product_pictures(
    client_id: str,
    api_key: str,
    *,
    product_id: str,
    images: list[str],
) -> dict[str, Any]:
    if str(api_key).startswith("key-") or str(api_key).startswith("demo"):
        return {"result": {"pictures": [{"product_id": product_id, "images": images, "status": "imported"}]}}
    if not str(product_id or "").strip():
        raise ValueError("缺少 Ozon 商品 ID，无法补图")
    if not images:
        raise ValueError("缺少商品图片，无法补图")
    payload = {
        "pictures": [
            {
                "product_id": int(product_id) if str(product_id).isdigit() else product_id,
                "images": images[:15],
            }
        ]
    }
    return await call_ozon(client_id, api_key, "/v1/product/pictures/import", payload)


async def get_product_import_info(client_id: str, api_key: str, task_id: str) -> dict[str, Any]:
    if str(api_key).startswith("key-") or str(api_key).startswith("demo") or str(task_id).startswith(("demo-import-", "local-")):
        return {
            "result": {
                "status": "imported",
                "items": [{"status": "imported", "errors": []}],
            }
        }
    return await call_ozon(client_id, api_key, "/v1/product/import/info", {"task_id": int(task_id)})


async def list_store_products(client_id: str, api_key: str, limit: int = 100) -> dict[str, Any]:
    if str(api_key).startswith("key-") or str(api_key).startswith("demo"):
        return {
            "result": {
                "items": [
                    {
                        "product_id": int(time.time() * 1000),
                        "offer_id": f"DEMO-OZON-{str(client_id)[-4:]}",
                    }
                ],
                "total": 1,
            }
        }
    return await call_ozon(
        client_id,
        api_key,
        "/v3/product/list",
        {"filter": {"visibility": "ALL"}, "limit": limit, "last_id": ""},
    )


async def list_product_info(client_id: str, api_key: str, *, offer_ids: list[str], product_ids: list[int]) -> dict[str, Any]:
    if str(api_key).startswith("key-") or str(api_key).startswith("demo"):
        return {
            "items": [
                {
                    "id": product_id,
                    "product_id": product_id,
                    "offer_id": offer_ids[index] if index < len(offer_ids) else str(product_id),
                    "name": f"Demo Ozon product {offer_ids[index] if index < len(offer_ids) else product_id}",
                }
                for index, product_id in enumerate(product_ids or [int(time.time() * 1000)])
            ]
        }
    body = product_lookup_body(offer_ids=offer_ids, product_ids=product_ids)
    return await call_ozon(client_id, api_key, "/v3/product/info/list", body)


def product_lookup_body(*, offer_ids: list[str], product_ids: list[int]) -> dict[str, Any]:
    if offer_ids:
        return {"offer_id": offer_ids}
    return {"product_id": product_ids}


async def list_product_prices(client_id: str, api_key: str, *, offer_ids: list[str], product_ids: list[int]) -> dict[str, Any]:
    if str(api_key).startswith("key-") or str(api_key).startswith("demo"):
        return {
            "items": [
                {
                    "product_id": product_id,
                    "offer_id": offer_ids[index] if index < len(offer_ids) else str(product_id),
                    "price": {"price": "999", "currency_code": OZON_PRICE_CURRENCY},
                }
                for index, product_id in enumerate(product_ids or [int(time.time() * 1000)])
            ]
        }
    filter_body = {"offer_id": offer_ids, "visibility": "ALL"} if offer_ids else {"product_id": product_ids, "visibility": "ALL"}
    return await call_ozon(client_id, api_key, "/v5/product/info/prices", {"filter": filter_body, "limit": 100, "last_id": ""})


async def list_product_stocks(client_id: str, api_key: str, *, offer_ids: list[str], product_ids: list[int]) -> dict[str, Any]:
    if str(api_key).startswith("key-") or str(api_key).startswith("demo"):
        return {
            "items": [
                {
                    "product_id": product_id,
                    "offer_id": offer_ids[index] if index < len(offer_ids) else str(product_id),
                    "stocks": [{"present": 7, "reserved": 2}],
                }
                for index, product_id in enumerate(product_ids or [int(time.time() * 1000)])
            ]
        }
    filter_body = {"offer_id": offer_ids, "visibility": "ALL"} if offer_ids else {"product_id": product_ids, "visibility": "ALL"}
    return await call_ozon(client_id, api_key, "/v4/product/info/stocks", {"filter": filter_body, "limit": 100, "last_id": ""})


async def update_product_prices(
    client_id: str,
    api_key: str,
    *,
    offer_id: str,
    product_id: str = "",
    price_cny: float,
    old_price_cny: float | None = None,
    min_price_cny: float | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "price": str(round(float(price_cny), 2)),
        "currency_code": OZON_PRICE_CURRENCY,
    }
    if str(offer_id or "").strip():
        item["offer_id"] = str(offer_id).strip()
    elif str(product_id or "").strip():
        item["product_id"] = int(product_id) if str(product_id).isdigit() else str(product_id).strip()
    else:
        raise ValueError("缺少 Ozon Offer ID 或 Product ID")
    old_price = float(old_price_cny) if old_price_cny is not None else float(price_cny) * 1.18
    if old_price > 0:
        item["old_price"] = str(round(old_price, 2))
    if min_price_cny is not None:
        item["min_price"] = str(round(float(min_price_cny), 2))
    if str(api_key).startswith("key-") or str(api_key).startswith("demo"):
        return {"result": [{"offer_id": offer_id, "updated": True}]}
    response = await call_ozon(client_id, api_key, "/v1/product/import/prices", {"prices": [item]})
    error = price_update_error(response)
    if error:
        raise RuntimeError(error)
    return response


def price_update_error(response: dict[str, Any]) -> str:
    result = response.get("result") if isinstance(response, dict) else None
    items = result if isinstance(result, list) else []
    if isinstance(result, dict) and isinstance(result.get("items"), list):
        items = result["items"]
    for item in items:
        if not isinstance(item, dict):
            continue
        errors = item.get("errors") or item.get("error")
        if not errors:
            continue
        if isinstance(errors, list):
            return "；".join(
                str(error.get("message") or error.get("code") or error)
                for error in errors
                if error
            )
        return str(errors)
    return ""


async def update_product_stocks(
    client_id: str,
    api_key: str,
    *,
    offer_id: str,
    stock: int,
    warehouse_id: int,
) -> dict[str, Any]:
    item = {
        "offer_id": offer_id,
        "stock": int(stock),
        "warehouse_id": int(warehouse_id),
    }
    if str(api_key).startswith("key-") or str(api_key).startswith("demo"):
        return {"result": [{**item, "updated": True, "errors": []}]}
    response = await call_ozon(client_id, api_key, "/v2/products/stocks", {"stocks": [item]})
    error = stock_update_error(response)
    if error:
        raise RuntimeError(error)
    return response


def stock_update_error(response: dict[str, Any]) -> str:
    result = response.get("result") if isinstance(response, dict) else None
    items = result if isinstance(result, list) else []
    if isinstance(result, dict):
        for key in ("items", "stocks"):
            if isinstance(result.get(key), list):
                items = result[key]
                break
    for item in items:
        if not isinstance(item, dict):
            continue
        errors = item.get("errors") or item.get("error")
        if not errors:
            continue
        if isinstance(errors, list):
            return "；".join(
                stock_error_message(error)
                for error in errors
                if error
            )
        return stock_error_message(errors)
    return ""


def stock_error_message(error: Any) -> str:
    if not isinstance(error, dict):
        return str(error)
    code = str(error.get("code") or "").strip()
    message = str(error.get("message") or "").strip()
    if code == "PRODUCT_HAS_NOT_BEEN_TAGGED_YET" or "tags validation failed" in message.lower():
        return "商品还未完成 Ozon 打标/审核，暂不能同步库存；请先同步上架状态，待商品有 Ozon Product ID 后再改库存"
    return message or code or str(error)


async def list_fbs_orders(client_id: str, api_key: str, since: str, to: str) -> dict[str, Any]:
    return await call_ozon(
        client_id,
        api_key,
        "/v3/posting/fbs/list",
        {
            "dir": "ASC",
            "filter": {"since": since, "to": to},
            "limit": 100,
            "offset": 0,
            "with": {"analytics_data": False, "financial_data": False},
        },
    )
