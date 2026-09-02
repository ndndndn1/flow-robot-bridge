# Enterprise requirements

## Functional and interface contract

- Advertise eleven versioned modules through `GET /v1/modules` and execute them only through
  `POST /v1/run`.
- Preserve canonical physical command and simulation dataset fields without silently renaming or
  dropping them.
- Resolve trusted physical, simulation, embedded action-gateway, and application base URLs from
  deployment configuration, never workflow input.
- Carry only artifact references across flow boundaries. Raw camera/point-cloud/model bytes are
  rejected; the embedded gateway maps fixed routes to documented ROS 2 actions and topics.
- Reject unknown modules, malformed envelopes, unbounded dataset requests, oversized requests,
  upstream errors, invalid JSON, and unauthorized real targets explicitly.

## Reliability, safety, and performance

- Default all command traffic to deterministic mock targets. Real traffic requires two independent
  deployment flags and remains subject to adapter and hardware safety validation.
- Bound request and response bodies, upstream timeouts, dataset record counts, container memory,
  processes, and CPU. HTTP worker threads terminate with the server and no background queue is used.
- A local dispatch benchmark must sustain at least 10,000 observe-state transformations per second
  on the host baseline. Runtime service latency is otherwise dominated by the configured adapters.
- A 30-minute external soak must show no growing thread count, pending queue, or more than 10%
  post-warmup RSS growth before an approved real-adapter deployment.

## Acceptance table

| Requirement | Evidence | Verification |
| --- | --- | --- |
| Runner contract | Versioned catalog and run envelope | Catalog and runtime tests |
| Physical isolation | Deployment-owned URL and canonical command pass-through | Runtime tests |
| Simulation bounds | 2,000-record synchronous ceiling | Dataset tests |
| Industrial async jobs | Idempotency-keyed generation, BC-RNN training/evaluation, and status routing | Runtime tests |
| Perception boundary | Artifact-reference-only calibration and inference calls to fixed trusted endpoints | Runtime raw-payload rejection test |
| Approved execution | Intent creation goes only to the application control plane; this bridge cannot approve it | Runtime target-routing test |
| Safe target gate | Mock default plus explicit real enablement | Real-target rejection test |
| Failure semantics | Status-preserving 4xx and bounded 502 responses | Client/runtime tests |
| Operational containment | Non-root, read-only, no capabilities, internal network | Compose and runtime inspection |
| Quality threshold | Machine-readable score of at least 80/100 | `quality/check_score.py` |

Inputs and outputs are reusable public contracts; no recruitment content, company text, private
identifiers, credentials, or workflow payloads are stored by this service.
