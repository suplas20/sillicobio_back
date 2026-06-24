import unittest

from app.models.batch_data import TbSampling


class SamplingModelTest(unittest.TestCase):
    def test_sampling_numeric_columns_do_not_force_decimal_scale(self):
        for column_name in (
            "sampling_time",
            "od",
            "feed_weight",
            "broth_volume",
            "target_prod_conc",
            "glucose_conc",
            "lycopene",
            "a_carotene",
            "b_carotene",
            "citric_acid",
            "pyruvic_acid",
            "succinic_acid",
            "lactic_acid",
            "acetic_acid",
        ):
            column_type = TbSampling.__table__.c[column_name].type
            self.assertIsNone(column_type.scale, column_name)


if __name__ == "__main__":
    unittest.main()
