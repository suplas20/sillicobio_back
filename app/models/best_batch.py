from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TbBestBatch(Base):
    __tablename__ = "tb_best_batch"

    best_batch_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    exp_id: Mapped[str] = mapped_column(String(20), nullable=False)
    batch_id: Mapped[str] = mapped_column(String(40), ForeignKey("tb_batch.batch_id"), nullable=False)
    sort_ord: Mapped[int | None] = mapped_column(Integer)
    reg_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))
    reg_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    upd_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))
    upd_dt: Mapped[datetime | None] = mapped_column(DateTime)
