from prometheus_client import Counter, Histogram, Gauge

VALIDATOR_RUNS_TOTAL = Counter(
    "validator_runs_total",
    "Total orchestrated validation runs handled by the engine",
    ["environment", "trigger", "decision"]
)

CHECK_STATUS_TOTAL = Counter(
    "check_status_total",
    "Status outcomes for dynamically loaded check plugins",
    ["environment", "check_type", "cluster", "status"]
)

CHECK_LATENCY_SECONDS = Histogram(
    "check_latency_seconds",
    "Latency of validated domains",
    ["check_type", "cluster"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

SLO_BURN_RATE = Gauge(
    "slo_burn_rate",
    "Current rolling SLO burn rate calculated by SLOEngine",
    ["service_id", "window"]
)
