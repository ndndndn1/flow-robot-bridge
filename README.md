# Flow Robot Bridge

`flow-robot-bridge` connects the generic `flow-runner` contract to replaceable robot and
simulation services. It does not implement a robot driver and it never accepts an upstream URL
from workflow input. Deployment-owned environment variables select the trusted services.

## Targets, inputs, and outputs

| Module | Software target | Input | Output |
| --- | --- | --- | --- |
| `observe-state` | `physical-robot-interface` | `robot_id` | Canonical `RobotState` |
| `submit-safe-command` | physical mock or explicitly approved adapter | Canonical physical command | Target mode and `CommandRecord` |
| `generate-policy-dataset` | `simulation-robot-learning-data` | Bounded scenario request | Dataset manifest plus inline records or artifact metadata |
| `generate-perception-dataset` | simulation `mock`, MuJoCo, or Isaac worker | Scenario, backend, capture/randomization and idempotency key | Asynchronous dataset job metadata |
| `get-robot-job` | simulation job service | Job kind and ID | Generation, BC-RNN training, or evaluation job state |
| `train-imitation-policy` | simulation BC-RNN trainer | Dataset ID and bounded hyperparameters | Asynchronous model job metadata |
| `evaluate-policy` | simulation policy evaluator | Model ID and dataset ID | Asynchronous metrics job metadata |
| `validate-calibration` | deployment-owned ROS action gateway | GridFS/MCAP observation reference and TF frame metadata | Calibration action result |
| `infer-pose-grasps` | deployment-owned ROS perception gateway | Frame-bundle reference and approved calibration/policy identities | 6DoF pose and grasp result |
| `request-execution-intent` | `application-robot-operations` | Recorded result/grasp, live state version, expiry, actor | Pending auditable intent |
| `validate-adapter` | physical adapter conformance surface | Empty object | Product/robot inventory and named checks |

The command bridge starts in `mock` mode. Setting `ROBOT_TARGET_MODE=real` is insufficient by
itself: `ROBOT_ALLOW_REAL=true` is also required after hardware safety approval. A software
`protective_stop` is not a certified hardware emergency-stop circuit.

Large RGB-D, stereo, LiDAR, MCAP, Zarr, HDF5, model, and checkpoint bytes are never accepted by
the bridge. Flow inputs carry only bounded IDs, SHA-256 identities, media types, and control
parameters; storage and transfer stay with simulation/GridFS/model storage. The embedded target is
an HTTP-to-ROS action gateway owned by the private deployment. It maps only to the documented
`CalibrateExtrinsics`/perception interfaces and must not expose arbitrary ROS topic or action names.

## Run

Start the physical and simulation mock services on `robot-net`, then:

```bash
docker compose up --build -d --wait
curl -fsS http://127.0.0.1:18094/v1/modules
curl -fsS http://127.0.0.1:18094/v1/run \
  -H 'content-type: application/json' \
  -d '{"module":"observe-state","input":{"robot_id":"mh-01-a"}}'
docker compose stop
```

`POST /v1/run` returns the common runner envelope with `schema_version`, `run_id`, `module`,
`output`, and metadata-only `lineage`; the module-specific value is always under `output`.

The service also accepts fully versioned refs such as
`flow-robot-bridge/observe-state@1.0.0`. Synchronous dataset requests are capped at 2,000 records;
larger generation belongs to the simulation service's native async job API. Requests have a 2 MiB
limit and each upstream call has a five-second timeout.

## Develop and verify

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/ruff check .
PYTHONPATH=src .venv/bin/python bench/benchmark.py
python3 quality/check_score.py
docker compose config --quiet
```

See [enterprise requirements](docs/enterprise-requirements.md) and
[operations](docs/operations.md) for failure handling, resource limits, and adapter rollout.
