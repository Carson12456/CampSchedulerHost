
import unittest
from evaluate_week_success import DEFAULT_WEIGHTS

class TestScoringWeights(unittest.TestCase):
    def test_preference_weights(self):
        """Verify the scoring weights match the user-requested curve."""
        
        # Checking Top 1-5 (40 -> 20)
        top5 = DEFAULT_WEIGHTS["preference_points"]["top5"]
        self.assertEqual(top5[0], 40.0, "Rank 1 should be 40.0")
        self.assertEqual(top5[4], 20.0, "Rank 5 should be 20.0")
        
        # Checking Top 6-10 (19 -> 15)
        top10 = DEFAULT_WEIGHTS["preference_points"]["top6_10"]
        self.assertEqual(top10[0], 19.0, "Rank 6 should be 19.0")
        self.assertEqual(top10[4], 15.0, "Rank 10 should be 15.0")
        
        # Checking Top 11-15 (13.5 -> 7.5) - Steeper drop
        top15 = DEFAULT_WEIGHTS["preference_points"]["top11_15"]
        self.assertEqual(top15[0], 13.5, "Rank 11 should be 13.5")
        
        # Checking Top 16-20 (6.0 -> 0.0)
        top20 = DEFAULT_WEIGHTS["preference_points"]["top16_20"]
        self.assertEqual(top20[4], 0.0, "Rank 20 should be 0.0")

    def test_penalties(self):
        """Verify penalties remain consistent."""
        self.assertEqual(DEFAULT_WEIGHTS["constraint_violation_penalty"], 25.0, "Soft constraint penalty should be 25.0")

if __name__ == '__main__':
    unittest.main()
