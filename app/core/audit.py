from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.client_ip import get_client_ip
from app.db.session import SessionLocal
from app.models.audit_log import TbAuditLog


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        actor_before = _session_member_id(request)
        response = await call_next(request)
        if _should_log(request, response.status_code):
            actor_after = _session_member_id(request)
            _write_audit_log(request, actor_after or actor_before)
        return response


def _session_member_id(request: Request) -> str | None:
    if "session" not in request.scope:
        return None
    return request.session.get("member_id")


def _should_log(request: Request, status_code: int) -> bool:
    if status_code >= 400:
        return False
    path = request.url.path
    if not path.startswith("/api/v1/"):
        return False
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        return True
    return request.method == "GET" and ("/files/" in path or path.endswith("/calc-view"))


def _write_audit_log(request: Request, actor_id: str | None) -> None:
    db = SessionLocal()
    try:
        target_table, target_id = _target(request.url.path)
        db.add(
            TbAuditLog(
                action_type=_action_type(request.method, request.url.path),
                target_table=target_table,
                target_id=target_id,
                request_method=request.method,
                request_path=request.url.path,
                client_ip=get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
                reg_id=actor_id,
                reg_dt=datetime.now(),
            )
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()


def _action_type(method: str, path: str) -> str:
    if path.endswith("/auth/login"):
        return "LOGIN"
    if path.endswith("/auth/logout"):
        return "LOGOUT"
    if method == "GET" and "/files/" in path:
        return "DOWNLOAD"
    if method == "GET" and path.endswith("/calc-view"):
        return "CALC_VIEW"
    if method == "DELETE":
        return "DELETE"
    if method == "POST" and "/files" in path:
        return "UPLOAD"
    if method == "POST":
        return "CREATE"
    if method in {"PUT", "PATCH"}:
        return "UPDATE"
    return method


def _target(path: str) -> tuple[str | None, str | None]:
    parts = [part for part in path.split("/") if part]
    if len(parts) < 3 or parts[:2] != ["api", "v1"]:
        return None, None

    resource = parts[2]
    resource_id = parts[3] if len(parts) > 3 else None
    target_tables = {
        "auth": "tb_member",
        "members": "tb_member",
        "researchers": "tb_researcher",
        "plans": "tb_exp_plan",
        "experiments": "tb_exp_plan",
        "batches": "tb_batch",
        "batch-data": "tb_sampling",
        "results": "tb_batch",
        "attachments": None,
    }
    target_table = target_tables.get(resource)

    if resource == "auth":
        return target_table, None
    if resource == "batches" and "sampling" in parts:
        sampling_index = parts.index("sampling")
        if len(parts) > sampling_index + 1:
            return "tb_sampling", parts[sampling_index + 1]
        return "tb_sampling", resource_id
    if resource == "batches" and "files" in parts:
        return "tb_batch_file", resource_id
    if resource == "plans" and "files" in parts:
        return "tb_exp_file", resource_id
    return target_table, resource_id
