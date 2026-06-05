import unittest
from unittest.mock import AsyncMock, patch

from backend import ozon_client


class OzonClientTest(unittest.IsolatedAsyncioTestCase):
    def test_build_ozon_headers_sends_credentials_server_side(self):
        self.assertEqual(
            ozon_client.build_ozon_headers("12345", "secret"),
            {
                "Client-Id": "12345",
                "Api-Key": "secret",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    def test_mask_client_id_keeps_short_display_text(self):
        self.assertEqual(ozon_client.mask_client_id("1234567890"), "1234...7890")
        self.assertEqual(ozon_client.mask_client_id("123456"), "123456")

    def test_create_bound_store_response_does_not_expose_credentials(self):
        result = ozon_client.create_bound_store_response(
            name="真实 Ozon 店铺",
            client_id="1234567890",
            api_key="secret",
            warehouses=[{"name": "Warehouse A"}],
        )
        self.assertEqual(result["store"]["platform"], "Ozon")
        self.assertEqual(result["store"]["realBound"], True)
        self.assertEqual(result["store"]["authLabel"], "Client ID: 1234...7890 · 1 个仓库")
        self.assertNotIn("apiKey", result["store"])
        self.assertNotIn("clientId", result["store"])

    def test_validate_bind_payload_requires_fields(self):
        with self.assertRaisesRegex(ValueError, "请填写店铺名称、Client ID 和 API Key"):
            ozon_client.validate_bind_payload({"name": "", "clientId": "", "apiKey": ""})

    async def test_bind_ozon_store_uses_v2_warehouse_list(self):
        with patch(
            "backend.ozon_client.call_ozon",
            AsyncMock(return_value={"warehouses": [{"name": "Warehouse A"}]}),
        ) as mocked:
            result = await ozon_client.bind_ozon_store(
                {"name": "h1", "clientId": "1234567890", "apiKey": "secret"}
            )

        mocked.assert_awaited_once_with("1234567890", "secret", "/v2/warehouse/list", {})
        self.assertEqual(result["warehousesCount"], 1)

    async def test_update_product_stocks_uses_offer_id_and_warehouse_id(self):
        with patch("backend.ozon_client.call_ozon", AsyncMock(return_value={"result": []})) as mocked:
            await ozon_client.update_product_stocks(
                "client-1",
                "real-key",
                offer_id="xhDemo1234567890",
                stock=10,
                warehouse_id=1020005017796530,
            )

        mocked.assert_awaited_once_with(
            "client-1",
            "real-key",
            "/v2/products/stocks",
            {
                "stocks": [
                    {
                        "offer_id": "xhDemo1234567890",
                        "stock": 10,
                        "warehouse_id": 1020005017796530,
                    }
                ]
            },
        )

    async def test_update_product_prices_uses_only_one_identifier(self):
        with patch("backend.ozon_client.call_ozon", AsyncMock(return_value={"result": [{"offer_id": "OFFER-1", "errors": []}]})) as mocked:
            await ozon_client.update_product_prices(
                "client-1",
                "real-key",
                offer_id="OFFER-1",
                product_id="9001",
                price_cny=99,
            )

        mocked.assert_awaited_once_with(
            "client-1",
            "real-key",
            "/v1/product/import/prices",
            {"prices": [{"price": "99.0", "currency_code": "CNY", "offer_id": "OFFER-1", "old_price": "116.82"}]},
        )

    async def test_update_product_prices_raises_item_errors(self):
        with patch(
            "backend.ozon_client.call_ozon",
            AsyncMock(return_value={"result": [{"offer_id": "OFFER-1", "errors": [{"message": "price rejected"}]}]}),
        ):
            with self.assertRaisesRegex(RuntimeError, "price rejected"):
                await ozon_client.update_product_prices(
                    "client-1",
                    "real-key",
                    offer_id="OFFER-1",
                    price_cny=99,
                )

    async def test_product_info_uses_only_one_lookup_identifier(self):
        with patch("backend.ozon_client.call_ozon", AsyncMock(return_value={"items": []})) as mocked:
            await ozon_client.list_product_info(
                "client-1",
                "real-key",
                offer_ids=["OFFER-1"],
                product_ids=[123],
            )

        mocked.assert_awaited_once_with(
            "client-1",
            "real-key",
            "/v3/product/info/list",
            {"offer_id": ["OFFER-1"]},
        )

    def test_product_import_payload_uses_cny_currency(self):
        item = ozon_client.build_product_import_item(
            {"ruTitle": "Товар", "categoryId": 1, "typeId": 2, "images": [], "ozonAttributes": []},
            "OFFER-1",
            88,
            5,
        )
        self.assertEqual(item["price"], "88")
        self.assertEqual(item["currency_code"], "CNY")

    def test_product_import_payload_adds_required_model_name_attribute(self):
        item = ozon_client.build_product_import_item(
            {"ruTitle": "Женская повязка на голову", "categoryId": 29183107, "typeId": 97579, "images": []},
            "xhvGtY3YtVFOsyBGhG",
            63,
            10,
        )

        model_attribute = next(attribute for attribute in item["attributes"] if attribute["id"] == 9048)
        self.assertEqual(model_attribute["values"][0]["value"], "Женская повязка на голову")

    def test_validate_product_for_publish_requires_positive_ozon_type_and_category_ids(self):
        errors = ozon_client.validate_product_for_publish(
            {
                "ruTitle": "Товар",
                "sku": "xhDemo1234567890",
                "suggestedPriceRub": 88,
                "category": "General",
                "categoryId": "0",
                "typeId": "0",
            }
        )
        self.assertIn("缺少 Ozon 类目 ID", errors)
        self.assertIn("缺少 Ozon 类型 ID", errors)


if __name__ == "__main__":
    unittest.main()
