import pytest

from orchestrator.health_engine import (
    calculate_health_score,
    classify_health,
    evaluate_health,
)


def test_healthy_score():
    signals = {
        "pod": 90,
        "application": 90,
        "dependency": 90,
        "security": 90,
    }
    assert calculate_health_score(signals) == 90
    assert classify_health(90) == "HEALTHY"


def test_weighted_score():
    signals = {
        "pod": 100,
        "application": 80,
        "dependency": 60,
        "security": 40,
    }
    assert calculate_health_score(signals) == 72


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (85, "HEALTHY"),
        (70, "DEGRADED"),
        (50, "UNHEALTHY"),
        (20, "CRITICAL"),
    ],
)
def test_health_classification(score, expected):
    assert classify_health(score) == expected


def test_invalid_signal_is_rejected():
    signals = {
        "pod": 110,
        "application": 80,
        "dependency": 80,
        "security": 80,
    }
    with pytest.raises(ValueError):
        calculate_health_score(signals)


def test_decision_record():
    signals = {
        "pod": 90,
        "application": 90,
        "dependency": 90,
        "security": 90,
    }
    result = evaluate_health(signals)
    assert result["health_state"] == "HEALTHY"
    assert result["proposed_action"] == "NO_ACTION"
    assert "timestamp" in result


from orchestrator.health_engine import HysteresisMonitor


def test_hysteresis_ignores_single_bad_sample():
    monitor = HysteresisMonitor()
    assert monitor.observe(40)["event"] == "NO_CHANGE"
    assert monitor.active is False


def test_hysteresis_triggers_after_three_bad_samples():
    monitor = HysteresisMonitor()
    monitor.observe(40)
    monitor.observe(35)
    result = monitor.observe(30)
    assert result["event"] == "TRIGGER"
    assert result["active"] is True


def test_hysteresis_recovers_after_two_good_samples():
    monitor = HysteresisMonitor()
    for score in [40, 40, 40]:
        monitor.observe(score)

    assert monitor.observe(80)["event"] == "NO_CHANGE"
    result = monitor.observe(85)
    assert result["event"] == "RECOVER"
    assert result["active"] is False


def test_hysteresis_resets_bad_counter_on_good_sample():
    monitor = HysteresisMonitor()
    monitor.observe(40)
    result = monitor.observe(80)
    assert result["bad_samples"] == 0
    assert result["active"] is False


def test_hysteresis_rejects_invalid_score():
    monitor = HysteresisMonitor()
    with pytest.raises(ValueError):
        monitor.observe(101)


import json
from orchestrator.decision_engine import OrchestratorEngine


def test_transient_problem_does_not_recommend_remediation(tmp_path):
    engine = OrchestratorEngine(tmp_path / "audit.jsonl")
    signals = {
        "pod": 40,
        "application": 40,
        "dependency": 40,
        "security": 40,
    }

    result = engine.evaluate(signals)

    assert result["hysteresis"]["event"] == "NO_CHANGE"
    assert result["action"] == "NO_ACTION"
    assert result["execution_mode"] == "DRY_RUN"


def test_sustained_problem_recommends_dry_run_remediation(tmp_path):
    engine = OrchestratorEngine(tmp_path / "audit.jsonl")
    signals = {
        "pod": 40,
        "application": 40,
        "dependency": 40,
        "security": 40,
    }

    engine.evaluate(signals)
    engine.evaluate(signals)
    result = engine.evaluate(signals)

    assert result["hysteresis"]["event"] == "TRIGGER"
    assert result["action"] == "DRY_RUN_REMEDIATION_RECOMMENDED"
    assert result["execution_mode"] == "DRY_RUN"


def test_decisions_are_written_to_audit_log(tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    engine = OrchestratorEngine(audit_path)
    signals = {
        "pod": 90,
        "application": 90,
        "dependency": 90,
        "security": 90,
    }

    engine.evaluate(signals)
    records = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]

    assert len(records) == 1
    assert records[0]["health_state"] == "HEALTHY"
    assert records[0]["execution_mode"] == "DRY_RUN"


def test_critical_problem_requires_manual_approval(tmp_path):
    engine = OrchestratorEngine(tmp_path / "audit.jsonl")
    signals = {
        "pod": 10,
        "application": 10,
        "dependency": 10,
        "security": 10,
    }

    engine.evaluate(signals)
    engine.evaluate(signals)
    result = engine.evaluate(signals)

    assert result["health_state"] == "CRITICAL"
    assert result["action"] == "ESCALATE_FOR_MANUAL_APPROVAL"
    assert result["execution_mode"] == "DRY_RUN"


from orchestrator.run_live import build_live_signals


def test_live_signals_mark_unknown_sources():
    telemetry = {
        "pods": [
            {"ready": True, "restart_count": 0},
            {"ready": True, "restart_count": 0},
        ],
        "backend_health": "healthy",
    }

    result = build_live_signals(telemetry)

    assert result["composite_score"] == 100
    assert result["coverage"] == "2 of 4 signals measured"
    assert result["unknown_signals"] == ["dependency", "security"]


def test_unready_pod_reduces_live_score():
    telemetry = {
        "pods": [
            {"ready": True, "restart_count": 0},
            {"ready": False, "restart_count": 0},
        ],
        "backend_health": "healthy",
    }

    result = build_live_signals(telemetry)

    assert result["signals"]["pod"] == 30
    assert result["composite_score"] < 100


def test_restarts_reduce_pod_signal():
    telemetry = {
        "pods": [
            {"ready": True, "restart_count": 2},
        ],
        "backend_health": "healthy",
    }

    result = build_live_signals(telemetry)

    assert result["signals"]["pod"] == 70


def test_missing_pods_are_rejected():
    telemetry = {"pods": [], "backend_health": "healthy"}

    import pytest
    with pytest.raises(ValueError):
        build_live_signals(telemetry)
