import unittest

from app.services.pdf_service import create_result_pdf


class PdfServiceTest(unittest.TestCase):
    def test_create_result_pdf_creates_pdf_bytes(self):
        data = {
            "batch": {"batchId": "LAB00001_BAT01", "planId": "LAB00001", "purpose": "test"},
            "researchers": [{"role": "OWNER", "id": "R001", "name": "Researcher"}],
            "sampling": [{"samplingTime": 0, "od": 0.2}],
            "calcFull": [{"sampling_time": 0, "lutein": 0, "yield_pct": 0}],
            "calcSummary": {"age": 0, "final_lutein": 0},
        }

        pdf_bytes = create_result_pdf(data)

        self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))
