# Operations

Run the bridge only while a workflow needs it. Bind the standalone port to `127.0.0.1`; in the
private flow stack, keep module traffic on the internal `flow-net` and robot traffic on the internal
`robot-net`. The standalone service joins the host-standard Squid network only for controlled
egress and does not receive an externally reachable port.

1. Start and health-check the physical and simulation targets.
2. Run `validate-adapter` and require every named check to pass.
3. Start the bridge in `mock` mode and run an observe, dataset, and protective-stop smoke.
4. Inspect container UID, read-only root filesystem, memory/PID limits, and request metrics at the
   surrounding runner/proxy boundary.
5. Stop the bridge after the workflow completes.

An upstream 4xx is returned as a bounded `upstream_rejected` response. Connection, timeout,
malformed JSON, or upstream 5xx failures become `502 upstream_unavailable`. Do not retry command
submissions with a different `command_id`; physical idempotency depends on preserving it.

Before a real adapter is enabled, document the robot product/model, isolated OT network, ROS domain
and namespace, DDS connectivity, watchdog, hardware E-stop validation, and conformance result.
Enable both real-target environment flags only for that bounded deployment window.
