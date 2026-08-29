from __future__ import annotations

import argparse
import json
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from .catalog import CATALOG, MODULES_BY_ID
from .client import BridgeError
from .runtime import Runtime

MAX_REQUEST_BYTES = 2 * 1024 * 1024
RUNTIME = Runtime()


def run_identity(request: dict[str, object]) -> tuple[str, str]:
    requested_run_id = request.get("run_id")
    if requested_run_id is not None and (
        not isinstance(requested_run_id, str) or not requested_run_id or len(requested_run_id) > 128
    ):
        raise BridgeError(400, "invalid_envelope", "run_id must be a bounded non-empty string")
    run_id = requested_run_id or str(uuid.uuid4())
    module = str(request.get("module", ""))
    return run_id, module


def run_envelope(request: dict[str, object], output: dict[str, object]) -> dict[str, object]:
    run_id, module = run_identity(request)
    return {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "module": module,
        "output": output,
        "lineage": {"run_id": run_id, "module": module},
    }


def dispatch_request(request: dict[str, object], runtime: Runtime = RUNTIME) -> dict[str, object]:
    run_identity(request)
    return run_envelope(request, runtime.dispatch(request))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/healthz":
            self._send(200, {"status": "ok", "modules": sorted(MODULES_BY_ID)})
        elif path == "/v1/modules":
            self._send(200, CATALOG)
        elif path.startswith("/v1/modules/"):
            module = MODULES_BY_ID.get(unquote(path.removeprefix("/v1/modules/")))
            self._send(200, module) if module else self._send(404, {"error": "module not found"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/v1/run":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("content-length", "0"))
            if length < 1 or length > MAX_REQUEST_BYTES:
                raise BridgeError(413, "request_too_large", "request size is outside allowed bounds")
            payload = json.loads(self.rfile.read(length))
            self._send(200, dispatch_request(payload))
        except BridgeError as error:
            self._send(error.status, {"error": {"code": error.code, "message": str(error)}})
        except (ValueError, json.JSONDecodeError) as error:
            self._send(400, {"error": {"code": "invalid_json", "message": str(error)}})

    def log_message(self, format: str, *args: object) -> None:
        return


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the flow robot bridge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
