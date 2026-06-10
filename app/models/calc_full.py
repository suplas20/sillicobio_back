from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TbCalcFull(Base):
    __tablename__ = "tb_calc_full"

    calc_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(40), ForeignKey("tb_batch.batch_id"), nullable=False)
    sample_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("tb_sampling.sample_id"))
    age: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    lutein: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
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
    current_od: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    max_od: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    delta_od: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    lycopene: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    a_carotene: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    b_carotene: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    citric_acid: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    pyruvic_acid: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    succinic_acid: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    lactic_acid: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    acetic_acid: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    calc_version: Mapped[str | None] = mapped_column(String(20))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    calc_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
