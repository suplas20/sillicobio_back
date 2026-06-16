"""add calculation fields

Revision ID: 20260615_0002
Revises: 20260615_0001
Create Date: 2026-06-15 00:00:00.000000
"""

from alembic import op


revision = "20260615_0002"
down_revision = "20260615_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tb_batch
        ADD COLUMN IF NOT EXISTS calc_sample_id bigint
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_tb_batch_calc_sample'
            ) THEN
                ALTER TABLE tb_batch
                ADD CONSTRAINT fk_tb_batch_calc_sample
                FOREIGN KEY (calc_sample_id) REFERENCES tb_sampling(sample_id);
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        ALTER TABLE tb_calc_full
        ADD COLUMN IF NOT EXISTS compare_sample_id bigint,
        ADD COLUMN IF NOT EXISTS compare_age numeric(7, 2),
        ADD COLUMN IF NOT EXISTS compare_time_diff numeric(7, 2)
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_tb_calc_full_compare_sample'
            ) THEN
                ALTER TABLE tb_calc_full
                ADD CONSTRAINT fk_tb_calc_full_compare_sample
                FOREIGN KEY (compare_sample_id) REFERENCES tb_sampling(sample_id);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE tb_calc_full DROP CONSTRAINT IF EXISTS fk_tb_calc_full_compare_sample")
    op.execute("ALTER TABLE tb_calc_full DROP COLUMN IF EXISTS compare_time_diff")
    op.execute("ALTER TABLE tb_calc_full DROP COLUMN IF EXISTS compare_age")
    op.execute("ALTER TABLE tb_calc_full DROP COLUMN IF EXISTS compare_sample_id")
    op.execute("ALTER TABLE tb_batch DROP CONSTRAINT IF EXISTS fk_tb_batch_calc_sample")
    op.execute("ALTER TABLE tb_batch DROP COLUMN IF EXISTS calc_sample_id")
