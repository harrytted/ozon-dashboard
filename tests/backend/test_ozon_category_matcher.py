import unittest

from backend.ozon_category_matcher import flatten_ozon_category_tree, match_ozon_category


class OzonCategoryMatcherTest(unittest.TestCase):
    def test_flatten_inherits_description_category_id_for_type_children(self):
        tree = [
            {
                "description_category_id": 170,
                "category_name": "Одежда и аксессуары",
                "children": [
                    {
                        "category_name": "Аксессуары",
                        "children": [
                            {"type_name": "Аксессуары для волос", "type_id": 777}
                        ],
                    }
                ],
            }
        ]

        candidates = flatten_ozon_category_tree(tree)

        self.assertEqual(candidates[0]["categoryId"], "170")
        self.assertEqual(candidates[0]["typeId"], "777")
        self.assertEqual(candidates[0]["category"], "Аксессуары для волос")

    def test_match_uses_real_ozon_candidate_for_headwear_source(self):
        candidates = [
            {
                "category": "Подголовник для бани",
                "categoryId": "999",
                "typeId": "111",
                "searchText": "Дом и сад / Товары для бани / Подголовник для бани",
            },
            {
                "category": "Аксессуары для волос",
                "categoryId": "170",
                "typeId": "777",
                "searchText": "Одежда и аксессуары / Аксессуары / Аксессуары для волос",
            }
        ]

        match = match_ozon_category({"title": "夏季薄刺绣头巾包头发带"}, candidates)

        self.assertEqual(match["ozon_category_id"], "170")
        self.assertEqual(match["ozon_type_id"], "777")
        self.assertEqual(match["ozon_category_matched_by"], "ozon_tree:fashion_accessories")

    def test_match_does_not_assign_real_ids_without_1688_category_signal(self):
        candidates = [
            {
                "category": "Съемник фасадной крышки",
                "categoryId": "17028653",
                "typeId": "971151174",
                "searchText": "Автотовары / Съемник фасадной крышки",
            }
        ]

        match = match_ozon_category({"title": "1688 商品 739590664908"}, candidates)

        self.assertEqual(match["ozon_category"], "General")
        self.assertEqual(match["ozon_category_id"], "0")
        self.assertEqual(match["ozon_type_id"], "0")


if __name__ == "__main__":
    unittest.main()
