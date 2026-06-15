"""add tb_best_batch

Revision ID: 20260615_0001
Revises:
Create Date: 2026-06-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260615_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_best_batch",
        sa.Column("best_batch_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("exp_id", sa.String(length=20), nullable=False),
        sa.Column("batch_id", sa.String(length=40), nullable=False),
        sa.Column("sort_ord", sa.Integer(), nullable=True),
        sa.Column("reg_id", sa.String(length=20), nullable=True),
        sa.Column("reg_dt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("upd_id", sa.String(length=20), nullable=True),
        sa.Column("upd_dt", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["tb_batch.batch_id"], name="fk_tb_best_batch_batch"),
        sa.ForeignKeyConstraint(["reg_id"], ["tb_member.member_id"]),
        sa.ForeignKeyConstraint(["upd_id"], ["tb_member.member_id"]),
        sa.PrimaryKeyConstraint("best_batch_id"),
    )
    op.execute(
        "COMMENT ON TABLE tb_best_batch IS "
        "'베스트 배치 등록 정보. 통합/배치별 비교배치 선택창에서 상단 고정 노출되는 배치 목록'"
    )
    op.execute("COMMENT ON COLUMN tb_best_batch.best_batch_id IS '베스트 배치 등록 고유 ID'")
    op.execute("COMMENT ON COLUMN tb_best_batch.exp_id IS '실험 ID. 베스트로 등록된 배치가 속한 실험 ID'")
    op.execute("COMMENT ON COLUMN tb_best_batch.batch_id IS '배치 ID. 베스트로 등록된 배치 ID'")
    op.execute("COMMENT ON COLUMN tb_best_batch.sort_ord IS '정렬 순서. 베스트 배치 상단 노출 순서'")
    op.execute("COMMENT ON COLUMN tb_best_batch.reg_id IS '등록자 ID'")
    op.execute("COMMENT ON COLUMN tb_best_batch.reg_dt IS '등록일시'")
    op.execute("COMMENT ON COLUMN tb_best_batch.upd_id IS '수정자 ID'")
    op.execute("COMMENT ON COLUMN tb_best_batch.upd_dt IS '수정일시'")


def downgrade() -> None:
    op.drop_table("tb_best_batch")
