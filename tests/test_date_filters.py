import unittest
from datetime import date, datetime

from fastapi import HTTPException

from app.utils.date_filters import date_range, datetime_range, parse_date_filter


class DateFilterTest(unittest.TestCase):
    def test_parse_accepts_compact_and_dash_formats(self):
        self.assertEqual(parse_date_filter("20260601", "createdFrom"), date(2026, 6, 1))
        self.assertEqual(parse_date_filter("2026-06-01", "createdFrom"), date(2026, 6, 1))

    def test_datetime_range_uses_exclusive_next_day_end(self):
        start, end = datetime_range("20260601", "20260607", "createdFrom", "createdTo")

        self.assertEqual(start, datetime(2026, 6, 1))
        self.assertEqual(end, datetime(2026, 6, 8))

    def test_date_range_rejects_inverted_range(self):
        with self.assertRaises(HTTPException) as ctx:
            date_range("20260607", "20260601", "startDtFrom", "startDtTo")

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail["code"], "INVALID_DATE_RANGE")


if __name__ == "__main__":
    unittest.main()
