import unittest
from unittest.mock import patch

from starlette.datastructures import Headers
from starlette.requests import Request

from app.core.client_ip import _client_ip_from_headers, get_client_ip


def _request(client_host: str, headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers or [],
            "client": (client_host, 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )


class ClientIpTest(unittest.TestCase):
    def test_client_ip_from_x_forwarded_for_uses_first_valid_ip(self) -> None:
        headers = Headers({"x-forwarded-for": "unknown, 192.168.10.25, 10.0.0.5"})

        self.assertEqual(_client_ip_from_headers(headers), "192.168.10.25")

    def test_client_ip_from_forwarded_header(self) -> None:
        headers = Headers({"forwarded": 'for="172.16.0.15:5544";proto=http'})

        self.assertEqual(_client_ip_from_headers(headers), "172.16.0.15")

    def test_get_client_ip_uses_remote_host_when_not_local(self) -> None:
        request = _request("203.0.113.10")

        self.assertEqual(get_client_ip(request), "203.0.113.10")

    def test_get_client_ip_replaces_loopback_with_local_network_ip(self) -> None:
        request = _request("127.0.0.1")

        with patch("app.core.client_ip._local_network_ip", return_value="192.168.0.44"):
            self.assertEqual(get_client_ip(request), "192.168.0.44")


if __name__ == "__main__":
    unittest.main()
