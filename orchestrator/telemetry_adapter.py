import json
import subprocess
import urllib.request
from datetime import datetime, timezone


NAMESPACE = "cloudmart"


def run_command(*args):
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    return result.stdout


def collect_telemetry():
    raw = run_command(
        "kubectl", "get", "pods",
        "-n", NAMESPACE,
        "-o", "json",
    )
    data = json.loads(raw)

    pods = []
    for item in data.get("items", []):
        statuses = item.get("status", {}).get(
            "containerStatuses", []
        )
        pods.append({
            "name": item["metadata"]["name"],
            "phase": item.get("status", {}).get("phase", "Unknown"),
            "ready": bool(statuses) and all(
                c.get("ready", False) for c in statuses
            ),
            "restart_count": sum(
                c.get("restartCount", 0) for c in statuses
            ),
        })

    backend_health = "UNKNOWN"
    try:
        response = run_command(
            "kubectl", "exec",
            "-n", NAMESPACE,
            "deployment/backend", "--",
            "python", "-c",
            "import urllib.request; "
            "print(urllib.request.urlopen("
            "'http://127.0.0.1:5000/api/health', "
            "timeout=5).read().decode())",
        )
        parsed = json.loads(response.strip())
        backend_health = parsed.get("status", "UNKNOWN")
    except Exception as exc:
        backend_health = f"UNAVAILABLE: {type(exc).__name__}"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "namespace": NAMESPACE,
        "pods": pods,
        "backend_health": backend_health,
        "database_health": "UNKNOWN_NOT_INDEPENDENTLY_CHECKED",
        "runtime_security": "UNKNOWN_NO_ADAPTER_CONFIGURED",
    }


if __name__ == "__main__":
    print(json.dumps(collect_telemetry(), indent=2))
