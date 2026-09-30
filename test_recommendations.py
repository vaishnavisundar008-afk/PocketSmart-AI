import unittest

from app.services.recommendations import build_fallback


class FallbackRecommendationTests(unittest.TestCase):
    def test_each_planner_returns_recommendations_within_budget(self):
        cases = [
            ("home", {"items": ["Lights", "Ceiling fan", "Dining table"]}),
            ("party", {"event_type": "birthday", "guests": 24, "city": "Austin"}),
            ("jewelry", {"occasion": "wedding", "style": "modern"}),
        ]

        for planner, preferences in cases:
            with self.subTest(planner=planner):
                result = build_fallback(planner, 1200, "USD", **preferences)
                total = sum(item["price"] for item in result["recommendations"])
                allocation_total = sum(item["amount"] for item in result["allocations"])
                self.assertGreater(len(result["recommendations"]), 0)
                self.assertLessEqual(total, 1200)
                self.assertLessEqual(allocation_total, 1200)

    def test_unknown_planner_and_invalid_budget_are_rejected(self):
        with self.assertRaises(ValueError):
            build_fallback("wedding", 1200)
        with self.assertRaises(ValueError):
            build_fallback("home", 0)

    def test_home_quantity_is_included_in_budgeted_total(self):
        result = build_fallback(
            "home",
            500,
            items=[{"name": "Ceiling fan", "quantity": 3}],
        )
        recommendation = result["recommendations"][0]
        self.assertEqual(recommendation["quantity"], 3)
        self.assertLessEqual(recommendation["price"] * recommendation["quantity"], 500)


if __name__ == "__main__":
    unittest.main()