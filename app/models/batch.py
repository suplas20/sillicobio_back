from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CHAR, Computed, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TbBatch(Base):
    __tablename__ = "tb_batch"
    __table_args__ = (UniqueConstraint("exp_id", "batch_no"),)

    batch_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    exp_id: Mapped[str] = mapped_column(String(20), ForeignKey("tb_exp_plan.exp_id"), nullable=False)
    batch_no: Mapped[str] = mapped_column(CHAR(2), nullable=False)
    start_dt: Mapped[date | None] = mapped_column(Date)
    prep_time: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    equip_vol: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    purify_yield: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    dcw_od_factor: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    feed_glucose_conc: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    feed_density: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    feed_glucose_per_feed: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
        Computed("feed_glucose_conc / NULLIF(feed_density * 1000, 0)"),
    )
    cmp_type: Mapped[str | None] = mapped_column(String(10))
    cmp_batch_id: Mapped[str | None] = mapped_column(String(40), ForeignKey("tb_batch.batch_id"))
    reg_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    upd_dt: Mapped[datetime | None] = mapped_column(DateTime)
    upd_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))
