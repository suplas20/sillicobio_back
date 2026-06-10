from datetime import datetime

from sqlalchemy import BigInteger, CHAR, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TbExpFile(Base):
    __tablename__ = "tb_exp_file"

    file_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    exp_id: Mapped[str] = mapped_column(String(20), ForeignKey("tb_exp_plan.exp_id"), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    origin_file_nm: Mapped[str] = mapped_column(String(255), nullable=False)
    save_file_nm: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    use_yn: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    reg_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reg_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))
