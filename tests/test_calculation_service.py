from decimal import Decimal
from types import SimpleNamespace
import unittest

from app.services.calculation_service import _apply_compare, _calculate_full_rows


class CalculationServiceTest(unittest.TestCase):
    def test_substrate_uses_initial_feed_weight_minus_current_feed_weight(self):
        batch = SimpleNamespace(
            batch_id="BATCH01",
            feed_glucose_conc=Decimal("100"),
            feed_density=Decimal("1"),
            dcw_od_factor=Decimal("1"),
            prep_time=Decimal("0"),
            equip_vol=Decimal("1"),
            purify_yield=Decimal("1"),
        )
        samplings = [
            _sampling(1, Decimal("0"), Decimal("1"), Decimal("10"), Decimal("1"), Decimal("0")),
            _sampling(2, Decimal("10"), Decimal("2"), Decimal("8"), Decimal("1"), Decimal("2")),
        ]

        rows = _calculate_full_rows(batch, samplings)

        self.assertGreater(rows[1]["yield_pct"], 0)
        self.assertGreater(rows[1]["ts"], 0)
        self.assertGreater(rows[1]["scr"], 0)
        self.assertGreater(rows[1]["sscr"], 0)
        self.assertGreater(rows[0]["yx_s"], 0)
        self.assertEqual(rows[1]["yield_pct"], Decimal("1000"))
        self.assertEqual(rows[1]["ts"], Decimal("0.02"))
        self.assertEqual(rows[1]["scr"], Decimal("0.02"))

    def test_substrate_follows_formula_without_forcing_positive_value(self):
        batch = SimpleNamespace(
            batch_id="BATCH01",
            feed_glucose_conc=Decimal("100"),
            feed_density=Decimal("1"),
            dcw_od_factor=Decimal("1"),
            prep_time=Decimal("0"),
            equip_vol=Decimal("1"),
            purify_yield=Decimal("1"),
        )
        samplings = [
            _sampling(1, Decimal("0"), Decimal("1"), Decimal("0"), Decimal("1"), Decimal("0")),
            _sampling(2, Decimal("10"), Decimal("2"), Decimal("2"), Decimal("1"), Decimal("2")),
        ]

        rows = _calculate_full_rows(batch, samplings)

        self.assertLess(rows[1]["yield_pct"], 0)
        self.assertLess(rows[1]["ts"], 0)
        self.assertLess(rows[1]["scr"], 0)
        self.assertLess(rows[1]["sscr"], 0)

    def test_compare_uses_one_hour_match_and_forces_last_row_to_last_compare_sample(self):
        current_batch = _batch("BATCH01")
        compare_batch = _batch("BATCH02")
        current_rows = _calculate_full_rows(
            current_batch,
            [
                _sampling(1, Decimal("10"), Decimal("1"), Decimal("10"), Decimal("1"), Decimal("1"), "BATCH01"),
                _sampling(2, Decimal("20"), Decimal("1"), Decimal("8"), Decimal("1"), Decimal("1"), "BATCH01"),
                _sampling(3, Decimal("30"), Decimal("1"), Decimal("7"), Decimal("1"), Decimal("1"), "BATCH01"),
            ],
        )
        compare_rows = _calculate_full_rows(
            compare_batch,
            [
                _sampling(11, Decimal("10.5"), Decimal("1"), Decimal("10"), Decimal("1"), Decimal("1"), "BATCH02"),
                _sampling(12, Decimal("90"), Decimal("1"), Decimal("8"), Decimal("1"), Decimal("1"), "BATCH02"),
            ],
        )

        _apply_compare(current_rows, compare_rows)

        self.assertEqual(current_rows[0]["compare_sample_id"], 11)
        self.assertEqual(current_rows[0]["compare_sampling_time"], Decimal("10.5"))
        self.assertIsNone(current_rows[1]["compare_sample_id"])
        self.assertIsNone(current_rows[1]["compare_sampling_time"])
        self.assertEqual(current_rows[2]["compare_sample_id"], 12)
        self.assertEqual(current_rows[2]["compare_sampling_time"], Decimal("90"))
        self.assertEqual(current_rows[2]["compare_time_diff"], Decimal("60"))


def _batch(batch_id):
    return SimpleNamespace(
        batch_id=batch_id,
        feed_glucose_conc=Decimal("100"),
        feed_density=Decimal("1"),
        dcw_od_factor=Decimal("1"),
        prep_time=Decimal("0"),
        equip_vol=Decimal("1"),
        purify_yield=Decimal("1"),
    )


def _sampling(sample_id, sampling_time, od, feed_weight, broth_volume, target_prod_conc, batch_id="BATCH01"):
    return SimpleNamespace(
        sample_id=sample_id,
        batch_id=batch_id,
        sampling_time=sampling_time,
        od=od,
        feed_weight=feed_weight,
        broth_volume=broth_volume,
        target_prod_conc=target_prod_conc,
        glucose_conc=None,
        lycopene=None,
        a_carotene=None,
        b_carotene=None,
        citric_acid=None,
        pyruvic_acid=None,
        succinic_acid=None,
        lactic_acid=None,
        acetic_acid=None,
    )
