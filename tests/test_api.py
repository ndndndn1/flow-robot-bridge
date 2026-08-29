from __future__ import annotations

import pytest

from flow_robot_bridge.api import dispatch_request, run_envelope, run_identity
from flow_robot_bridge.client import BridgeError


def test_run_response_uses_common_flow_runner_envelope() -> None:
    result = run_envelope(
        {"run_id": "run-17", "module": "observe-state"},
        {"state": {"robot_id": "mh-01-a"}},
    )
    assert result == {
        "schema_version": "1.0.0",
        "run_id": "run-17",
        "module": "observe-state",
        "output": {"state": {"robot_id": "mh-01-a"}},
        "lineage": {"run_id": "run-17", "module": "observe-state"},
    }


@pytest.mark.parametrize("run_id", ["", 17, "x" * 129])
def test_run_response_rejects_invalid_run_id(run_id: object) -> None:
    with pytest.raises(BridgeError, match="run_id"):
        run_identity({"run_id": run_id, "module": "observe-state"})


def test_invalid_run_id_is_rejected_before_runtime_side_effects() -> None:
    class SideEffectRuntime:
        called = False

        def dispatch(self, request: dict[str, object]) -> dict[str, object]:
            self.called = True
            return {}

    runtime = SideEffectRuntime()
    with pytest.raises(BridgeError, match="run_id"):
        dispatch_request(
            {"run_id": "", "module": "submit-safe-command", "input": {}},
            runtime,  # type: ignore[arg-type]
        )
    assert runtime.called is False
