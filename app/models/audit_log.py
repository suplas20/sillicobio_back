from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TbAuditLog(Base):
    __tablename__ = "tb_audit_log"

    log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_table: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[str | None] = mapped_column(String(100))
    request_method: Mapped[str | None] = mapped_column(String(10))
    request_path: Mapped[str | None] = mapped_column(String(300))
    before_data: Mapped[str | None] = mapped_column(Text)
    after_data: Mapped[str | None] = mapped_column(Text)
    client_ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    reg_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("tb_member.member_id"))
    reg_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
