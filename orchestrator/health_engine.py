from datetime import datetime, timezone

SIGNAL_WEIGHTS = {
    "pod": 0.25,
    "application": 0.30,
    "dependency": 0.25,
    "security": 0.20,
}


def calculate_health_score(signals, weights=None):
    """Calculate a weighted health score from 0 to 100."""
    weights = weights or SIGNAL_WEIGHTS

    if set(signals) != set(weights):
        raise ValueError("Signals and weights must have matching keys")

    if any(not 0 <= value <= 100 for value in signals.values()):
        raise ValueError("Signal scores must be between 0 and 100")

    if any(value < 0 for value in weights.values()):
        raise ValueError("Weights cannot be negative")

    if not abs(sum(weights.values()) - 1.0) < 1e-9:
        raise ValueError("Weights must sum to 1.0")

    return round(
        sum(signals[name] * weights[name] for name in weights), 2
    )


def classify_health(score):
    """Classify a composite health score."""
    if not 0 <= score <= 100:
        raise ValueError("Health score must be between 0 and 100")

    if score >= 80:
        return "HEALTHY"
    if score >= 60:
        return "DEGRADED"
    if score >= 40:
        return "UNHEALTHY"
    return "CRITICAL"


def evaluate_health(signals, weights=None):
    """Return an explainable health decision record."""
    score = calculate_health_score(signals, weights)
    state = classify_health(score)

    actions = {
        "HEALTHY": "NO_ACTION",
        "DEGRADED": "INCREASE_MONITORING",
        "UNHEALTHY": "PROPOSE_REMEDIATION",
        "CRITICAL": "ESCALATE_FOR_APPROVED_REMEDIATION",
    }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signals": dict(signals),
        "composite_score": score,
        "health_state": state,
        "proposed_action": actions[state],
        "reason": f"Composite health score is {score}/100 ({state})",
    }


class HysteresisMonitor:
    """Require consecutive bad/good samples before changing state."""

    def __init__(
        self,
        unhealthy_threshold=60,
        recovery_threshold=75,
        trigger_samples=3,
        recovery_samples=2,
    ):
        if not 0 <= unhealthy_threshold < recovery_threshold <= 100:
            raise ValueError("Invalid health thresholds")
        if trigger_samples < 1 or recovery_samples < 1:
            raise ValueError("Sample counts must be at least 1")

        self.unhealthy_threshold = unhealthy_threshold
        self.recovery_threshold = recovery_threshold
        self.trigger_samples = trigger_samples
        self.recovery_samples = recovery_samples
        self.active = False
        self.bad_count = 0
        self.good_count = 0

    def observe(self, score):
        if not 0 <= score <= 100:
            raise ValueError("Health score must be between 0 and 100")

        event = "NO_CHANGE"

        if not self.active:
            self.good_count = 0
            if score < self.unhealthy_threshold:
                self.bad_count += 1
                if self.bad_count >= self.trigger_samples:
                    self.active = True
                    self.bad_count = 0
                    event = "TRIGGER"
            else:
                self.bad_count = 0
        else:
            self.bad_count = 0
            if score >= self.recovery_threshold:
                self.good_count += 1
                if self.good_count >= self.recovery_samples:
                    self.active = False
                    self.good_count = 0
                    event = "RECOVER"
            else:
                self.good_count = 0

        return {
            "score": score,
            "active": self.active,
            "event": event,
            "bad_samples": self.bad_count,
            "good_samples": self.good_count,
        }
