"""Minimal Prometheus metrics (no extra deps): counters + latency histogram."""
import time
from collections import Counter, defaultdict

req_count = Counter()
req_errors = Counter()
lat_samples = defaultdict(list)


def observe(endpoint, status, latency_ms):
    req_count[endpoint] += 1
    if status >= 500:
        req_errors[endpoint] += 1
    ls = lat_samples[endpoint]
    ls.append(latency_ms)
    if len(ls) > 500:
        del ls[: len(ls) - 500]


def render_metrics():
    lines = ["# HELP cloudmart_http_requests_total Total HTTP requests by endpoint",
             "# TYPE cloudmart_http_requests_total counter"]
    for ep, c in sorted(req_count.items()):
        lines.append(f'cloudmart_http_requests_total{{endpoint="{ep}"}} {c}')
    lines += ["# HELP cloudmart_http_errors_total HTTP 5xx by endpoint",
              "# TYPE cloudmart_http_errors_total counter"]
    for ep, c in sorted(req_errors.items()):
        lines.append(f'cloudmart_http_errors_total{{endpoint="{ep}"}} {c}')
    lines += ["# HELP cloudmart_http_latency_ms_avg Average latency ms (last 500)",
              "# TYPE cloudmart_http_latency_ms_avg gauge"]
    for ep, ls in sorted(lat_samples.items()):
        avg = sum(ls) / len(ls) if ls else 0
        lines.append(f'cloudmart_http_latency_ms_avg{{endpoint="{ep}"}} {avg:.2f}')
    return "\n".join(lines) + "\n"
