import json

from flow_robot_bridge.catalog import CATALOG, MODULES_BY_ID


def test_catalog_has_unique_versioned_refs_and_strict_inputs() -> None:
    refs = [module["ref"] for module in CATALOG["modules"]]
    assert len(refs) == len(set(refs)) == 4
    assert all(ref.startswith("flow-robot-bridge/") and ref.endswith("@1.0.0") for ref in refs)
    assert all(module["input_schema"]["additionalProperties"] is False
               for module in CATALOG["modules"])
    json.dumps(CATALOG)
    assert set(MODULES_BY_ID) == {
        "observe-state", "submit-safe-command", "generate-policy-dataset", "validate-adapter"
    }
