from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TbSampling(Base):
    __tablename__ = "tb_sampling"
    __table_args__ = (UniqueConstraint("batch_id", "sampling_time"),)

    sample_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(40), ForeignKey("tb_batch.batch_id"), nullable=False)
    sampling_time: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    od: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    feed_weight: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    broth_volume: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    target_prod_conc: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    glucose_conc: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    lycopene: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    a_carotene: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    b_carotene: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    citric_acid: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    pyruvic_acid: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    succinic_acid: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    lactic_acid: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    acetic_acid: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    reg_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    upd_dt: Mapped[datetime | None] = mapped_column(DateTime)
    upd_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))


TbBatchData = TbSampling
