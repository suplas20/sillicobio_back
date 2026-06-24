from datetime import datetime
from decimal import Decimal
import unittest

from app.api.v1.endpoints.batches import _calc_full_response, _calc_summary_response
from app.models.calc_full import TbCalcFull
from app.models.calc_summary import TbCalcSummary


class CalcResponseTooltipTest(unittest.TestCase):
    def test_batch_calc_full_response_includes_raw_tooltip_values(self):
        row = TbCalcFull(
            calc_id=1,
            batch_id="BATCH01",
            sample_id=10,
            age=Decimal("1.23456"),
            yield_pct=Decimal("2.34567"),
            calc_dt=datetime(2026, 6, 24, 12, 0, 0),
        )
        compare_meta = {
            "compare_sampling_time": Decimal("3.45678"),
            "abs_yield_up": Decimal("4.56789"),
        }

        response = _calc_full_response(row, compare_meta, Decimal("5.67891"))

        self.assertEqual(response["tooltips"]["age"], "1.23456")
        self.assertEqual(response["tooltips"]["yield_pct"], "2.34567")
        self.assertEqual(response["tooltips"]["sampling_time"], "5.67891")
        self.assertEqual(response["tooltips"]["compare_sampling_time"], "3.45678")
        self.assertEqual(response["tooltips"]["abs_yield_up"], "4.56789")

    def test_batch_calc_summary_response_includes_raw_tooltip_values(self):
        row = TbCalcSummary(
            batch_id="BATCH01",
            age=Decimal("1.23456"),
            final_lutein=Decimal("2.34567"),
            calc_dt=datetime(2026, 6, 24, 12, 0, 0),
        )

        response = _calc_summary_response(row, compare_meta={"prod_up": Decimal("3.45678")})

        self.assertEqual(response["tooltips"]["age"], "1.23456")
        self.assertEqual(response["tooltips"]["final_lutein"], "2.34567")
        self.assertEqual(response["tooltips"]["prod_up"], "3.45678")


if __name__ == "__main__":
    unittest.main()
