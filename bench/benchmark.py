#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from typing import Any

from flow_robot_bridge.runtime import Runtime


class FakeClient:
    def robot_path(self, robot_id: str) -> str:
        return "/v1/robots/" + robot_id

    def get(self, path: str) -> Any:
        return {"robot_id": path.rsplit("/", 1)[-1], "state_version": 1}

    def post(self, path: str, body: dict[str, Any]) -> Any:
        return body

runtime = Runtime(FakeClient(), FakeClient(), target_mode="mock")  # type: ignore[arg-type]
request = {"module": "observe-state", "input": {"robot_id": "mh-01-a"}}
iterations = 25_000
started = time.perf_counter()
for _ in range(iterations):
    runtime.dispatch(request)
elapsed = time.perf_counter() - started
ops = iterations / elapsed
result = {"iterations": iterations, "elapsed_seconds": round(elapsed, 6),
          "operations_per_second": round(ops, 2), "threshold": 10_000,
          "passed": ops >= 10_000}
print(json.dumps(result))
raise SystemExit(0 if result["passed"] else 1)
