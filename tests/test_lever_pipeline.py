import unittest

import pandas as pd

from src.build_atlas import build_component_records


class LeverPipelineTest(unittest.TestCase):
    def setUp(self):
        self.row = pd.Series({
            "v2cltrnslw": 2.1,
            "v2juhcind": 2.2,
            "v2juncind": 2.0,
            "v2clkill": 2.4,
            "v2xcl_acjst": 0.6,
            "v2cltort": 2.3,
            "v2x_clphy": 0.4,
            "v2clrspct": 1.9,
            "v2x_freexp": 0.7,
        })

    def test_nine_levers_use_distinct_operational_signals(self):
        components = build_component_records(self.row, 2.5, 1.0)
        self.assertEqual(len(components), 9)
        self.assertEqual(components[2]["field"], "v2clkill")
        self.assertEqual(components[5]["field"], "v2x_clphy")
        self.assertEqual(components[3]["field"], "v2xcl_acjst")
        self.assertEqual(components[6]["field"], "v2clrspct")
        self.assertNotEqual(components[2]["bin"], components[5]["bin"])
        self.assertNotEqual(components[3]["bin"], components[6]["bin"])

    def test_score_is_exact_mean_of_nine_records(self):
        components = build_component_records(self.row, 2.5, 1.0)
        score = sum(component["bin"] for component in components) / 9.0
        self.assertEqual(score, 7 / 9)


if __name__ == "__main__":
    unittest.main()
