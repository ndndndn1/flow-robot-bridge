from __future__ import annotations

from typing import Any

import pytest

from flow_robot_bridge.client import BridgeError
from flow_robot_bridge.runtime import Runtime


class FakeClient:
    def __init__(self) -> None:
        self.posts: list[tuple[Any, ...]] = []

    def robot_path(self, robot_id: str) -> str:
        return "/v1/robots/" + robot_id

    def get(self, path: str) -> Any:
        if path == "/v1/products":
            return [{"product_id": "mock-humanoid-mh-01"}]
        if path == "/v1/robots":
            return [{"robot_id": "mh-01-a"}]
        return {"robot_id": path.rsplit("/", 1)[-1], "state_version": 2}

    def post(self, path: str, body: dict[str, Any], **kwargs: Any) -> Any:
        self.posts.append((path, body) if not kwargs else (path, body, kwargs))
        if path == "/v1/datasets":
            return {"manifest": {"record_count": body["episodes"] * body["steps_per_episode"]},
                    "records": [], "artifact": None}
        return {"status": "accepted", "request": body}


def runtime(**kwargs: Any) -> tuple[Runtime, FakeClient, FakeClient]:
    physical, simulation = FakeClient(), FakeClient()
    return Runtime(physical, simulation, **kwargs), physical, simulation  # type: ignore[arg-type]


def test_observe_state_uses_bounded_robot_path() -> None:
    subject, _, _ = runtime(target_mode="mock")
    result = subject.dispatch({"module": "observe-state", "input": {"robot_id": "mh-01-a"}})
    assert result["state"]["robot_id"] == "mh-01-a"


def test_safe_command_preserves_physical_contract() -> None:
    subject, physical, _ = runtime(target_mode="mock")
    command = {"contract_version": "1.0.0", "command_id": "c-1", "robot_id": "mh-01-a",
               "issued_at": "2026-08-29T00:00:00Z", "expires_at": "2026-08-29T00:01:00Z",
               "expected_state_version": 0,
               "action": {"type": "protective_stop", "reason": "test"}}
    result = subject.dispatch({"module": "submit-safe-command", "input": command})
    assert result["target_mode"] == "mock"
    assert physical.posts == [("/v1/commands", command)]


def test_real_commands_fail_closed_without_explicit_gate() -> None:
    subject, _, _ = runtime(target_mode="real", allow_real=False)
    with pytest.raises(BridgeError, match="hardware safety approval") as raised:
        subject.dispatch({"module": "submit-safe-command",
                          "input": {"command_id": "c", "robot_id": "r"}})
    assert raised.value.status == 403


def test_dataset_is_bounded_to_runner_budget() -> None:
    subject, _, simulation = runtime(target_mode="mock")
    value = {"schema_version": "1.0", "scenario_id": "line-a", "product_profile": "MM-01",
             "seed": 7, "episodes": 2, "steps_per_episode": 10, "task": "navigate",
             "sensors": ["lidar"]}
    result = subject.dispatch({"module": "generate-policy-dataset", "input": value})
    assert result["manifest"]["record_count"] == 20
    assert simulation.posts[0][0] == "/v1/datasets"

    value["episodes"] = 3
    value["steps_per_episode"] = 1000
    with pytest.raises(BridgeError, match="native async jobs"):
        subject.dispatch({"module": "generate-policy-dataset", "input": value})


def test_adapter_validation_requires_products_and_robots() -> None:
    subject, _, _ = runtime(target_mode="mock")
    result = subject.dispatch({"module": "validate-adapter", "input": {}})
    assert result["valid"] is True
    assert all(check["passed"] for check in result["checks"])


def test_perception_generation_and_policy_jobs_forward_only_metadata() -> None:
    physical, simulation, embedded, application = (FakeClient() for _ in range(4))
    subject = Runtime(physical, simulation, embedded, application, target_mode="mock")  # type: ignore[arg-type]
    generated = subject.dispatch({"module": "generate-perception-dataset", "input": {
        "schema_version": "2.0", "idempotency_key": "run-1", "scenario_id": "bin-pick",
        "asset_set_id": "public-primitives-v1", "product_profile": "MM-01", "seed": 7,
        "backend": "mujoco", "task": "manipulate", "episodes": 2,
        "frames_per_episode": 10,
    }})
    assert generated["job"]["status"] == "accepted"
    assert simulation.posts[0][0] == "/v2/jobs"
    assert "idempotency_key" not in simulation.posts[0][1]
    assert simulation.posts[0][2]["headers"] == {"Idempotency-Key": "run-1"}

    subject.dispatch({"module": "train-imitation-policy", "input": {
        "idempotency_key": "train-1", "dataset_id": "dataset-1", "sequence_length": 16,
    }})
    subject.dispatch({"module": "evaluate-policy", "input": {
        "idempotency_key": "eval-1", "model_id": "model-1", "dataset_id": "dataset-1",
    }})
    assert [call[0] for call in simulation.posts[1:]] == [
        "/v2/training/jobs", "/v2/evaluation/jobs"
    ]


def test_calibration_inference_and_intent_use_owned_targets() -> None:
    physical, simulation, embedded, application = (FakeClient() for _ in range(4))
    subject = Runtime(physical, simulation, embedded, application, target_mode="mock")  # type: ignore[arg-type]
    artifact = {"artifact_id": "gridfs-1", "sha256": "a" * 64,
                "media_type": "application/vnd.mcap"}
    calibration = {"robot_id": "mm-01-a", "product_id": "mock-mobile-mm-01",
                   "sensor_rig_id": "rig-1", "parent_frame": "base_link",
                   "child_frame": "camera_link", "observation_artifact": artifact,
                   "method": "stereo_hand_eye"}
    subject.dispatch({"module": "validate-calibration", "input": calibration})
    assert embedded.posts[0][0] == "/v1/actions/calibrate-extrinsics"

    inference = {"robot_id": "mm-01-a", "product_id": "mock-mobile-mm-01",
                 "scene_sequence": 2, "calibration_id": "cal-1",
                 "calibration_sha256": "b" * 64, "policy_id": "policy-1",
                 "policy_sha256": "c" * 64, "frame_bundle": artifact}
    subject.dispatch({"module": "infer-pose-grasps", "input": inference})
    assert embedded.posts[1][0] == "/v1/perception/infer"

    intent = {"schema_version": "1.0.0", "intent_id": "intent-1",
              "result_id": "result-1", "grasp_id": "grasp-1", "robot_id": "mm-01-a",
              "expected_state_version": 0, "expires_at": "2027-01-01T00:00:00Z",
              "actor": "operator"}
    subject.dispatch({"module": "request-execution-intent", "input": intent})
    assert application.posts[0] == ("/api/v2/execution-intents", intent)


def test_raw_sensor_payload_is_rejected_at_bridge_boundary() -> None:
    physical, simulation, embedded, application = (FakeClient() for _ in range(4))
    subject = Runtime(physical, simulation, embedded, application, target_mode="mock")  # type: ignore[arg-type]
    with pytest.raises(BridgeError, match="raw payload"):
        subject.dispatch({"module": "infer-pose-grasps", "input": {
            "frame_bundle": {"artifact_id": "a", "sha256": "b" * 64,
                             "media_type": "application/json"},
            "rgb": "base64-not-allowed",
        }})


@pytest.mark.parametrize("envelope", [{}, {"module": "observe-state", "input": []}])
def test_invalid_envelopes_fail_closed(envelope: dict[str, Any]) -> None:
    subject, _, _ = runtime(target_mode="mock")
    with pytest.raises(BridgeError) as raised:
        subject.dispatch(envelope)
    assert raised.value.status == 400
