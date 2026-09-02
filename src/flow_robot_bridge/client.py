from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class BridgeError(RuntimeError):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


@dataclass(frozen=True)
class JsonHttpClient:
    base_url: str
    timeout_seconds: float = 5.0
    max_response_bytes: int = 8 * 1024 * 1024

    def get(self, path: str) -> Any:
        return self._exchange("GET", path, None)

    def post(
        self, path: str, body: dict[str, Any], *, headers: dict[str, str] | None = None
    ) -> Any:
        return self._exchange("POST", path, body, headers)

    def delete(self, path: str) -> Any:
        return self._exchange("DELETE", path, None)

    def robot_path(self, robot_id: str) -> str:
        return "/v1/robots/" + quote(robot_id, safe="")

    def _exchange(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        data = None if body is None else json.dumps(body, separators=(",", ":")).encode()
        headers = {"accept": "application/json", "content-type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        request = Request(
            self.base_url.rstrip("/") + path,
            method=method,
            data=data,
            headers=headers,
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                length = response.headers.get("content-length")
                if length and int(length) > self.max_response_bytes:
                    raise BridgeError(502, "upstream_too_large", "upstream response exceeds limit")
                payload = response.read(self.max_response_bytes + 1)
                if len(payload) > self.max_response_bytes:
                    raise BridgeError(502, "upstream_too_large", "upstream response exceeds limit")
                return json.loads(payload)
        except HTTPError as error:
            detail = error.read(1024).decode(errors="replace")
            status = error.code if 400 <= error.code < 500 else 502
            raise BridgeError(status, "upstream_rejected", detail or str(error)) from error
        except (URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
            raise BridgeError(502, "upstream_unavailable", str(error)) from error
