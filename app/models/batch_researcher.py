from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TbBatchResearcher(Base):
    __tablename__ = "tb_batch_researcher"
    __table_args__ = (UniqueConstraint("batch_id", "researcher_id", "researcher_role"),)

    seq: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(40), ForeignKey("tb_batch.batch_id"), nullable=False)
    researcher_id: Mapped[str] = mapped_column(String(20), ForeignKey("tb_researcher.researcher_id"), nullable=False)
    researcher_role: Mapped[str] = mapped_column(String(20), nullable=False)
    reg_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reg_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))
