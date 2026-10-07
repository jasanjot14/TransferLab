import unittest
from analysis import Prediction, assess, forecast_history, next_arrival


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.a = Prediction("A", "a1", "S", 1_000, 500)
        self.b = Prediction("B", "b1", "S", 1_420, 500)

    def test_comfortable_and_walk_threshold(self):
        self.assertEqual(assess(self.a, self.b, 3, 550)["status"], "comfortable")
        self.assertEqual(assess(self.a, self.b, 6, 550)["status"], "tight")
        self.assertEqual(assess(self.a, self.b, 8, 550)["status"], "missed")

    def test_stale_does_not_claim_connection(self):
        self.assertEqual(assess(self.a, self.b, 3, 600)["status"], "stale")
        self.assertIsNone(assess(self.a, None, 3, 550)["gap_minutes"])

    def test_next_arrival_and_history(self):
        later = Prediction("B", "b2", "S", 1_620, 500)
        self.assertEqual(next_arrival([later, self.b], "B", "S", 900), self.b)
        self.assertEqual(forecast_history([(self.a, self.b), (self.a, later)], 8)["forecast_share"], 0.5)


if __name__ == "__main__":
    unittest.main()
