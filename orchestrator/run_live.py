import json
from pathlib import Path

from orchestrator.health_engine import (
    HysteresisMonitor,
    SIGNAL_WEIGHTS,
    calculate_health_score,
)
from orchestrator.telemetry_adapter import collect_telemetry


def build_live_signals(telemetry):
    """Convert verified observations into transparent signal scores."""
    pods = telemetry["pods"]

    if not pods:
        raise ValueError("No pod observations available")

    if not all(pod["ready"] for pod in pods):
        pod_score = 30
    elif any(pod["restart_count"] > 0 for pod in pods):
        pod_score = 70
    else:
        pod_score = 100

    backend = telemetry["backend_health"]
    application_score = 100 if backend == "healthy" else 0

    # These are the only two signals currently measured.
    # Unknown database and security signals are intentionally excluded.
    signals = {
        "pod": pod_score,
        "application": application_score,
    }

    measured_weights = {
        key: SIGNAL_WEIGHTS[key] for key in signals
    }
    total = sum(measured_weights.values())
    normalized_weights = {
        key: value / total
        for key, value in measured_weights.items()
    }

    score = calculate_health_score(signals, normalized_weights)

    return {
        "signals": signals,
        "weights_used": normalized_weights,
        "composite_score": score,
        "coverage": "2 of 4 signals measured",
        "unknown_signals": ["dependency", "security"],
    }


def main():
    telemetry = collect_telemetry()
    assessment = build_live_signals(telemetry)

    report = {
        "telemetry": telemetry,
        "assessment": assessment,
        "mode": "OBSERVE_ONLY",
        "note": (
            "Partial score based on pod readiness/restarts and backend "
            "health only. No automated remediation is performed."
        ),
    }

    audit_path = Path("orchestrator/live-observations.jsonl")
    with audit_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(report) + "\n")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
