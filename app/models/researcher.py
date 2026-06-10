from datetime import datetime

from sqlalchemy import CHAR, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TbResearcher(Base):
    __tablename__ = "tb_researcher"

    researcher_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    researcher_nm: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100))
    tel: Mapped[str | None] = mapped_column(String(20))
    use_yn: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    reg_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reg_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))
    upd_dt: Mapped[datetime | None] = mapped_column(DateTime)
    upd_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))
