import asyncio
import unittest
from unittest.mock import patch

from backend import ai_normalizer, alibaba1688_client, pricing, sku


class PricingSku1688Test(unittest.TestCase):
    def test_extracts_1688_offer_id_from_common_urls(self):
        self.assertEqual(
            alibaba1688_client.extract_offer_id("https://detail.1688.com/offer/739590664908.html"),
            "739590664908",
        )
        self.assertEqual(
            alibaba1688_client.extract_offer_id("https://m.1688.com/offer/123456789012.html?spm=a"),
            "123456789012",
        )

    def test_parse_1688_html_extracts_title_price_images_and_specs(self):
        html = """
        <html>
          <head>
            <title>夏季民族风方巾批发-1688</title>
            <meta property="og:image" content="https://img.example/main.jpg">
          </head>
          <body>
            <h1>夏季民族风方巾 3 件套</h1>
            <script>
              window.__INIT_DATA__ = {
                "price": "12.50",
                "sku": [
                  {"name": "红色", "price": "12.50", "stock": 88},
                  {"name": "蓝色", "price": "13.00", "stock": 30}
                ],
                "shopName": "义乌围巾工厂",
                "images": ["https://img.example/a.jpg", "https://img.example/b.jpg"]
              };
            </script>
          </body>
        </html>
        """
        parsed = alibaba1688_client.parse_product_html(
            "https://detail.1688.com/offer/739590664908.html",
            html,
        )
        self.assertEqual(parsed["offer_id"], "739590664908")
        self.assertEqual(parsed["title"], "夏季民族风方巾 3 件套")
        self.assertEqual(parsed["shop_name"], "义乌围巾工厂")
        self.assertEqual(parsed["price_min"], 12.5)
        self.assertEqual(parsed["price_max"], 13.0)
        self.assertEqual(parsed["images"][0], "https://img.example/main.jpg")
        self.assertEqual(len(parsed["skus"]), 2)

    def test_parse_1688_html_filters_detail_attributes_from_skus(self):
        html = """
        <html><body><script>
          window.__INIT_DATA__ = {
            "sku": [
              {"name": "白色"},
              {"name": "货号"},
              {"name": "材质"},
              {"name": "红色"}
            ],
            "price": "4.20"
          };
        </script></body></html>
        """

        parsed = alibaba1688_client.parse_product_html(
            "https://detail.1688.com/offer/614142976242.html",
            html,
        )

        self.assertEqual([item["name"] for item in parsed["skus"]], ["白色", "红色"])

    def test_parse_1688_html_extracts_title_from_meta_and_boot_data(self):
        html = r"""
        <html>
          <head>
            <meta property="og:title" content="跨境爆款女士厚底运动凉鞋批发_阿里巴巴">
          </head>
          <body>
            <script>
              window.__OFFER_DETAIL__ = "{\"offerTitle\":\"跨境爆款女士厚底运动凉鞋 2026 夏季新款\",\"price\":\"28.80\"}";
            </script>
          </body>
        </html>
        """
        parsed = alibaba1688_client.parse_product_html(
            "https://detail.1688.com/offer/853346579651.html",
            html,
        )
        self.assertEqual(parsed["title"], "跨境爆款女士厚底运动凉鞋 2026 夏季新款")
        self.assertEqual(parsed["status"], "parsed")

    def test_fetch_product_tries_mobile_offer_page_when_desktop_is_punished(self):
        calls = []

        class FakeResponse:
            def __init__(self, text, headers=None, status_code=200):
                self.text = text
                self.headers = headers or {}
                self.status_code = status_code

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return False

            async def get(self, url, headers=None):
                calls.append(url)
                if "detail.1688.com" in url:
                    return FakeResponse("<html>验证页</html>", {"bxpunish": "1"})
                return FakeResponse(
                    '<html><head><meta property="og:title" content="跨境爆款女士厚底运动凉鞋批发_阿里巴巴"></head></html>'
                )

        with patch("backend.alibaba1688_client.httpx.AsyncClient", return_value=FakeClient()):
            product = asyncio.run(
                alibaba1688_client.fetch_product_from_url("https://detail.1688.com/offer/853346579651.html")
            )

        self.assertEqual(calls, [
            "https://detail.1688.com/offer/853346579651.html",
            "https://m.1688.com/offer/853346579651.html",
        ])
        self.assertEqual(product["title"], "跨境爆款女士厚底运动凉鞋批发")

    def test_generate_offer_id_is_stable_unique_and_safe(self):
        first = sku.generate_offer_id("Moscow Home", "739590664908", {"颜色": "红色", "尺寸": "均码"})
        second = sku.generate_offer_id("Moscow Home", "739590664908", {"尺寸": "均码", "颜色": "红色"})
        other_store = sku.generate_offer_id("Kazan Store", "739590664908", {"颜色": "红色", "尺寸": "均码"})
        self.assertEqual(first, second)
        self.assertNotEqual(first, other_store)
        self.assertRegex(first, r"^xh[A-Za-z0-9]{16}$")
        self.assertNotIn("-", first)

    def test_heuristic_normalize_uses_russian_listing_title(self):
        normalized = ai_normalizer.heuristic_normalize("夏季薄刺绣头巾包头发带女遮白发宽边时尚宽蕾丝压发头套发箍头饰")

        self.assertEqual(normalized.ruTitle, "Женская повязка на голову для волос")
        self.assertNotIn("头巾", normalized.ruTitle)

    def test_dynamic_net_margin_pricing_matches_demo(self):
        quote = pricing.calculate_price(
            cost_cny=34.5,
            exchange_rate=10.5,
            commission_rate=0.18,
            payment_rate=0.015,
            ad_rate=0.05,
            return_loss_rate=0.03,
            target_margin=0.50,
        )
        self.assertEqual(round(quote.fixed_cost_cny, 2), 34.5)
        self.assertEqual(round(quote.price_cny), 153)
        self.assertEqual(round(quote.fixed_cost_rub, 2), 34.5)
        self.assertEqual(round(quote.price_rub), 153)
        self.assertAlmostEqual(quote.net_margin, 0.50, places=2)

    def test_rejects_impossible_margin_and_fee_combination(self):
        with self.assertRaisesRegex(ValueError, "利润率和扣点之和必须小于 1"):
            pricing.calculate_price(
                cost_cny=10,
                exchange_rate=10,
                commission_rate=0.30,
                payment_rate=0.05,
                ad_rate=0.10,
                return_loss_rate=0.10,
                target_margin=0.50,
            )


if __name__ == "__main__":
    unittest.main()
