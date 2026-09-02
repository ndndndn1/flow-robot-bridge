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
        embedded: JsonHttpClient | None = None,
        application: JsonHttpClient | None = None,
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
        self.embedded = embedded or JsonHttpClient(
            os.getenv("EMBEDDED_ACTION_GATEWAY_URL", "http://embedded-action-gateway:8080")
        )
        self.application = application or JsonHttpClient(
            os.getenv("APPLICATION_ROBOT_URL", "http://application-robot-operations:8080")
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
        if module_id == "generate-perception-dataset":
            reject_unknown(value, {"schema_version", "idempotency_key", "scenario_id",
                                   "asset_set_id", "product_profile", "seed", "backend", "task",
                                   "episodes", "frames_per_episode", "capture", "randomization"})
            body, idempotency_key = body_with_idempotency(value)
            return {"job": self.simulation.post(
                "/v2/jobs", body, headers={"Idempotency-Key": idempotency_key}
            )}
        if module_id == "get-robot-job":
            reject_unknown(value, {"job_kind", "job_id"})
            kind = require_choice(value, "job_kind", {"generation", "training", "evaluation"})
            job_id = require_string(value, "job_id")
            paths = {
                "generation": "/v2/jobs/",
                "training": "/v2/training/jobs/",
                "evaluation": "/v2/evaluation/jobs/",
            }
            return {"job": self.simulation.get(paths[kind] + job_id)}
        if module_id == "train-imitation-policy":
            reject_unknown(value, {"idempotency_key", "dataset_id", "sequence_length",
                                   "hidden_dim", "ridge", "seed"})
            body, idempotency_key = body_with_idempotency(value)
            require_string(body, "dataset_id")
            return {"job": self.simulation.post(
                "/v2/training/jobs", body, headers={"Idempotency-Key": idempotency_key}
            )}
        if module_id == "evaluate-policy":
            reject_unknown(value, {"idempotency_key", "model_id", "dataset_id",
                                   "sequence_length"})
            body, idempotency_key = body_with_idempotency(value)
            require_string(body, "model_id")
            require_string(body, "dataset_id")
            return {"job": self.simulation.post(
                "/v2/evaluation/jobs", body, headers={"Idempotency-Key": idempotency_key}
            )}
        if module_id == "validate-calibration":
            require_artifact_reference(value, "observation_artifact")
            reject_binary_fields(value)
            return {"calibration": self.embedded.post("/v1/actions/calibrate-extrinsics", value)}
        if module_id == "infer-pose-grasps":
            require_artifact_reference(value, "frame_bundle")
            reject_binary_fields(value)
            return {"perception_result": self.embedded.post("/v1/perception/infer", value)}
        if module_id == "request-execution-intent":
            reject_unknown(value, {"schema_version", "intent_id", "result_id", "grasp_id",
                                   "robot_id", "expected_state_version", "expires_at", "actor"})
            return {"intent": self.application.post("/api/v2/execution-intents", value)}
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


def body_with_idempotency(value: dict[str, Any]) -> tuple[dict[str, Any], str]:
    body = dict(value)
    idempotency_key = require_string(body, "idempotency_key")
    del body["idempotency_key"]
    return body, idempotency_key


def reject_unknown(value: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise BridgeError(422, "unknown_fields", "unknown fields: " + ", ".join(unknown))


def require_choice(value: dict[str, Any], key: str, choices: set[str]) -> str:
    selected = require_string(value, key)
    if selected not in choices:
        raise BridgeError(422, "invalid_choice", f"{key} is not supported")
    return selected


def require_artifact_reference(value: dict[str, Any], key: str) -> None:
    reference = value.get(key)
    if not isinstance(reference, dict):
        raise BridgeError(422, "artifact_reference_required", f"{key} must be an object")
    reject_unknown(reference, {"artifact_id", "sha256", "media_type"})
    require_string(reference, "artifact_id")
    digest = require_string(reference, "sha256")
    require_string(reference, "media_type")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise BridgeError(422, "invalid_digest", f"{key}.sha256 must be lowercase SHA-256")


def reject_binary_fields(value: dict[str, Any]) -> None:
    forbidden = {"rgb", "depth", "image", "pointcloud", "model", "bytes", "data"}
    found = sorted(forbidden.intersection(value))
    if found:
        raise BridgeError(422, "raw_payload_forbidden", "raw payload fields are not accepted")


def require_string(value: dict[str, Any], field: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item or len(item) > 128:
        raise BridgeError(422, "invalid_input", f"{field} must be a bounded non-empty string")
    return item
