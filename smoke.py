#!/usr/bin/env python3
from __future__ import annotations

import json
from urllib.request import urlopen

BASE_URL = "http://127.0.0.1:18094"

with urlopen(BASE_URL + "/healthz", timeout=5) as response:
    health = json.load(response)
assert health["status"] == "ok"
assert health["modules"] == [
    "generate-policy-dataset",
    "observe-state",
    "submit-safe-command",
    "validate-adapter",
]

with urlopen(BASE_URL + "/v1/modules", timeout=5) as response:
    catalog = json.load(response)
refs = {module["ref"] for module in catalog["modules"]}
assert refs == {
    "flow-robot-bridge/generate-policy-dataset@1.0.0",
    "flow-robot-bridge/observe-state@1.0.0",
    "flow-robot-bridge/submit-safe-command@1.0.0",
    "flow-robot-bridge/validate-adapter@1.0.0",
}
print("flow robot bridge health and catalog smoke passed")
