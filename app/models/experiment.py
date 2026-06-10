from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TbExpPlan(Base):
    __tablename__ = "tb_exp_plan"

    exp_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(200), nullable=False)
    content1: Mapped[str | None] = mapped_column(String(500))
    content2: Mapped[str | None] = mapped_column(String(500))
    content3: Mapped[str | None] = mapped_column(String(500))
    content4: Mapped[str | None] = mapped_column(String(500))
    strain_nm: Mapped[str | None] = mapped_column(String(100))
    cmp_batch_id: Mapped[str | None] = mapped_column(String(40), ForeignKey("tb_batch.batch_id"))
    result_content: Mapped[str | None] = mapped_column(Text)
    reg_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))
    reg_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    upd_dt: Mapped[datetime | None] = mapped_column(DateTime)
    upd_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))


TbExperiment = TbExpPlan
