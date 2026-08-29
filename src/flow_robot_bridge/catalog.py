from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0.0"
REPOSITORY = "flow-robot-bridge"


def object_schema(
    properties: dict[str, Any], required: list[str] | None = None, *, additional: bool = False
) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": additional,
    }
    if required:
        schema["required"] = required
    return schema


STRING = {"type": "string"}
INTEGER = {"type": "integer"}
NUMBER = {"type": "number"}
BOOLEAN = {"type": "boolean"}
OPEN_OBJECT = {"type": "object", "additionalProperties": True}
OPEN_ARRAY = {"type": "array", "items": OPEN_OBJECT}

COMMAND_INPUT = object_schema(
    {
        "contract_version": {"const": "1.0.0"},
        "command_id": {"type": "string", "format": "uuid"},
        "robot_id": STRING,
        "issued_at": {"type": "string", "format": "date-time"},
        "expires_at": {"type": "string", "format": "date-time"},
        "expected_state_version": {"type": "integer", "minimum": 0},
        "action": OPEN_OBJECT,
    },
    [
        "contract_version",
        "command_id",
        "robot_id",
        "issued_at",
        "expires_at",
        "expected_state_version",
        "action",
    ],
)

DATASET_INPUT = object_schema(
    {
        "schema_version": {"const": "1.0"},
        "scenario_id": STRING,
        "product_profile": {"enum": ["MH-01", "MM-01"]},
        "seed": {"type": "integer", "minimum": 0, "maximum": 4294967295},
        "episodes": {"type": "integer", "minimum": 1, "maximum": 100},
        "steps_per_episode": {"type": "integer", "minimum": 1, "maximum": 1000},
        "task": {"enum": ["navigate", "manipulate"]},
        "sensors": {
            "type": "array",
            "items": {"enum": ["joint_state", "imu", "rgbd", "force_torque", "lidar"]},
            "uniqueItems": True,
            "maxItems": 5,
        },
    },
    [
        "schema_version",
        "scenario_id",
        "product_profile",
        "seed",
        "episodes",
        "steps_per_episode",
        "task",
        "sensors",
    ],
)

MODULES = [
    {
        "id": "observe-state",
        "ref": f"{REPOSITORY}/observe-state@1.0.0",
        "schema_version": SCHEMA_VERSION,
        "input_schema": object_schema({"robot_id": STRING}, ["robot_id"]),
        "output_schema": object_schema({"state": OPEN_OBJECT}, ["state"]),
    },
    {
        "id": "submit-safe-command",
        "ref": f"{REPOSITORY}/submit-safe-command@1.0.0",
        "schema_version": SCHEMA_VERSION,
        "input_schema": COMMAND_INPUT,
        "output_schema": object_schema(
            {"target_mode": STRING, "command": OPEN_OBJECT}, ["target_mode", "command"]
        ),
    },
    {
        "id": "generate-policy-dataset",
        "ref": f"{REPOSITORY}/generate-policy-dataset@1.0.0",
        "schema_version": SCHEMA_VERSION,
        "input_schema": DATASET_INPUT,
        "output_schema": object_schema(
            {"manifest": OPEN_OBJECT, "records": {"type": ["array", "null"]},
             "artifact": {"type": ["object", "null"]}},
            ["manifest", "records", "artifact"],
        ),
    },
    {
        "id": "validate-adapter",
        "ref": f"{REPOSITORY}/validate-adapter@1.0.0",
        "schema_version": SCHEMA_VERSION,
        "input_schema": object_schema({}),
        "output_schema": object_schema(
            {"valid": BOOLEAN, "products": OPEN_ARRAY, "robots": OPEN_ARRAY, "checks": OPEN_ARRAY},
            ["valid", "products", "robots", "checks"],
        ),
    },
]

CATALOG = {"schema_version": SCHEMA_VERSION, "modules": MODULES}
MODULES_BY_ID = {item["id"]: item for item in MODULES}
MODULES_BY_REF = {item["ref"]: item for item in MODULES}
