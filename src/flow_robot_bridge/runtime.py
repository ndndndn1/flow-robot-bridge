from __future__ import annotations

import os
from typing import Any

from .catalog import MODULES_BY_ID, MODULES_BY_REF
from .client import BridgeError, JsonHttpClient

MAX_INLINE_RECORDS = 2_000


class Runtime:
    def __init__(
        self,
        physical: JsonHttpClient | None = None,
        simulation: JsonHttpClient | None = None,
        *,
        target_mode: str | None = None,
        allow_real: bool | None = None,
    ) -> None:
        self.physical = physical or JsonHttpClient(
            os.getenv("PHYSICAL_ROBOT_URL", "http://physical-robot-interface:8080")
        )
        self.simulation = simulation or JsonHttpClient(
            os.getenv("SIMULATION_ROBOT_URL", "http://simulation-robot-learning-data:8080")
        )
        self.target_mode = target_mode or os.getenv("ROBOT_TARGET_MODE", "mock")
        self.allow_real = (
            allow_real
            if allow_real is not None
            else os.getenv("ROBOT_ALLOW_REAL", "false").casefold() == "true"
        )
        if self.target_mode not in {"mock", "real"}:
            raise ValueError("ROBOT_TARGET_MODE must be mock or real")

    def dispatch(self, envelope: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(envelope, dict) or not isinstance(envelope.get("input"), dict):
            raise BridgeError(400, "invalid_envelope", "input must be an object")
        requested = str(envelope.get("module", ""))
        module = MODULES_BY_ID.get(requested) or MODULES_BY_REF.get(requested)
        if module is None:
            raise BridgeError(404, "unknown_module", f"unknown module: {requested}")
        value = envelope["input"]
        module_id = module["id"]
        if module_id == "observe-state":
            robot_id = require_string(value, "robot_id")
            return {"state": self.physical.get(self.physical.robot_path(robot_id))}
        if module_id == "submit-safe-command":
            self._require_command_authority()
            require_string(value, "robot_id")
            require_string(value, "command_id")
            return {"target_mode": self.target_mode,
                    "command": self.physical.post("/v1/commands", value)}
        if module_id == "generate-policy-dataset":
            records = int(value.get("episodes", 0)) * int(value.get("steps_per_episode", 0))
            if records < 1 or records > MAX_INLINE_RECORDS:
                raise BridgeError(
                    422,
                    "dataset_size_out_of_range",
                    "flow datasets must contain 1..2000 records; use native async jobs for larger runs",
                )
            result = self.simulation.post("/v1/datasets", value)
            if not isinstance(result, dict):
                raise BridgeError(502, "invalid_upstream", "simulation result must be an object")
            return result
        products = self.physical.get("/v1/products")
        robots = self.physical.get("/v1/robots")
        checks = [
            {"name": "products_nonempty", "passed": isinstance(products, list) and bool(products)},
            {"name": "robots_nonempty", "passed": isinstance(robots, list) and bool(robots)},
            {"name": "target_guard", "passed": self.target_mode == "mock" or self.allow_real},
        ]
        return {"valid": all(item["passed"] for item in checks), "products": products,
                "robots": robots, "checks": checks}

    def _require_command_authority(self) -> None:
        if self.target_mode == "real" and not self.allow_real:
            raise BridgeError(
                403,
                "real_target_disabled",
                "real robot commands require ROBOT_ALLOW_REAL=true after hardware safety approval",
            )


def require_string(value: dict[str, Any], field: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item or len(item) > 128:
        raise BridgeError(422, "invalid_input", f"{field} must be a bounded non-empty string")
    return item
