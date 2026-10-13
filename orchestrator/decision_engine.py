import json
from pathlib import Path

from orchestrator.health_engine import (
    HysteresisMonitor,
    evaluate_health,
)


class OrchestratorEngine:
    """Evaluate health and record safe, dry-run decisions."""

    def __init__(self, audit_path="orchestrator/audit.jsonl"):
        self.monitor = HysteresisMonitor()
        self.audit_path = Path(audit_path)

    def evaluate(self, signals):
        result = evaluate_health(signals)
        hysteresis = self.monitor.observe(result["composite_score"])

        state = result["health_state"]
        event = hysteresis["event"]

        if event == "TRIGGER":
            action = (
                "ESCALATE_FOR_MANUAL_APPROVAL"
                if state == "CRITICAL"
                else "DRY_RUN_REMEDIATION_RECOMMENDED"
            )
        elif event == "RECOVER":
            action = "RECOVERY_CONFIRMED"
        else:
            action = "NO_ACTION"

        record = {
            **result,
            "hysteresis": hysteresis,
            "action": action,
            "execution_mode": "DRY_RUN",
        }

        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record) + "\n")

        return record
