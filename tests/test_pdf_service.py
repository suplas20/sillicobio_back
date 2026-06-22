import unittest

from app.services.pdf_service import _render_calc_view_html, _render_result_html, create_calc_view_pdf, create_result_pdf


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
