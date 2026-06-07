from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any


def database_path() -> Path:
    configured = os.environ.get("OZON_DASHBOARD_DB")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent.parent / "ozon_dashboard.sqlite3"


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    ensure_schema(connection)
    return connection


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS stores (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            client_id TEXT NOT NULL,
            api_key TEXT NOT NULL,
            platform TEXT NOT NULL DEFAULT 'Ozon',
            status TEXT NOT NULL DEFAULT 'active',
            owner TEXT NOT NULL DEFAULT '真实 API',
            auth_label TEXT NOT NULL,
            created_at TEXT NOT NULL,
            real_bound INTEGER NOT NULL DEFAULT 1,
            verification_error TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS alibaba_sources (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            offer_id TEXT NOT NULL,
            title TEXT NOT NULL,
            shop_name TEXT NOT NULL DEFAULT '',
            ozon_category TEXT NOT NULL DEFAULT '',
            ozon_category_id TEXT NOT NULL DEFAULT '0',
            ozon_type_id TEXT NOT NULL DEFAULT '0',
            ozon_category_confidence REAL NOT NULL DEFAULT 0,
            ozon_category_matched_by TEXT NOT NULL DEFAULT '',
            price_min REAL NOT NULL DEFAULT 0,
            price_max REAL NOT NULL DEFAULT 0,
            images_json TEXT NOT NULL DEFAULT '[]',
            skus_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL,
            error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            title TEXT NOT NULL,
            ru_title TEXT NOT NULL,
            description TEXT NOT NULL,
            sku TEXT NOT NULL,
            category TEXT NOT NULL,
            category_id TEXT NOT NULL,
            type_id TEXT NOT NULL,
            attributes_json TEXT NOT NULL DEFAULT '{}',
            cost_cny REAL NOT NULL,
            suggested_price_rub REAL NOT NULL,
            target_margin REAL NOT NULL,
            validation_status TEXT NOT NULL,
            validation_errors_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES alibaba_sources(id)
        );

        CREATE TABLE IF NOT EXISTS published_products (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            offer_id TEXT NOT NULL,
            ozon_product_id TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL,
            status TEXT NOT NULL,
            import_task_id TEXT NOT NULL DEFAULT '',
            error TEXT NOT NULL DEFAULT '',
            price_rub REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(store_id, offer_id),
            FOREIGN KEY(store_id) REFERENCES stores(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL,
            order_no TEXT NOT NULL,
            status TEXT NOT NULL,
            shipping_status TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            items_json TEXT NOT NULL DEFAULT '[]',
            source TEXT NOT NULL DEFAULT 'local',
            created_at TEXT NOT NULL,
            UNIQUE(store_id, order_no),
            FOREIGN KEY(store_id) REFERENCES stores(id)
        );

        CREATE TABLE IF NOT EXISTS task_logs (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS operation_tasks (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            status TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            current_step TEXT NOT NULL DEFAULT '',
            total_steps INTEGER NOT NULL DEFAULT 0,
            completed_steps INTEGER NOT NULL DEFAULT 0,
            store_id TEXT NOT NULL DEFAULT '',
            store_name TEXT NOT NULL DEFAULT '',
            message TEXT NOT NULL DEFAULT '',
            error TEXT NOT NULL DEFAULT '',
            result_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    store_columns = {row["name"] for row in connection.execute("PRAGMA table_info(stores)").fetchall()}
    if "verification_error" not in store_columns:
        connection.execute("ALTER TABLE stores ADD COLUMN verification_error TEXT NOT NULL DEFAULT ''")
    source_columns = {row["name"] for row in connection.execute("PRAGMA table_info(alibaba_sources)").fetchall()}
    source_migrations = {
        "ozon_category": "ALTER TABLE alibaba_sources ADD COLUMN ozon_category TEXT NOT NULL DEFAULT ''",
        "ozon_category_id": "ALTER TABLE alibaba_sources ADD COLUMN ozon_category_id TEXT NOT NULL DEFAULT '0'",
        "ozon_type_id": "ALTER TABLE alibaba_sources ADD COLUMN ozon_type_id TEXT NOT NULL DEFAULT '0'",
        "ozon_category_confidence": "ALTER TABLE alibaba_sources ADD COLUMN ozon_category_confidence REAL NOT NULL DEFAULT 0",
        "ozon_category_matched_by": "ALTER TABLE alibaba_sources ADD COLUMN ozon_category_matched_by TEXT NOT NULL DEFAULT ''",
    }
    for column, statement in source_migrations.items():
        if column not in source_columns:
            connection.execute(statement)
    connection.commit()


def now_date() -> str:
    return time.strftime("%Y-%m-%d")


def now_stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def make_id(prefix: str) -> str:
    return f"{prefix}-{int(time.time() * 1000)}-{os.urandom(3).hex()}"


def encode_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def decode_json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def row_to_store(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "platform": row["platform"],
        "status": row["status"],
        "owner": row["owner"],
        "authLabel": row["auth_label"],
        "createdAt": row["created_at"],
        "realBound": bool(row["real_bound"]),
        "verificationError": row["verification_error"],
    }


def row_to_source(row: sqlite3.Row) -> dict[str, Any]:
    sku_match = re.search(r"[?&](?:skuId|sku_id|skuid)=(\d+)", row["url"], flags=re.I)
    return {
        "id": row["id"],
        "url": row["url"],
        "offerId": row["offer_id"],
        "skuId": sku_match.group(1) if sku_match else "",
        "title": row["title"],
        "shopName": row["shop_name"],
        "ozonCategory": row["ozon_category"],
        "ozonCategoryId": row["ozon_category_id"],
        "ozonTypeId": row["ozon_type_id"],
        "ozonCategoryConfidence": row["ozon_category_confidence"],
        "ozonCategoryMatchedBy": row["ozon_category_matched_by"],
        "priceMin": row["price_min"],
        "priceMax": row["price_max"],
        "images": decode_json(row["images_json"], []),
        "skus": decode_json(row["skus_json"], []),
        "status": row["status"],
        "error": row["error"],
        "createdAt": row["created_at"],
    }


def row_to_product(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "sourceId": row["source_id"],
        "title": row["title"],
        "ruTitle": row["ru_title"],
        "description": row["description"],
        "sku": row["sku"],
        "category": row["category"],
        "categoryId": row["category_id"],
        "typeId": row["type_id"],
        "attributes": decode_json(row["attributes_json"], {}),
        "costCny": row["cost_cny"],
        "suggestedPriceCny": row["suggested_price_rub"],
        "suggestedPriceRub": row["suggested_price_rub"],
        "targetMargin": row["target_margin"],
        "validationStatus": row["validation_status"],
        "validationErrors": decode_json(row["validation_errors_json"], []),
        "createdAt": row["created_at"],
    }


def row_to_operation_task(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "kind": row["kind"],
        "status": row["status"],
        "progress": row["progress"],
        "currentStep": row["current_step"],
        "totalSteps": row["total_steps"],
        "completedSteps": row["completed_steps"],
        "storeId": row["store_id"],
        "storeName": row["store_name"],
        "message": row["message"],
        "error": row["error"],
        "result": decode_json(row["result_json"], {}),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def reset_database_for_tests() -> None:
    path = database_path()
    if path.exists():
        path.unlink()
    with connect():
        pass
