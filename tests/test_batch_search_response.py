from datetime import datetime
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.endpoints.batches import _batch_search_response, search_batches
from app.db.database import Base
import app.models  # noqa: F401
from app.models.batch import TbBatch
from app.models.best_batch import TbBestBatch
from app.models.experiment import TbExpPlan


class BatchSearchResponseTest(unittest.TestCase):
    def test_batch_search_response_includes_best_registered_at(self):
        response = _batch_search_response(
            {
                "batch_id": "BATCH01",
                "exp_id": "PLAN01",
                "batch_no": "01",
                "is_best": True,
                "best_registered_at": datetime(2026, 6, 10, 9, 30, 0),
                "last_sampled_at": datetime(2026, 6, 9, 10, 20, 0),
                "sampling_time": None,
                "od": None,
                "feed_weight": None,
                "broth_volume": None,
                "target_prod_conc": None,
                "glucose_conc": None,
                "lycopene": None,
                "a_carotene": None,
                "b_carotene": None,
                "citric_acid": None,
                "pyruvic_acid": None,
                "succinic_acid": None,
                "lactic_acid": None,
                "acetic_acid": None,
            }
        )

        self.assertEqual(response["best_registered_at"], "2026-06-10 09:30:00")

    def test_batch_search_response_uses_null_for_non_best_registered_at(self):
        response = _batch_search_response(
            {
                "batch_id": "BATCH01",
                "exp_id": "PLAN01",
                "batch_no": "01",
                "is_best": False,
                "best_registered_at": None,
                "last_sampled_at": None,
                "sampling_time": None,
                "od": None,
                "feed_weight": None,
                "broth_volume": None,
                "target_prod_conc": None,
                "glucose_conc": None,
                "lycopene": None,
                "a_carotene": None,
                "b_carotene": None,
                "citric_acid": None,
                "pyruvic_acid": None,
                "succinic_acid": None,
                "lactic_acid": None,
                "acetic_acid": None,
            }
        )

        self.assertIsNone(response["best_registered_at"])

    def test_search_batches_returns_all_best_registration_times_but_marks_latest_current_best(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            db.add(TbExpPlan(exp_id="PLAN01", purpose="Purpose", reg_dt=datetime(2026, 6, 1, 9, 0, 0)))
            db.add_all(
                [
                    TbBatch(batch_id="BATCH_OLD", exp_id="PLAN01", batch_no="01", reg_dt=datetime(2026, 6, 1, 10, 0, 0)),
                    TbBatch(batch_id="BATCH_NEW", exp_id="PLAN01", batch_no="02", reg_dt=datetime(2026, 6, 1, 11, 0, 0)),
                    TbBatch(batch_id="BATCH_NONE", exp_id="PLAN01", batch_no="03", reg_dt=datetime(2026, 6, 1, 12, 0, 0)),
                ]
            )
            db.add_all(
                [
                    TbBestBatch(
                        best_batch_id=1,
                        exp_id="PLAN01",
                        batch_id="BATCH_OLD",
                        sort_ord=1,
                        reg_dt=datetime(2026, 6, 10, 9, 0, 0),
                    ),
                    TbBestBatch(
                        best_batch_id=2,
                        exp_id="PLAN01",
                        batch_id="BATCH_NEW",
                        sort_ord=2,
                        reg_dt=datetime(2026, 6, 11, 9, 0, 0),
                    ),
                ]
            )
            db.commit()

            response = search_batches(db=db, _=object(), page=1, limit=10)

        items = {item["batch_id"]: item for item in response["items"]}
        self.assertFalse(items["BATCH_OLD"]["is_best"])
        self.assertEqual(items["BATCH_OLD"]["best_registered_at"], "2026-06-10 09:00:00")
        self.assertTrue(items["BATCH_NEW"]["is_best"])
        self.assertEqual(items["BATCH_NEW"]["best_registered_at"], "2026-06-11 09:00:00")
        self.assertFalse(items["BATCH_NONE"]["is_best"])
        self.assertIsNone(items["BATCH_NONE"]["best_registered_at"])


if __name__ == "__main__":
    unittest.main()
