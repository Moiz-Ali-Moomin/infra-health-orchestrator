# System Health Validator

[![Platform: Kubernetes](https://img.shields.io/badge/Platform-Kubernetes-blue.svg)](https://kubernetes.io)
[![Framework: FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)

**System Health Validator** is a production-grade, modular API service designed to provide deterministic health assertions for cloud-native environments. It acts as an aggregated validation gateway, orchestrating deep-dive health checks across HTTP dependencies, Kubernetes cluster states, database availability, and system resource utilization.

Built for Reliability Engineering teams, it sits in the critical path of post-deployment verification and continuous environment monitoring, bridging the gap between basic liveness probes and comprehensive synthetic monitoring.

---

## 🏗️ Architecture & Philosophy

The system is built on **FastAPI** to leverage asynchronous I/O capabilities for concurrent validation runs. It is designed around the principles of **Fail-Fast**, **Stateless Execution**, and **High Observability**.

### Core Capabilities
- **Deterministic Orchestration:** Runs a suite of independent validation modules synchronously or asynchronously, aggregating results into a unified payload.
- **Deep K8s Integration:** Natively interacts with the Kubernetes API to evaluate Pod lifecycles, detecting hidden anomalies like `CrashLoopBackOff`, and asserting that deployment target state matches actual state.
- **Dependency Validation:** Connects to PostgreSQL databases to verify query latency and authentication, rather than just port availability.
- **Proactive Alerting:** Automatically dispatches structured payload alerts via Slack and SMTP in the event of subset failures, eliminating the need for downstream alert processing.

---

## 📂 Project Anatomy

```text
system-health-validator/
├── app/
│   ├── main.py                     # ASGI application entrypoint & lifecycle hooks
│   ├── config.py                   # Pydantic BaseSettings for deterministic configurations
│   ├── api/
│   │   └── routes.py               # Gateway endpoints (Live, Ready, Run)
│   ├── checks/                     # Isolated validation domain boundaries
│   │   ├── http_check.py           # HTTP/HTTPS latency & status assertion
│   │   ├── kubernetes_check.py     # K8s target-state vs actual-state assertion
│   │   ├── database_check.py       # RDBMS connectivity & query latency assertion
│   │   └── resource_check.py       # Compute node saturation checks (CPU/MEM)
│   ├── services/
│   │   ├── health_orchestrator.py  # Aggregator for validation modules
│   │   └── notifier.py             # External communication adapters (Slack, SMTP)
│   └── utils/
│       └── logger.py               # Centralized, structured JSON-compatible logger
├── Dockerfile                      # Distroless-inspired multi-stage build manifest
└── requirements.txt                # Pinned dependencies
```

---

## 🚦 API Reference

The service exposes the following endpoints:

### `GET /health/live`
Assertion of the API server's ability to accept connections. Used primarily by K8s `livenessProbe`.
* **Response:** `200 OK`
* **Latency Expectation:** `<5ms`

### `GET /health/ready`
Assertion of the validation engine's readiness to execute checks. Used primarily by K8s `readinessProbe`.
* **Response:** `200 OK`
* **Latency Expectation:** `<5ms`

### `POST /health/run`
Executes the aggregated validation suite.
* **Responses:**
  * `200 OK`: All checks passed successfully.
  * `503 Service Unavailable`: One or more validation domain checks failed. Triggers alerts.
* **Payload Structure:**
  ```json
  {
    "status": "unhealthy",
    "details": {
      "http": {
        "status": "healthy",
        "details": { "https://api.internal.corp/status": "Passed" },
        "latency_sec": 0.042
      },
      "kubernetes": {
        "status": "unhealthy",
        "details": { "pods": ["payment-worker-8bfabc (CrashLoopBackOff)"] },
        "latency_sec": 0.150
      },
      ...
    },
    "latency_sec": 1.104,
    "timestamp": "2026-02-23T15:42:10.123456+00:00"
  }
  ```

---

## ⚙️ Configuration Reference

The application is completely environment-driven, utilizing Pydantic `BaseSettings` for strict type validation at boot time.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PORT` | Integer | `8000` | Port for ASGI server to bind. |
| `LOG_LEVEL` | String | `INFO` | Standard logging levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `HTTP_ENDPOINTS` | CSV String | - | Comma-separated list of downstream URLs to validate. |
| `HTTP_TIMEOUT_SEC` | Integer | `5` | Maximum allowed latency for HTTP dependencies. |
| `KUBERNETES_NAMESPACE` | String | `default` | Target namespace for K8s API validation sweeps. |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`| String | - | Database connection parameters. |
| `DB_PASSWORD` | String | - | Database authentication constraint. |
| `CPU_THRESHOLD_PERCENT` | Float | `85.0` | Alerting threshold for Host/Pod CPU Node saturation. |
| `MEM_THRESHOLD_PERCENT` | Float | `85.0` | Alerting threshold for Host/Pod Memory saturation. |
| `SLACK_WEBHOOK_URL` | String | - | Webhook URI for routing critical alerts to Slack. |
| `SMTP_HOST`, `ALERT_EMAIL_TO` | String | - | Email delivery configurations for failure notifications. |

---

## 🚀 Deployment & Operations

### Local Development / CI Environments

**Requirements:** Python 3.11+, virtualenv

```bash
# 1. Initialize environment
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Export strict permutations (modify as needed)
export HTTP_ENDPOINTS="https://google.com"
export LOG_LEVEL="DEBUG"

# 3. Boot ASGI Server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Kubernetes Native Deployment

This service is explicitly designed to run as a `Deployment` with a mapped `Service` inside a Kubernetes cluster to leverage In-Cluster RBAC for validation.

```bash
# Build & Push Immutable Artifact
docker build -t registry.internal/system-health-validator:$(git rev-parse --short HEAD) .
docker push registry.internal/system-health-validator:$(git rev-parse --short HEAD)
```

**RBAC Requirement:**
Ensure the `ServiceAccount` bound to this pod has `get` and `list` verbs enabled for `pods` and `deployments` in the targeted `KUBERNETES_NAMESPACE` (or cluster-wide via `ClusterRole`).

#### Example YAML integration
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: health-validator-role
rules:
- apiGroups: ["", "apps"]
  resources: ["pods", "deployments"]
  verbs: ["get", "list"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: system-health-validator
spec:
  replicas: 2
  template:
    spec:
      serviceAccountName: health-validator-sa
      containers:
      - name: validator
        image: registry.internal/system-health-validator:latest
        envFrom:
        - configMapRef:
            name: validator-config
```

---

## 🛠️ Extensibility & Contribution

To add new validation domains (e.g., Redis, Kafka, Custom Metrics):
1. Navigate to `app/checks/` and create `your_check.py`.
2. Encapsulate validation rules within a class that yields the deterministic dictionary shape: `{"status": "...", "details": ..., "latency_sec": ...}`.
3. Import and mount your check in `app/services/health_orchestrator.py` `__init__` payload. Validations are automatically picked up by the aggregator logic.

---
*Built with operational empathy by your friendly Platform Engineering Team.*
