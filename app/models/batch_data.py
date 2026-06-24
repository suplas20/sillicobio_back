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
    sampling_time: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    od: Mapped[Decimal | None] = mapped_column(Numeric)
    feed_weight: Mapped[Decimal | None] = mapped_column(Numeric)
    broth_volume: Mapped[Decimal | None] = mapped_column(Numeric)
    target_prod_conc: Mapped[Decimal | None] = mapped_column(Numeric)
    glucose_conc: Mapped[Decimal | None] = mapped_column(Numeric)
    lycopene: Mapped[Decimal | None] = mapped_column(Numeric)
    a_carotene: Mapped[Decimal | None] = mapped_column(Numeric)
    b_carotene: Mapped[Decimal | None] = mapped_column(Numeric)
    citric_acid: Mapped[Decimal | None] = mapped_column(Numeric)
    pyruvic_acid: Mapped[Decimal | None] = mapped_column(Numeric)
    succinic_acid: Mapped[Decimal | None] = mapped_column(Numeric)
    lactic_acid: Mapped[Decimal | None] = mapped_column(Numeric)
    acetic_acid: Mapped[Decimal | None] = mapped_column(Numeric)
    reg_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    upd_dt: Mapped[datetime | None] = mapped_column(DateTime)
    upd_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))


TbBatchData = TbSampling
