import unittest

from app.services.pdf_service import _render_result_html, create_result_pdf


class PdfServiceTest(unittest.TestCase):
    def _sample_data(self):
        return {
            "batch": {"batchId": "LAB00001_BAT01", "planId": "LAB00001", "purpose": "test"},
            "researchers": [{"role": "OWNER", "id": "R001", "name": "Researcher"}],
            "sampling": [{"samplingTime": 0, "od": 0.2}],
            "calcFull": [{"sampling_time": 0, "lutein": 0, "yield_pct": 0}],
            "calcSummary": {"age": 0, "final_lutein": 0},
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
