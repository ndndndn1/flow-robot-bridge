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
ID = {"type": "string", "minLength": 1, "maxLength": 128,
      "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]*$"}
SHA256 = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
ARTIFACT_REF = object_schema(
    {"artifact_id": ID, "sha256": SHA256, "media_type": STRING},
    ["artifact_id", "sha256", "media_type"],
)

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

PERCEPTION_DATASET_INPUT = object_schema(
    {
        "schema_version": {"const": "2.0"},
        "idempotency_key": ID,
        "scenario_id": ID,
        "asset_set_id": {"const": "public-primitives-v1"},
        "product_profile": {"enum": ["MH-01", "MM-01"]},
        "seed": {"type": "integer", "minimum": 0, "maximum": 4294967295},
        "backend": {"enum": ["mock", "mujoco", "isaac_sim"]},
        "task": {"enum": ["navigate", "manipulate"]},
        "episodes": {"type": "integer", "minimum": 1, "maximum": 100},
        "frames_per_episode": {"type": "integer", "minimum": 1, "maximum": 2000},
        "capture": OPEN_OBJECT,
        "randomization": OPEN_OBJECT,
    },
    ["schema_version", "idempotency_key", "scenario_id", "asset_set_id",
     "product_profile", "seed", "backend", "task", "episodes", "frames_per_episode"],
)

TRAINING_INPUT = object_schema(
    {
        "idempotency_key": ID,
        "dataset_id": ID,
        "sequence_length": {"type": "integer", "minimum": 2, "maximum": 256},
        "hidden_dim": {"type": "integer", "minimum": 8, "maximum": 2048},
        "ridge": {"type": "number", "minimum": 0, "maximum": 1},
        "seed": {"type": "integer", "minimum": 0, "maximum": 4294967295},
    },
    ["idempotency_key", "dataset_id"],
)

EVALUATION_INPUT = object_schema(
    {
        "idempotency_key": ID,
        "model_id": ID,
        "dataset_id": ID,
        "sequence_length": {"type": "integer", "minimum": 2, "maximum": 256},
    },
    ["idempotency_key", "model_id", "dataset_id"],
)

CALIBRATION_INPUT = object_schema(
    {
        "robot_id": ID,
        "product_id": ID,
        "sensor_rig_id": ID,
        "parent_frame": ID,
        "child_frame": ID,
        "observation_artifact": ARTIFACT_REF,
        "method": {"enum": ["stereo_hand_eye", "target_board", "factory_fixture"]},
    },
    ["robot_id", "product_id", "sensor_rig_id", "parent_frame", "child_frame",
     "observation_artifact", "method"],
)

INFERENCE_INPUT = object_schema(
    {
        "robot_id": ID,
        "product_id": ID,
        "scene_sequence": {"type": "integer", "minimum": 0},
        "calibration_id": ID,
        "calibration_sha256": SHA256,
        "policy_id": ID,
        "policy_sha256": SHA256,
        "frame_bundle": ARTIFACT_REF,
    },
    ["robot_id", "product_id", "scene_sequence", "calibration_id",
     "calibration_sha256", "policy_id", "policy_sha256", "frame_bundle"],
)

INTENT_INPUT = object_schema(
    {
        "schema_version": {"const": "1.0.0"},
        "intent_id": ID,
        "result_id": ID,
        "grasp_id": ID,
        "robot_id": ID,
        "expected_state_version": {"type": "integer", "minimum": 0},
        "expires_at": {"type": "string", "format": "date-time"},
        "actor": {"type": "string", "minLength": 1, "maxLength": 128},
    },
    ["schema_version", "intent_id", "result_id", "grasp_id", "robot_id",
     "expected_state_version", "expires_at", "actor"],
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
        "id": "generate-perception-dataset",
        "ref": f"{REPOSITORY}/generate-perception-dataset@1.0.0",
        "schema_version": SCHEMA_VERSION,
        "input_schema": PERCEPTION_DATASET_INPUT,
        "output_schema": object_schema({"job": OPEN_OBJECT}, ["job"]),
    },
    {
        "id": "get-robot-job",
        "ref": f"{REPOSITORY}/get-robot-job@1.0.0",
        "schema_version": SCHEMA_VERSION,
        "input_schema": object_schema(
            {"job_kind": {"enum": ["generation", "training", "evaluation"]}, "job_id": ID},
            ["job_kind", "job_id"],
        ),
        "output_schema": object_schema({"job": OPEN_OBJECT}, ["job"]),
    },
    {
        "id": "train-imitation-policy",
        "ref": f"{REPOSITORY}/train-imitation-policy@1.0.0",
        "schema_version": SCHEMA_VERSION,
        "input_schema": TRAINING_INPUT,
        "output_schema": object_schema({"job": OPEN_OBJECT}, ["job"]),
    },
    {
        "id": "evaluate-policy",
        "ref": f"{REPOSITORY}/evaluate-policy@1.0.0",
        "schema_version": SCHEMA_VERSION,
        "input_schema": EVALUATION_INPUT,
        "output_schema": object_schema({"job": OPEN_OBJECT}, ["job"]),
    },
    {
        "id": "validate-calibration",
        "ref": f"{REPOSITORY}/validate-calibration@1.0.0",
        "schema_version": SCHEMA_VERSION,
        "input_schema": CALIBRATION_INPUT,
        "output_schema": object_schema({"calibration": OPEN_OBJECT}, ["calibration"]),
    },
    {
        "id": "infer-pose-grasps",
        "ref": f"{REPOSITORY}/infer-pose-grasps@1.0.0",
        "schema_version": SCHEMA_VERSION,
        "input_schema": INFERENCE_INPUT,
        "output_schema": object_schema({"perception_result": OPEN_OBJECT}, ["perception_result"]),
    },
    {
        "id": "request-execution-intent",
        "ref": f"{REPOSITORY}/request-execution-intent@1.0.0",
        "schema_version": SCHEMA_VERSION,
        "input_schema": INTENT_INPUT,
        "output_schema": object_schema({"intent": OPEN_OBJECT}, ["intent"]),
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
