from io import BytesIO
import unittest
from zipfile import ZipFile

from app.services.pdf_service import create_results_pdf_zip


class PdfServiceTest(unittest.TestCase):
    def test_create_results_pdf_zip_creates_one_pdf_per_batch(self):
        data = [
            {
                "batch": {"batchId": "LAB00001_BAT01", "planId": "LAB00001", "purpose": "test"},
                "researchers": [{"role": "OWNER", "id": "R001", "name": "Researcher"}],
                "sampling": [{"samplingTime": 0, "od": 0.2}],
                "calcFull": [{"sampling_time": 0, "lutein": 0, "yield_pct": 0}],
                "calcSummary": {"age": 0, "final_lutein": 0},
            },
            {
                "batch": {"batchId": "LAB00001_BAT02", "planId": "LAB00001", "purpose": "test"},
                "researchers": [],
                "sampling": [],
                "calcFull": [],
                "calcSummary": {},
            },
        ]

        zip_bytes = create_results_pdf_zip(data)

        with ZipFile(BytesIO(zip_bytes)) as archive:
            self.assertEqual(archive.namelist(), ["LAB00001_BAT01.pdf", "LAB00001_BAT02.pdf"])
            self.assertTrue(archive.read("LAB00001_BAT01.pdf").startswith(b"%PDF-1.4"))
            self.assertTrue(archive.read("LAB00001_BAT02.pdf").startswith(b"%PDF-1.4"))
