import json
from pathlib import Path

from orchestrator.health_engine import HysteresisMonitor

SAMPLE_INTERVAL_SECONDS = 5

# Synthetic test data: no live workload is disrupted.
samples = [
    ("baseline", 100),
    ("fault", 45),
    ("fault", 45),
    ("fault", 45),
    ("continued_fault", 50),
    ("recovery", 80),
    ("recovery", 85),
]

monitor = HysteresisMonitor()
results = []
trigger_time = None
recovery_time = None

for index, (scenario, score) in enumerate(samples):
    simulated_time = index * SAMPLE_INTERVAL_SECONDS
    observation = monitor.observe(score)

    if observation["event"] == "TRIGGER":
        trigger_time = simulated_time

    if observation["event"] == "RECOVER":
        recovery_time = simulated_time

    results.append({
        "simulated_time_seconds": simulated_time,
        "scenario": scenario,
        "score": score,
        **observation,
    })

report = {
    "experiment": "CloudMart health hysteresis simulation",
    "data_type": "SYNTHETIC_NOT_LIVE_MEASUREMENTS",
    "sample_interval_seconds": SAMPLE_INTERVAL_SECONDS,
    "trigger_time_seconds": trigger_time,
    "recovery_time_seconds": recovery_time,
    "detection_delay_seconds": (
        trigger_time - SAMPLE_INTERVAL_SECONDS
        if trigger_time is not None else None
    ),
    "recovery_confirmation_delay_seconds": (
        recovery_time - next(
            r["simulated_time_seconds"]
            for r in results
            if r["scenario"] == "recovery"
        )
        if recovery_time is not None else None
    ),
    "results": results,
}

output = Path("orchestrator/fault-experiment-report.json")
output.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
print(f"\nReport saved to: {output}")
