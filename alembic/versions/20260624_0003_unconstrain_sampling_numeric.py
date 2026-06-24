"""unconstrain sampling numeric scale

Revision ID: 20260624_0003
Revises: 20260615_0002
Create Date: 2026-06-24 00:00:00.000000
"""

from alembic import op


revision = "20260624_0003"
down_revision = "20260615_0002"
branch_labels = None
depends_on = None


SAMPLING_NUMERIC_COLUMNS = (
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
)


def upgrade() -> None:
    for column in SAMPLING_NUMERIC_COLUMNS:
        op.execute(f"ALTER TABLE tb_sampling ALTER COLUMN {column} TYPE numeric")


def downgrade() -> None:
    column_types = {
        "sampling_time": "numeric(7, 2)",
        "od": "numeric(10, 2)",
        "feed_weight": "numeric(12, 2)",
        "broth_volume": "numeric(8, 2)",
        "target_prod_conc": "numeric(10, 4)",
        "glucose_conc": "numeric(10, 2)",
        "lycopene": "numeric(10, 4)",
        "a_carotene": "numeric(10, 4)",
        "b_carotene": "numeric(10, 4)",
        "citric_acid": "numeric(10, 4)",
        "pyruvic_acid": "numeric(10, 4)",
        "succinic_acid": "numeric(10, 4)",
        "lactic_acid": "numeric(10, 4)",
        "acetic_acid": "numeric(10, 4)",
    }
    for column, column_type in column_types.items():
        op.execute(f"ALTER TABLE tb_sampling ALTER COLUMN {column} TYPE {column_type}")
