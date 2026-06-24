import unittest
from decimal import Decimal

from app.services.pdf_service import (
    _pdf_value,
    _render_calc_view_html,
    _render_result_html,
    create_calc_view_pdf,
    create_result_pdf,
)


class PdfServiceTest(unittest.TestCase):
    def _sample_data(self):
        return {
            "batch": {
                "batchId": "LAB00001_BAT01",
                "planId": "LAB00001",
                "purpose": "test",
                "startDt": "2026-06-22",
                "params": {
                    "prepTime": 12,
                    "equipVol": 5,
                    "purifyYield": 0.8,
                    "dcwOdFactor": 0.1,
                    "feedGlucoseConc": 600,
                    "feedDensity": 1.2,
                    "feedGlucosePerFeed": 0.5,
                },
                "comparison": {"type": "BATCH", "targetBatchId": "LAB00001_BAT02"},
            },
            "plan": {"purpose": "test", "strain": "SB-LUT-01"},
            "researchers": [{"role": "OWNER", "id": "R001", "name": "Researcher"}],
            "files": {"doPh": {"fileName": "do-ph.csv"}, "co2O2": None, "ref": {"fileName": "ref.pdf"}},
            "sampling": [{"samplingTime": 0, "od": 0.2}],
            "compareBatchId": "LAB00001_BAT02",
            "compareSampling": [{"samplingTime": 0, "od": 0.1}],
            "calcFull": [{"sampling_time": 0, "compare_sampling_time": 0, "lutein": 0, "yield_pct": 0}],
            "calcSummary": {"age": 0, "compare_sampling_time": 0, "final_lutein": 0, "fn": 0.2},
        }

    def test_create_result_pdf_creates_pdf_bytes(self):
        pdf_bytes = create_result_pdf(self._sample_data())

        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 1000)

    def test_result_pdf_template_allows_full_table_rendering(self):
        html = _render_result_html(self._sample_data())

        self.assertIn("overflow: visible", html)
        self.assertIn("table-layout: fixed", html)
        self.assertIn("white-space: normal", html)
        self.assertNotIn("overflow: hidden", html)

    def test_create_calc_view_pdf_creates_pdf_bytes(self):
        pdf_bytes = create_calc_view_pdf(self._sample_data())

        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 1000)

    def test_calc_view_pdf_template_uses_batch_view_context(self):
        html = _render_calc_view_html(self._sample_data())

        self.assertIn("배치 기본 내용", html)
        self.assertIn("SB-LUT-01", html)
        self.assertIn("do-ph.csv", html)
        self.assertIn("LAB00001_BAT02", html)
        self.assertIn("비교배치 데이터", html)
        self.assertNotIn("overflow: hidden", html)

    def test_pdf_numeric_values_are_displayed_with_three_decimals(self):
        data = self._sample_data()
        data["batch"]["params"]["prepTime"] = Decimal("12.3455")
        data["sampling"] = [
            {
                "samplingTime": Decimal("1.2344"),
                "od": Decimal("2.2345"),
                "targetProdConc": Decimal("3"),
            }
        ]
        data["calcFull"] = [{"sampling_time": Decimal("4.2345"), "yield_pct": Decimal("5.2344")}]
        data["calcSummary"] = {"age": Decimal("6.2345"), "final_lutein": Decimal("7.2344"), "fn": Decimal("8")}

        html = _render_result_html(data)
        calc_view_html = _render_calc_view_html(data)

        self.assertIn("12.346", calc_view_html)
        self.assertIn("1.234", html)
        self.assertIn("2.235", html)
        self.assertIn("3.000", html)
        self.assertIn("4.235", html)
        self.assertIn("5.234", html)
        self.assertIn("6.235", html)
        self.assertIn("7.234", html)
        self.assertIn("8.000", html)

    def test_pdf_value_uses_half_up_rounding(self):
        self.assertEqual(_pdf_value(Decimal("1.2345")), "1.235")
        self.assertEqual(_pdf_value(Decimal("1.2344")), "1.234")
