import unittest
from copy import deepcopy
import json
from pathlib import Path

from src.generate_eurozone_atlas import (
    EUROZONE_ISOS,
    EUROZONE_REPORT_URL,
    GDP_EUR_INDICATOR,
    _aggregate,
    _format_trend_text,
    _load_eurozone_rows,
    _world_bank_series,
    format_eur_per_capita,
    format_money,
)


class EurozoneCurrencyTest(unittest.TestCase):
    def test_qr_targets_versioned_standalone_report(self):
        self.assertEqual(
            EUROZONE_REPORT_URL,
            "https://github.com/SJAH9/rtldi-atlas/releases/download/v2026.8.8/"
            "RTLDI_EUROZONE_CAPITAL_EXCLUSION_MAP_2026.pdf",
        )

    def setUp(self):
        self.snapshot = {
            "responses": {
                indicator: {"data": [{"pages": 1}, [
                    {"countryiso3code": iso, "date": "2025", "value": value}
                    for iso in EUROZONE_ISOS
                ]]}
                for indicator, value in ((GDP_EUR_INDICATOR, 50000), ("SP.POP.TOTL", 1000000))
            },
            "country_metadata": {"data": {"source": [{"concept": [{"variable": [
                {"id": iso, "metatype": [{"id": "CurrencyUnit", "value": "Euro"}]}
                for iso in EUROZONE_ISOS
            ]}]}]}},
        }

    def test_euro_format_does_not_convert_input(self):
        self.assertEqual(format_money(1.13e9), "\u20ac1.1B")
        self.assertEqual(format_eur_per_capita(1130), "\u20ac1,130")

    def test_euro_baselines_replace_usd_only_in_scoped_rows(self):
        path = Path("data/processed/rtl_di_nation_breakdown_2026.json")
        original = path.read_bytes()
        rows, regression = _load_eurozone_rows(self.snapshot)
        summary = _aggregate(rows, regression)
        self.assertEqual(path.read_bytes(), original)
        originals = {row["iso3"]: row for row in json.loads(original)}
        for row in rows:
            self.assertEqual(row["g0"], 50000)
            self.assertEqual(row["g0_year"], 2025)
            self.assertEqual(row["population_year"], 2025)
            self.assertEqual(row["population"], 1000000)
            self.assertEqual(row["r"], originals[row["iso3"]]["r"])
            self.assertNotIn("total_deficit_usd", row)
        euro_total = summary["total_lost_gdp"]
        self.assertAlmostEqual(
            sum(row["total_deficit_eur"] for row in rows),
            euro_total, delta=0.01,
        )
        self.assertAlmostEqual(
            sum(item["attributable_lost_gdp"] for item in summary["indicators"]),
            euro_total, delta=0.01,
        )

    def test_trend_uses_euros_for_totals_and_per_capita(self):
        trend = _format_trend_text("DEU", 0.5, 1000, {2023: 1130, 2024: 2260}, 0.36)
        self.assertNotIn("$", trend)
        self.assertIn("\u20ac203/cap", trend)
        self.assertIn("\u20ac407/cap", trend)

    def test_non_euro_metadata_is_rejected(self):
        invalid = deepcopy(self.snapshot)
        invalid["country_metadata"]["data"]["source"][0]["concept"][0]["variable"][0]["metatype"][0]["value"] = "US dollar"
        with self.assertRaisesRegex(RuntimeError, "confirmed EUR"):
            _world_bank_series(invalid)

    def test_missing_population_is_rejected_instead_of_using_usd_fallback(self):
        self.snapshot["responses"]["SP.POP.TOTL"]["data"][1] = []
        with self.assertRaisesRegex(RuntimeError, "matched euro"):
            _world_bank_series(self.snapshot)


if __name__ == "__main__":
    unittest.main()
