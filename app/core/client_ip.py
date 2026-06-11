from collections.abc import Mapping
from ipaddress import ip_address
import socket

from starlette.requests import Request


CLIENT_IP_HEADERS = (
    "x-forwarded-for",
    "x-real-ip",
    "forwarded",
    "cf-connecting-ip",
    "true-client-ip",
    "x-client-ip",
    "client-ip",
)


def get_client_ip(request: Request) -> str | None:
    header_ip = _client_ip_from_headers(request.headers)
    if header_ip:
        return header_ip

    remote_host = request.client.host if request.client else None
    remote_ip = _normalize_ip(remote_host)
    if remote_ip and not _is_loopback(remote_ip):
        return remote_ip

    return _local_network_ip() or remote_ip


def _client_ip_from_headers(headers: Mapping[str, str]) -> str | None:
    for header in CLIENT_IP_HEADERS:
        value = headers.get(header)
        if not value:
            continue
        for candidate in _header_candidates(header, value):
            normalized = _normalize_ip(candidate)
            if normalized:
                return normalized
    return None


def _header_candidates(header: str, value: str) -> list[str]:
    if header == "forwarded":
        candidates: list[str] = []
        for forwarded_entry in value.split(","):
            for part in forwarded_entry.split(";"):
                key, separator, raw_value = part.strip().partition("=")
                if separator and key.lower() == "for":
                    candidates.append(raw_value)
        return candidates
    return [part.strip() for part in value.split(",")]


def _normalize_ip(value: str | None) -> str | None:
    if not value:
        return None

    candidate = value.strip().strip('"')
    if not candidate or candidate.lower() == "unknown":
        return None
    if candidate.lower() == "localhost":
        return "127.0.0.1"
    if candidate.startswith("[") and "]" in candidate:
        candidate = candidate[1 : candidate.index("]")]

    parsed = _parse_ip(candidate)
    if parsed:
        return parsed

    host, separator, port = candidate.rpartition(":")
    if separator and port.isdigit() and ":" not in host:
        return _parse_ip(host)

    return None


def _parse_ip(value: str) -> str | None:
    try:
        parsed = ip_address(value)
    except ValueError:
        return None
    if getattr(parsed, "ipv4_mapped", None):
        return str(parsed.ipv4_mapped)
    return str(parsed)


def _is_loopback(value: str) -> bool:
    try:
        return ip_address(value).is_loopback
    except ValueError:
        return value.lower() == "localhost"


def _local_network_ip() -> str | None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
        except OSError:
            local_ip = _hostname_ip()
    if local_ip and not _is_loopback(local_ip):
        return local_ip
    return None


def _hostname_ip() -> str | None:
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        return None
    return _normalize_ip(local_ip)
