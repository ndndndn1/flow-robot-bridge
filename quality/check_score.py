#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

source = Path(__file__).with_name("scorecard.json")
scorecard = json.loads(source.read_text(encoding="utf-8"))
maximum = sum(item["max"] for item in scorecard["categories"])
earned = sum(item["earned"] for item in scorecard["categories"])
if maximum != 100 or earned != scorecard["score"] or earned < scorecard["target"]:
    raise SystemExit("invalid quality score")
if not scorecard["hard_gates"] or not all(scorecard["hard_gates"].values()):
    raise SystemExit("quality hard gate is not satisfied")
if any(not item["evidence"] for item in scorecard["categories"]):
    raise SystemExit("quality evidence is missing")
print(json.dumps({"score": earned, "target": scorecard["target"], "passed": True}))
