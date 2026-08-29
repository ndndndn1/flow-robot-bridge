from __future__ import annotations

from typing import Any

import pytest

from flow_robot_bridge.client import BridgeError
from flow_robot_bridge.runtime import Runtime


class FakeClient:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, Any]]] = []

    def robot_path(self, robot_id: str) -> str:
        return "/v1/robots/" + robot_id

    def get(self, path: str) -> Any:
        if path == "/v1/products":
            return [{"product_id": "mock-humanoid-mh-01"}]
        if path == "/v1/robots":
            return [{"robot_id": "mh-01-a"}]
        return {"robot_id": path.rsplit("/", 1)[-1], "state_version": 2}

    def post(self, path: str, body: dict[str, Any]) -> Any:
        self.posts.append((path, body))
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


@pytest.mark.parametrize("envelope", [{}, {"module": "observe-state", "input": []}])
def test_invalid_envelopes_fail_closed(envelope: dict[str, Any]) -> None:
    subject, _, _ = runtime(target_mode="mock")
    with pytest.raises(BridgeError) as raised:
        subject.dispatch(envelope)
    assert raised.value.status == 400
