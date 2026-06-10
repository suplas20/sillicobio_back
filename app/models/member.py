from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TbMember(Base):
    __tablename__ = "tb_member"

    member_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    member_nm: Mapped[str] = mapped_column(String(50), nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    role_cd: Mapped[str] = mapped_column(String(10), nullable=False)
    last_login_dt: Mapped[datetime | None] = mapped_column(DateTime)
    last_login_ip: Mapped[str | None] = mapped_column(String(45))
    reg_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reg_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))
    upd_dt: Mapped[datetime | None] = mapped_column(DateTime)
    upd_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))
