from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TbCalcSummary(Base):
    __tablename__ = "tb_calc_summary"

    batch_id: Mapped[str] = mapped_column(String(40), ForeignKey("tb_batch.batch_id"), primary_key=True)
    age: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    final_lutein: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    max_lutein: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    yield_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    productivity: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    production: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    abs_yield_up: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    prod_up: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    ts: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    o_i: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    scr: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    sscr: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    yx_s: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    max_od: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    fn: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    delta_od: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    final_lycopene: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    final_a_carotene: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    final_b_carotene: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    final_citric: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    final_pyruvic: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    final_succinic: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    final_lactic: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    final_acetic: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    calc_version: Mapped[str | None] = mapped_column(String(20))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    calc_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
