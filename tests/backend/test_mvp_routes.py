import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


class MvpRoutesTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["OZON_DASHBOARD_DB"] = os.path.join(self.tempdir.name, "test.sqlite3")
        from backend import db

        db.reset_database_for_tests()
        from backend.main import app

        self.client = TestClient(app)

    def tearDown(self):
        self.tempdir.cleanup()
        os.environ.pop("OZON_DASHBOARD_DB", None)

    def test_import_url_creates_source_and_normalize_generates_products(self):
        import_response = self.client.post(
            "/api/1688/import-url",
            json={
                "urls": [
                    "https://detail.1688.com/offer/739590664908.html",
                    "https://detail.1688.com/offer/111222333444.html",
                ]
            },
        )
        self.assertEqual(import_response.status_code, 200)
        self.assertEqual(import_response.json()["imported"], 2)

        sources = self.client.get("/api/1688/sources").json()["sources"]
        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0]["status"], "parsed")

        normalize_response = self.client.post(
            "/api/products/normalize",
            json={"sourceIds": [source["id"] for source in sources], "targetMargin": 0.30},
        )
        self.assertEqual(normalize_response.status_code, 200)
        products = normalize_response.json()["products"]
        self.assertEqual(len(products), 2)
        self.assertTrue(products[0]["sku"])
        self.assertGreater(products[0]["suggestedPriceRub"], 0)
        self.assertEqual(products[0]["validationStatus"], "needs_review")
        self.assertIn("缺少 Ozon 类型 ID", products[0]["validationErrors"])

    def test_reimport_url_updates_fallback_title_when_real_title_is_found(self):
        url = "https://detail.1688.com/offer/853346579651.html"
        fallback_source = {
            "offer_id": "853346579651",
            "url": url,
            "title": "1688 商品 853346579651",
            "shop_name": "",
            "price_min": 28.8,
            "price_max": 28.8,
            "images": [],
            "skus": [{"name": "默认规格", "price": 28.8, "stock": 0}],
            "status": "parsed",
            "error": "未能访问 1688 页面，已按链接生成待复核商品源",
        }
        real_source = {
            **fallback_source,
            "title": "跨境爆款女士厚底运动凉鞋 2026 夏季新款",
            "shop_name": "广州鞋业源头工厂",
            "error": "",
        }

        with patch("backend.main.fetch_product_from_url", AsyncMock(return_value=fallback_source)):
            self.client.post("/api/1688/import-url", json={"urls": [url]})
        with patch("backend.main.fetch_product_from_url", AsyncMock(return_value=real_source)):
            self.client.post("/api/1688/import-url", json={"urls": [url]})

        sources = self.client.get("/api/1688/sources").json()["sources"]
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["title"], "跨境爆款女士厚底运动凉鞋 2026 夏季新款")
        self.assertEqual(sources[0]["shopName"], "广州鞋业源头工厂")
        self.assertEqual(sources[0]["error"], "")

    def test_import_matches_1688_product_to_ozon_category_tree(self):
        self.client.post(
            "/api/ozon/bind-bulk",
            json={"stores": [{"name": "h1", "clientId": "4861718", "apiKey": "real-key"}]},
        )
        parsed_source = {
            "offer_id": "614142976242",
            "url": "https://detail.1688.com/offer/614142976242.html",
            "title": "夏季薄刺绣头巾包头发带女遮白发宽边时尚宽蕾丝压发头套发箍头饰",
            "shop_name": "义乌妙斯电子商务有限公司",
            "price_min": 4.2,
            "price_max": 4.6,
            "images": [],
            "skus": [{"name": "默认规格", "price": 4.2, "stock": 0}],
            "status": "parsed",
            "error": "",
        }
        category_tree = {
            "result": [
                {
                    "category_name": "Одежда и аксессуары",
                    "children": [
                        {
                            "description_category_id": 170,
                            "type_id": 777,
                            "type_name": "Аксессуары для волос",
                        }
                    ],
                }
            ]
        }

        with patch("backend.main.fetch_product_from_url", AsyncMock(return_value=parsed_source)):
            with patch("backend.main.list_description_category_tree", AsyncMock(return_value=category_tree)):
                import_response = self.client.post("/api/1688/import-url", json={"urls": [parsed_source["url"]]})

        source = import_response.json()["sources"][0]
        self.assertEqual(source["ozonCategory"], "Аксессуары для волос")
        self.assertEqual(source["ozonCategoryId"], "170")
        self.assertEqual(source["ozonTypeId"], "777")

        product = self.client.post(
            "/api/products/normalize",
            json={"sourceIds": [source["id"]], "targetMargin": 0.30},
        ).json()["products"][0]
        self.assertEqual(product["category"], "Аксессуары для волос")
        self.assertEqual(product["categoryId"], "170")
        self.assertEqual(product["typeId"], "777")
        self.assertEqual(product["validationStatus"], "ready")

    def test_rematch_categories_updates_existing_1688_source_and_product(self):
        parsed_source = {
            "offer_id": "614142976242",
            "url": "https://detail.1688.com/offer/614142976242.html",
            "title": "夏季薄刺绣头巾包头发带女遮白发宽边时尚宽蕾丝压发头套发箍头饰",
            "shop_name": "义乌妙斯电子商务有限公司",
            "price_min": 4.2,
            "price_max": 4.6,
            "images": [],
            "skus": [{"name": "默认规格", "price": 4.2, "stock": 0}],
            "status": "parsed",
            "error": "",
        }
        with patch("backend.main.fetch_product_from_url", AsyncMock(return_value=parsed_source)):
            import_response = self.client.post(
                "/api/1688/import-url",
                json={"urls": [parsed_source["url"]]},
            )
        source_id = import_response.json()["sources"][0]["id"]
        product = self.client.post(
            "/api/products/normalize",
            json={"sourceIds": [source_id], "targetMargin": 0.30},
        ).json()["products"][0]
        self.assertEqual(product["typeId"], "0")

        self.client.post(
            "/api/ozon/bind-bulk",
            json={"stores": [{"name": "h1", "clientId": "4861718", "apiKey": "real-key"}]},
        )
        category_tree = {
            "result": [
                {
                    "description_category_id": 170,
                    "category_name": "Одежда и аксессуары",
                    "children": [
                        {
                            "category_name": "Аксессуары",
                            "children": [{"type_id": 777, "type_name": "Аксессуары для волос"}],
                        }
                    ],
                }
            ]
        }

        with patch("backend.main.list_description_category_tree", AsyncMock(return_value=category_tree)):
            response = self.client.post("/api/1688/rematch-categories", json={"sourceIds": [source_id]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["matched"], 1)
        source = response.json()["sources"][0]
        self.assertEqual(source["ozonCategoryId"], "170")
        self.assertEqual(source["ozonTypeId"], "777")
        from backend import db

        with db.connect() as connection:
            row = connection.execute("SELECT * FROM products WHERE id=?", (product["id"],)).fetchone()
        updated_product = db.row_to_product(row)
        self.assertEqual(updated_product["categoryId"], "170")
        self.assertEqual(updated_product["typeId"], "777")
        self.assertEqual(updated_product["validationStatus"], "ready")

    def test_normalize_same_source_updates_existing_product_instead_of_duplicating(self):
        import_response = self.client.post(
            "/api/1688/import-url",
            json={"urls": ["https://detail.1688.com/offer/739590664908.html"]},
        )
        source_id = import_response.json()["sources"][0]["id"]

        first = self.client.post(
            "/api/products/normalize",
            json={"sourceIds": [source_id], "targetMargin": 0.30},
        ).json()["products"][0]
        second = self.client.post(
            "/api/products/normalize",
            json={"sourceIds": [source_id], "targetMargin": 0.50},
        ).json()["products"][0]

        self.assertEqual(second["id"], first["id"])
        self.assertNotEqual(second["targetMargin"], first["targetMargin"])
        from backend import db

        with db.connect() as connection:
            count = connection.execute("SELECT COUNT(*) AS count FROM products WHERE source_id=?", (source_id,)).fetchone()["count"]
        self.assertEqual(count, 1)

    def test_delete_1688_source_removes_unpublished_source_and_generated_product(self):
        import_response = self.client.post(
            "/api/1688/import-url",
            json={"urls": ["https://detail.1688.com/offer/739590664908.html"]},
        )
        source_id = import_response.json()["sources"][0]["id"]
        product_id = self.client.post(
            "/api/products/normalize",
            json={"sourceIds": [source_id], "targetMargin": 0.30},
        ).json()["products"][0]["id"]

        response = self.client.delete(f"/api/1688/sources/{source_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted"], True)
        sources = self.client.get("/api/1688/sources").json()["sources"]
        self.assertEqual(sources, [])
        from backend import db

        with db.connect() as connection:
            product = connection.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        self.assertIsNone(product)

    def test_delete_1688_source_blocks_when_product_has_publish_record(self):
        import_response = self.client.post(
            "/api/1688/import-url",
            json={"urls": ["https://detail.1688.com/offer/739590664908.html"]},
        )
        source_id = import_response.json()["sources"][0]["id"]
        product_id = self.client.post(
            "/api/products/normalize",
            json={"sourceIds": [source_id], "targetMargin": 0.30},
        ).json()["products"][0]["id"]
        from backend import db

        with db.connect() as connection:
            connection.execute(
                """
                INSERT INTO published_products
                (id, store_id, product_id, offer_id, source_url, status, import_task_id, error, price_rub, stock, created_at)
                VALUES ('pub-test', 'store-1', ?, 'xhDemo1234567890', 'https://detail.1688.com/offer/739590664908.html', 'submitted', 'task-1', '', 88, 10, '2026-06-02')
                """,
                (product_id,),
            )
            connection.commit()

        response = self.client.delete(f"/api/1688/sources/{source_id}")

        self.assertEqual(response.status_code, 409)
        self.assertIn("已有上架记录", response.json()["error"])

    def test_publish_skips_failed_validation_and_records_store_product_links(self):
        bind_response = self.client.post(
            "/api/ozon/bind-bulk",
            json={
                "stores": [
                    {"name": "Moscow Home", "clientId": "client-1", "apiKey": "key-1"},
                    {"name": "Kazan Home", "clientId": "client-2", "apiKey": "key-2"},
                ],
                "validateWithOzon": False,
            },
        )
        self.assertEqual(bind_response.status_code, 200)
        store_ids = [store["id"] for store in bind_response.json()["stores"]]

        import_response = self.client.post(
            "/api/1688/import-url",
            json={"urls": ["https://detail.1688.com/offer/739590664908.html"]},
        )
        source_id = import_response.json()["sources"][0]["id"]
        normalize_payload = self.client.post(
            "/api/products/normalize",
            json={"sourceIds": [source_id], "targetMargin": 0.30},
        ).json()["products"][0]
        product_id = normalize_payload["id"]

        publish_response = self.client.post(
            "/api/products/publish",
            json={"productIds": [product_id], "storeIds": store_ids},
        )
        self.assertEqual(publish_response.status_code, 200)
        payload = publish_response.json()
        self.assertEqual(payload["summary"]["submitted"], 0)
        self.assertEqual(payload["summary"]["skipped"], 2)
        self.assertEqual(len(payload["results"]), 2)
        self.assertIn("缺少 Ozon 类型 ID", payload["results"][0]["error"])

        first_store_products = self.client.get(f"/api/stores/{store_ids[0]}/products").json()["products"]
        self.assertEqual(len(first_store_products), 0)

    def test_publish_jobs_can_be_listed_and_synced_to_done(self):
        bind_response = self.client.post(
            "/api/ozon/bind-bulk",
            json={"stores": [{"name": "Moscow Home", "clientId": "client-1", "apiKey": "key-1"}]},
        )
        store_id = bind_response.json()["stores"][0]["id"]
        import_response = self.client.post(
            "/api/1688/import-url",
            json={"urls": ["https://detail.1688.com/offer/739590664908.html"]},
        )
        source_id = import_response.json()["sources"][0]["id"]
        product_id = self.client.post(
            "/api/products/normalize",
            json={"sourceIds": [source_id], "targetMargin": 0.30},
        ).json()["products"][0]["id"]
        from backend import db

        with db.connect() as connection:
            connection.execute(
                """
                UPDATE products
                SET category_id='1', type_id='2', validation_status='ready', validation_errors_json='[]'
                WHERE id=?
                """,
                (product_id,),
            )
            connection.commit()

        publish_response = self.client.post(
            "/api/products/publish",
            json={"productIds": [product_id], "storeIds": [store_id]},
        )
        self.assertEqual(publish_response.status_code, 200)

        jobs_response = self.client.get("/api/products/publish-jobs")
        self.assertEqual(jobs_response.status_code, 200)
        jobs = jobs_response.json()["jobs"]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["status"], "submitted")
        self.assertTrue(jobs[0]["importTaskId"].startswith("demo-import-"))

        with (
            patch("backend.main.list_warehouses", AsyncMock(return_value={"warehouses": [{"warehouse_id": 123}]})) as warehouses_mock,
            patch("backend.main.update_product_stocks", AsyncMock(return_value={"result": [{"updated": True}]})) as stocks_mock,
        ):
            sync_response = self.client.post("/api/products/publish-jobs/sync")
        self.assertEqual(sync_response.status_code, 200)
        synced_jobs = sync_response.json()["jobs"]
        self.assertEqual(synced_jobs[0]["status"], "done")
        self.assertEqual(synced_jobs[0]["error"], "")
        warehouses_mock.assert_awaited_once_with("client-1", "key-1")
        stocks_mock.assert_awaited_once_with(
            "client-1",
            "key-1",
            offer_id=synced_jobs[0]["offerId"],
            stock=10,
            warehouse_id=123,
        )

    def test_import_status_with_errors_is_failed_even_when_imported(self):
        from backend.main import resolve_import_status

        status, error = resolve_import_status(
            {
                "result": {
                    "items": [
                        {
                            "offer_id": "xhvGtY3YtVFOsyBGhG",
                            "status": "imported",
                            "errors": [
                                {
                                    "attribute_id": 9048,
                                    "attribute_name": "Название модели",
                                    "message": "Attribute value empty",
                                }
                            ],
                        }
                    ]
                }
            },
            "xhvGtY3YtVFOsyBGhG",
        )

        self.assertEqual(status, "failed")
        self.assertIn("Attribute value empty", error)

    def test_publish_sends_system_sku_and_russian_name_to_ozon(self):
        bind_response = self.client.post(
            "/api/ozon/bind-bulk",
            json={"stores": [{"name": "h1", "clientId": "client-1", "apiKey": "key-1"}]},
        )
        store_id = bind_response.json()["stores"][0]["id"]
        parsed_source = {
            "offer_id": "614142976242",
            "url": "https://detail.1688.com/offer/614142976242.html",
            "title": "夏季薄刺绣头巾包头发带女遮白发宽边时尚宽蕾丝压发头套发箍头饰",
            "shop_name": "义乌妙斯电子商务有限公司",
            "price_min": 4.2,
            "price_max": 4.6,
            "images": [],
            "skus": [{"name": "货号"}, {"name": "白色"}, {"name": "红色"}],
            "status": "parsed",
            "error": "",
        }
        with patch("backend.main.fetch_product_from_url", AsyncMock(return_value=parsed_source)):
            import_response = self.client.post("/api/1688/import-url", json={"urls": [parsed_source["url"]]})
        source_id = import_response.json()["sources"][0]["id"]
        product = self.client.post(
            "/api/products/normalize",
            json={"sourceIds": [source_id], "targetMargin": 0.30},
        ).json()["products"][0]

        from backend import db

        with db.connect() as connection:
            connection.execute(
                """
                UPDATE products
                SET category='Невидимка', category_id='29183107', type_id='97579', validation_status='ready', validation_errors_json='[]'
                WHERE id=?
                """,
                (product["id"],),
            )
            connection.commit()

        with patch(
            "backend.main.submit_product_import",
            AsyncMock(return_value={"result": {"task_id": "demo-import-sku-name"}}),
        ) as mocked_submit:
            response = self.client.post("/api/products/publish", json={"productIds": [product["id"]], "storeIds": [store_id]})

        self.assertEqual(response.status_code, 200)
        call_kwargs = mocked_submit.await_args.kwargs
        self.assertEqual(call_kwargs["offer_id"], product["sku"])
        self.assertRegex(call_kwargs["offer_id"], r"^xh[A-Za-z0-9]{16}$")
        self.assertEqual(call_kwargs["product"]["ruTitle"], "Женская повязка на голову для волос")

    def test_store_orders_endpoint_returns_synced_or_demo_orders(self):
        bind_response = self.client.post(
            "/api/ozon/bind-bulk",
            json={"stores": [{"name": "Moscow Home", "clientId": "client-1", "apiKey": "key-1"}]},
        )
        store_id = bind_response.json()["stores"][0]["id"]
        response = self.client.get(f"/api/stores/{store_id}/orders")
        self.assertEqual(response.status_code, 200)
        self.assertIn("orders", response.json())

    def test_single_bind_rate_limit_saves_store_as_pending_verification(self):
        with patch(
            "backend.main.bind_ozon_store",
            AsyncMock(side_effect=RuntimeError("You have reached request rate limit per second")),
        ):
            response = self.client.post(
                "/api/ozon/bind",
                json={"name": "北京测试店", "clientId": "client-rate-limit", "apiKey": "real-key"},
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("warning", payload)
        self.assertEqual(payload["store"]["name"], "北京测试店")
        self.assertEqual(payload["store"]["status"], "warning")
        self.assertEqual(payload["store"]["owner"], "待验证")
        self.assertEqual(payload["store"]["realBound"], False)
        self.assertNotIn("apiKey", payload["store"])

        stores = self.client.get("/api/ozon/stores").json()["stores"]
        self.assertEqual(len(stores), 1)
        self.assertEqual(stores[0]["name"], "北京测试店")

    def test_sync_store_products_pulls_existing_ozon_items(self):
        bind_response = self.client.post(
            "/api/ozon/bind-bulk",
            json={"stores": [{"name": "H1", "clientId": "123456", "apiKey": "real-key"}]},
        )
        store_id = bind_response.json()["stores"][0]["id"]
        with (
            patch(
                "backend.main.list_store_products",
                AsyncMock(
                    return_value={
                        "result": {
                            "items": [
                                {"product_id": 9001, "offer_id": "H1-OFFER-001"},
                                {"product_id": 9002, "offer_id": "H1-OFFER-002"},
                            ]
                        }
                    }
                ),
            ),
            patch(
                "backend.main.list_product_info",
                AsyncMock(
                    return_value={
                        "items": [
                            {"product_id": 9001, "offer_id": "H1-OFFER-001", "name": "Existing kettle"},
                            {"product_id": 9002, "offer_id": "H1-OFFER-002", "name": "Existing title"},
                        ]
                    }
                ),
            ),
            patch(
                "backend.main.list_product_prices",
                AsyncMock(
                    return_value={
                        "items": [
                            {"product_id": 9001, "offer_id": "H1-OFFER-001", "price": {"price": "1299"}},
                            {"product_id": 9002, "offer_id": "H1-OFFER-002", "price": {"price": "899"}},
                        ]
                    }
                ),
            ),
            patch(
                "backend.main.list_product_stocks",
                AsyncMock(
                    return_value={
                        "items": [
                            {"product_id": 9001, "offer_id": "H1-OFFER-001", "stocks": [{"present": 11}, {"present": 4}]},
                            {"product_id": 9002, "offer_id": "H1-OFFER-002", "stocks": [{"present": 5}]},
                        ]
                    }
                ),
            ),
        ):
            response = self.client.post(f"/api/stores/{store_id}/products/sync")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["synced"], 2)
        self.assertEqual(payload["products"][0]["sourceUrl"], "")
        self.assertEqual(payload["products"][0]["status"], "synced")

        products = self.client.get(f"/api/stores/{store_id}/products").json()["products"]
        self.assertEqual(len(products), 2)
        self.assertEqual({product["offerId"] for product in products}, {"H1-OFFER-001", "H1-OFFER-002"})
        self.assertEqual(products[0]["sourceUrl"], "")
        first = next(product for product in products if product["offerId"] == "H1-OFFER-001")
        self.assertEqual(first["title"], "Existing kettle")
        self.assertEqual(first["priceCny"], 1299)
        self.assertEqual(first["priceRub"], 1299)
        self.assertEqual(first["stock"], 15)

    def test_sync_store_products_skips_detail_loaders_when_store_has_no_products(self):
        bind_response = self.client.post(
            "/api/ozon/bind-bulk",
            json={"stores": [{"name": "Empty", "clientId": "123456", "apiKey": "real-key"}]},
        )
        store_id = bind_response.json()["stores"][0]["id"]
        from backend import db

        with db.connect() as connection:
            connection.execute(
                "UPDATE stores SET status='warning', verification_error='商品详情同步失败：use either offer_id or product_id or sku' WHERE id=?",
                (store_id,),
            )
            connection.commit()
        with (
            patch("backend.main.list_store_products", AsyncMock(return_value={"result": {"items": []}})),
            patch("backend.main.list_product_info", AsyncMock()) as info_mock,
            patch("backend.main.list_product_prices", AsyncMock()) as prices_mock,
            patch("backend.main.list_product_stocks", AsyncMock()) as stocks_mock,
        ):
            response = self.client.post(f"/api/stores/{store_id}/products/sync")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["synced"], 0)
        self.assertEqual(payload["warnings"], [])
        self.assertEqual(payload["store"]["status"], "active")
        self.assertEqual(payload["store"]["verificationError"], "")
        info_mock.assert_not_awaited()
        prices_mock.assert_not_awaited()
        stocks_mock.assert_not_awaited()

    def test_bind_store_task_persists_progress_and_syncs_products(self):
        response = self.client.post(
            "/api/ozon/bind-task",
            json={"name": "Task Store", "clientId": "client-demo", "apiKey": "key-demo"},
        )

        self.assertEqual(response.status_code, 200)
        task_id = response.json()["taskId"]
        task = self.client.get(f"/api/tasks/{task_id}").json()["task"]
        self.assertEqual(task["kind"], "ozon_bind")
        self.assertEqual(task["status"], "done")
        self.assertEqual(task["progress"], 100)
        self.assertEqual(task["message"], "店铺已绑定，已同步 1 个商品")

        stores = self.client.get("/api/ozon/stores").json()["stores"]
        self.assertEqual(len(stores), 1)
        self.assertEqual(stores[0]["name"], "Task Store")
        products = self.client.get(f"/api/stores/{stores[0]['id']}/products").json()["products"]
        self.assertEqual(len(products), 1)

    def test_sync_store_products_task_records_failure_error(self):
        bind_response = self.client.post(
            "/api/ozon/bind-bulk",
            json={"stores": [{"name": "Broken Sync", "clientId": "client-demo", "apiKey": "key-demo"}]},
        )
        store_id = bind_response.json()["stores"][0]["id"]

        with patch("backend.main.list_store_products", AsyncMock(side_effect=RuntimeError("Ozon unavailable"))):
            response = self.client.post(f"/api/stores/{store_id}/products/sync-task")

        self.assertEqual(response.status_code, 200)
        task = self.client.get(f"/api/tasks/{response.json()['taskId']}").json()["task"]
        self.assertEqual(task["status"], "failed")
        self.assertIn("Ozon unavailable", task["error"])

    def test_bulk_bind_task_auto_sync_can_be_enabled(self):
        response = self.client.post(
            "/api/ozon/bind-bulk-task",
            json={
                "autoSyncProducts": True,
                "stores": [
                    {"name": "Bulk A", "clientId": "client-a", "apiKey": "key-a"},
                    {"name": "Bulk B", "clientId": "client-b", "apiKey": "key-b"},
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        task = self.client.get(f"/api/tasks/{response.json()['taskId']}").json()["task"]
        self.assertEqual(task["status"], "done")
        self.assertEqual(task["progress"], 100)
        self.assertEqual(len(task["result"]["stores"]), 2)

        tasks = self.client.get("/api/tasks").json()["tasks"]
        self.assertEqual(tasks[0]["id"], task["id"])

    def test_update_store_product_price_updates_ozon_and_local_record(self):
        bind_response = self.client.post(
            "/api/ozon/bind-bulk",
            json={"stores": [{"name": "H1", "clientId": "client-demo", "apiKey": "key-demo"}]},
        )
        store_id = bind_response.json()["stores"][0]["id"]
        with patch(
            "backend.main.list_store_products",
            AsyncMock(return_value={"result": {"items": [{"product_id": 9001, "offer_id": "H1-OFFER-001"}]}}),
        ):
            self.client.post(f"/api/stores/{store_id}/products/sync")

        with patch("backend.main.update_product_prices", AsyncMock(return_value={"result": [{"offer_id": "H1-OFFER-001"}]})) as mocked:
            response = self.client.post(
                f"/api/stores/{store_id}/products/H1-OFFER-001/price",
                json={"priceCny": 777, "oldPriceCny": 999},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["product"]["priceCny"], 777)
        self.assertEqual(response.json()["product"]["priceRub"], 777)
        mocked.assert_awaited_once_with(
            "client-demo",
            "key-demo",
            offer_id="H1-OFFER-001",
            price_cny=777,
            old_price_cny=999,
            min_price_cny=None,
        )
        products = self.client.get(f"/api/stores/{store_id}/products").json()["products"]
        self.assertEqual(products[0]["priceCny"], 777)
        self.assertEqual(products[0]["priceRub"], 777)

    def test_update_store_product_price_keeps_local_price_when_ozon_rejects(self):
        bind_response = self.client.post(
            "/api/ozon/bind-bulk",
            json={"stores": [{"name": "H1", "clientId": "client-demo", "apiKey": "key-demo"}]},
        )
        store_id = bind_response.json()["stores"][0]["id"]
        with patch(
            "backend.main.list_store_products",
            AsyncMock(return_value={"result": {"items": [{"product_id": 9001, "offer_id": "H1-OFFER-001"}]}}),
        ):
            self.client.post(f"/api/stores/{store_id}/products/sync")

        with patch("backend.main.update_product_prices", AsyncMock(side_effect=RuntimeError("price rejected"))):
            response = self.client.post(
                f"/api/stores/{store_id}/products/H1-OFFER-001/price",
                json={"priceCny": 777},
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn("price rejected", response.json()["error"])
        products = self.client.get(f"/api/stores/{store_id}/products").json()["products"]
        self.assertEqual(products[0]["priceCny"], 999)

    def test_delete_store_removes_bound_store_records(self):
        bind_response = self.client.post(
            "/api/ozon/bind-bulk",
            json={"stores": [{"name": "Delete Me", "clientId": "client-demo", "apiKey": "key-demo"}]},
        )
        store_id = bind_response.json()["stores"][0]["id"]
        self.client.get(f"/api/stores/{store_id}/orders")
        with patch(
            "backend.main.list_store_products",
            AsyncMock(return_value={"result": {"items": [{"product_id": 9001, "offer_id": "DELETE-OFFER"}]}}),
        ):
            self.client.post(f"/api/stores/{store_id}/products/sync")

        response = self.client.delete(f"/api/ozon/stores/{store_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted"], True)
        self.assertEqual(self.client.get("/api/ozon/stores").json()["stores"], [])
        self.assertEqual(self.client.get(f"/api/stores/{store_id}/products").json()["products"], [])

    def test_delete_store_product_removes_one_published_product(self):
        bind_response = self.client.post(
            "/api/ozon/bind-bulk",
            json={"stores": [{"name": "H1", "clientId": "client-demo", "apiKey": "key-demo"}]},
        )
        store_id = bind_response.json()["stores"][0]["id"]
        with patch(
            "backend.main.list_store_products",
            AsyncMock(
                return_value={
                    "result": {
                        "items": [
                            {"product_id": 9001, "offer_id": "DELETE-OFFER"},
                            {"product_id": 9002, "offer_id": "KEEP-OFFER"},
                        ]
                    }
                }
            ),
        ):
            self.client.post(f"/api/stores/{store_id}/products/sync")

        response = self.client.delete(f"/api/stores/{store_id}/products/DELETE-OFFER")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted"], True)
        products = self.client.get(f"/api/stores/{store_id}/products").json()["products"]
        self.assertEqual({product["offerId"] for product in products}, {"KEEP-OFFER"})

    def test_delete_store_product_returns_404_for_missing_product(self):
        bind_response = self.client.post(
            "/api/ozon/bind-bulk",
            json={"stores": [{"name": "H1", "clientId": "client-demo", "apiKey": "key-demo"}]},
        )
        store_id = bind_response.json()["stores"][0]["id"]

        response = self.client.delete(f"/api/stores/{store_id}/products/MISSING-OFFER")

        self.assertEqual(response.status_code, 404)
        self.assertIn("商品不存在", response.json()["error"])


if __name__ == "__main__":
    unittest.main()
