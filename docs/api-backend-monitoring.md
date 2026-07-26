# API Backend Monitoring

The AIOps Orchestrator includes comprehensive external API backend health monitoring capabilities. This allows you to monitor third-party services, internal microservices, and any HTTP/HTTPS endpoints your application depends on.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Configuration](#configuration)
- [Alert Rules](#alert-rules)
- [Playbooks](#playbooks)
- [MCP Diagnostic Tools](#mcp-diagnostic-tools)
- [Metrics](#metrics)
- [Health Endpoints](#health-endpoints)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)

---

## Overview

The API Backend Watch-Loop runs continuously in the background, polling configured external services to detect:

- **Downtime** — Service unavailable or returning errors
- **High Latency** — P95 response time exceeds threshold
- **Elevated Error Rates** — HTTP 4xx/5xx responses above threshold
- **SSL Certificate Expiration** — Certificates expiring within warning window

When issues are detected, the system:
1. Emits events to the Rule Engine
2. Triggers configured alert rules
3. Executes remediation playbooks (if defined)
4. Exposes metrics to Prometheus
5. Updates health endpoints

---

## Features

### ✅ Implemented

- **Background Polling**: Configurable check intervals (default: 60s)
- **Health Checks**: HTTP GET/HEAD requests with timeout
- **Latency Tracking**: Records response times, calculates P95
- **Error Rate Monitoring**: Tracks HTTP 4xx/5xx responses
- **SSL Certificate Validation**: Checks expiration dates
- **Environment Variable Substitution**: Use `${VAR:-default}` in config
- **Rule Engine Integration**: 4 condition types for API backends
- **Prometheus Metrics**: 4 metrics for API backend monitoring
- **Health Endpoints**: `/health` includes API status, `/health/api-backends` for details
- **MCP Diagnostic Tools**: DNS lookup, curl test, SSL check, traceroute
- **Remediation Playbooks**: 3 built-in playbooks for common scenarios

### 🔜 Future Enhancements

- **Advanced Assertions**: Response body validation (JSON schema, regex)
- **Custom Headers**: Authentication headers for private APIs
- **Webhook Notifications**: Direct notifications on status change
- **Rate Limiting**: Respect API rate limits
- **Circuit Breaker**: Automatic backoff on repeated failures

---

## Configuration

API backends are defined in `config/api_backends.yml`:

```yaml
api_backends:
  - name: "payment-gateway"
    url: "${PAYMENT_GATEWAY_URL:-https://api.stripe.com/v1/health}"
    check_interval_seconds: 60
    timeout_seconds: 10
    thresholds:
      latency_p95_ms: 500        # Alert if P95 latency > 500ms
      error_rate_percent: 5.0    # Alert if error rate > 5%
      ssl_expiry_days: 14        # Alert if cert expires within 14 days

  - name: "auth-service"
    url: "https://auth.example.com/health"
    check_interval_seconds: 30
    timeout_seconds: 5
    thresholds:
      latency_p95_ms: 200
      error_rate_percent: 1.0
      ssl_expiry_days: 7

  - name: "database-api"
    url: "${DATABASE_API_URL:-http://localhost:5432/health}"
    check_interval_seconds: 120
    timeout_seconds: 15
    thresholds:
      latency_p95_ms: 1000
      error_rate_percent: 10.0
      ssl_expiry_days: 30
```

### Configuration Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✅ | Unique identifier for the backend |
| `url` | string | ✅ | HTTP/HTTPS endpoint to check (supports env vars) |
| `check_interval_seconds` | int | ❌ | Polling interval (default: 60) |
| `timeout_seconds` | int | ❌ | Request timeout (default: 10) |
| `thresholds.latency_p95_ms` | int | ❌ | P95 latency alert threshold in milliseconds |
| `thresholds.error_rate_percent` | float | ❌ | Error rate alert threshold (0-100) |
| `thresholds.ssl_expiry_days` | int | ❌ | SSL cert expiry warning window in days |

### Environment Variable Substitution

Use `${VAR_NAME:-default_value}` syntax:

```yaml
api_backends:
  - name: "production-api"
    url: "${API_URL:-https://api.production.com/health}"
    timeout_seconds: ${API_TIMEOUT:-10}
```

**At runtime:**
```bash
export API_URL="https://api.staging.com/health"
export API_TIMEOUT=15
```

---

## Alert Rules

The Rule Engine includes 4 API backend conditions defined in `config/alert_rules.yml`:

```yaml
groups:
  - name: api_backend_monitoring
    rules:
      - name: api_backend_down
        condition: API_BACKEND_DOWN
        severity: critical
        message: "API backend {backend} is DOWN! Last error: {error}"
        playbook: api_backend_down_remediation

      - name: api_high_latency
        condition: API_HIGH_LATENCY
        severity: warning
        message: "API backend {backend} has high latency: {latency_ms}ms (threshold: {threshold_ms}ms)"
        playbook: api_latency_investigation

      - name: api_high_error_rate
        condition: API_HIGH_ERROR_RATE
        severity: warning
        message: "API backend {backend} has elevated error rate: {error_rate}% (threshold: {threshold}%)"
        playbook: api_error_rate_analysis

      - name: api_ssl_expiring
        condition: API_SSL_EXPIRING
        severity: warning
        message: "API backend {backend} SSL certificate expires in {days_until_expiry} days (threshold: {threshold_days} days)"
```

### Condition Details

| Condition | Trigger | Event Data |
|---|---|---|
| `API_BACKEND_DOWN` | HTTP errors, timeouts, connection failures | `backend`, `error` |
| `API_HIGH_LATENCY` | P95 latency > threshold | `backend`, `latency_ms`, `threshold_ms` |
| `API_HIGH_ERROR_RATE` | Error rate % > threshold | `backend`, `error_rate`, `threshold` |
| `API_SSL_EXPIRING` | Cert expires within threshold days | `backend`, `days_until_expiry`, `threshold_days` |

---

## Playbooks

Three built-in playbooks handle common API backend scenarios.

### 1. API Backend Down Remediation

**Playbook**: `api_backend_down_remediation`  
**Risk Level**: LOW (diagnostic only)

```yaml
steps:
  - name: "Check DNS resolution"
    tool: "api_dns_lookup"
    params:
      backend: "{backend}"
    
  - name: "Test connectivity with curl"
    tool: "api_curl_test"
    params:
      backend: "{backend}"
    
  - name: "Verify SSL certificate"
    tool: "api_ssl_check"
    params:
      backend: "{backend}"
    
  - name: "Run traceroute"
    tool: "api_traceroute"
    params:
      backend: "{backend}"
```

**When Triggered**: Immediate execution (LOW risk = auto-execute)

**Example Output**:
```
🔧 Executing Playbook: api_backend_down_remediation

Step 1/4: Check DNS resolution
✅ DNS lookup successful: api.stripe.com → 54.187.205.235

Step 2/4: Test connectivity with curl
❌ Curl test failed: Connection timeout after 10s

Step 3/4: Verify SSL certificate
⚠️ Skipped (no connection)

Step 4/4: Run traceroute
📍 Traceroute shows packet loss at hop 5 (ISP router)

🎯 Diagnosis: Network connectivity issue at ISP level
```

### 2. API Latency Investigation

**Playbook**: `api_latency_investigation`  
**Risk Level**: LOW (diagnostic only)

```yaml
steps:
  - name: "Measure current latency"
    tool: "api_curl_test"
    params:
      backend: "{backend}"
      verbose: true
    
  - name: "Check SSL handshake time"
    tool: "api_ssl_check"
    params:
      backend: "{backend}"
      timing: true
```

### 3. API Error Rate Analysis

**Playbook**: `api_error_rate_analysis`  
**Risk Level**: MEDIUM (requires approval for RCA)

```yaml
steps:
  - name: "Run diagnostic curl test"
    tool: "api_curl_test"
    params:
      backend: "{backend}"
      show_headers: true
    risk: LOW
    
  - name: "Run RCA on error patterns"
    tool: "rca_engine"
    params:
      incident_type: "api_errors"
      backend: "{backend}"
    risk: MEDIUM
```

---

## MCP Diagnostic Tools

Four MCP tools are available for API backend diagnostics. These can be called by playbooks or invoked directly via natural language.

### 1. `api_dns_lookup`

**Purpose**: Resolve DNS for an API backend

**Parameters**:
- `backend` (string, required): Backend name from config

**Example**:
```
User: Check DNS for payment-gateway
Bot: 🔍 DNS Lookup: payment-gateway
     api.stripe.com → 54.187.205.235, 54.187.144.72
```

### 2. `api_curl_test`

**Purpose**: Test HTTP connectivity and timing

**Parameters**:
- `backend` (string, required): Backend name
- `verbose` (bool, optional): Show detailed timing
- `show_headers` (bool, optional): Include response headers

**Example**:
```
User: Test API connectivity for auth-service
Bot: 🔍 Curl Test: auth-service

     GET https://auth.example.com/health
     Status: 200 OK
     Time: 145ms (DNS: 12ms, Connect: 34ms, TLS: 67ms, Transfer: 32ms)
```

### 3. `api_ssl_check`

**Purpose**: Validate SSL certificate

**Parameters**:
- `backend` (string, required): Backend name
- `timing` (bool, optional): Include handshake timing

**Example**:
```
User: Check SSL certificate for payment-gateway
Bot: 🔒 SSL Check: payment-gateway

     Subject: CN=*.stripe.com
     Issuer: DigiCert TLS RSA SHA256 2020 CA1
     Valid: 2025-01-15 to 2026-01-14
     Days until expiry: 201
     ✅ Certificate is valid
```

### 4. `api_traceroute`

**Purpose**: Trace network path to backend

**Parameters**:
- `backend` (string, required): Backend name

**Example**:
```
User: Run traceroute to database-api
Bot: 📍 Traceroute: database-api

     1.  192.168.1.1     1ms
     2.  10.0.0.1        5ms
     3.  172.16.0.5      12ms
     4.  * * *           (timeout)
     5.  52.46.128.1     45ms
     6.  54.187.205.235  48ms (destination)
```

---

## Metrics

API backend monitoring exposes 4 Prometheus metrics:

### 1. `aiagent_api_backend_up`

**Type**: Gauge  
**Labels**: `backend`  
**Description**: 1 if backend is up, 0 if down

```prometheus
aiagent_api_backend_up{backend="payment-gateway"} 1
aiagent_api_backend_up{backend="auth-service"} 0
```

### 2. `aiagent_api_backend_latency_seconds`

**Type**: Histogram  
**Labels**: `backend`  
**Buckets**: 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0  
**Description**: Response time distribution

```prometheus
aiagent_api_backend_latency_seconds_bucket{backend="payment-gateway",le="0.5"} 127
aiagent_api_backend_latency_seconds_sum{backend="payment-gateway"} 45.2
aiagent_api_backend_latency_seconds_count{backend="payment-gateway"} 150
```

**Calculate P95**:
```promql
histogram_quantile(0.95, 
  rate(aiagent_api_backend_latency_seconds_bucket[5m])
)
```

### 3. `aiagent_api_backend_errors_total`

**Type**: Counter  
**Labels**: `backend`, `error_type`  
**Description**: Total errors by type

```prometheus
aiagent_api_backend_errors_total{backend="auth-service",error_type="timeout"} 3
aiagent_api_backend_errors_total{backend="auth-service",error_type="http_500"} 7
```

### 4. `aiagent_api_backend_checks_total`

**Type**: Counter  
**Labels**: `backend`, `status`  
**Description**: Total health checks by status

```prometheus
aiagent_api_backend_checks_total{backend="payment-gateway",status="success"} 1450
aiagent_api_backend_checks_total{backend="payment-gateway",status="failure"} 5
```

---

## Health Endpoints

### GET `/health`

Main health check includes `api_backends` section:

```json
{
  "status": "healthy",
  "database": "ok",
  "redis": "ok",
  "kubernetes": "ok",
  "prometheus": "ok",
  "watchloop": "running",
  "api_backends": {
    "total": 3,
    "healthy": 2,
    "unhealthy": 1,
    "backends": [
      {"name": "payment-gateway", "status": "healthy"},
      {"name": "auth-service", "status": "unhealthy"},
      {"name": "database-api", "status": "healthy"}
    ]
  }
}
```

### GET `/health/api-backends`

Detailed API backend status:

```json
{
  "total_backends": 3,
  "healthy": 2,
  "unhealthy": 1,
  "backends": [
    {
      "name": "payment-gateway",
      "url": "https://api.stripe.com/v1/health",
      "status": "healthy",
      "last_check": "2026-01-25T10:30:45Z",
      "latency_ms": 145,
      "error_rate_percent": 0.0,
      "ssl_days_remaining": 365,
      "uptime_percent": 99.98
    },
    {
      "name": "auth-service",
      "url": "https://auth.example.com/health",
      "status": "unhealthy",
      "last_check": "2026-01-25T10:30:50Z",
      "latency_ms": null,
      "error_rate_percent": 100.0,
      "last_error": "Connection timeout after 5s",
      "consecutive_failures": 3
    }
  ]
}
```

---

## Usage Examples

### Example 1: Chat Interaction

```
User: Why is the payment gateway slow?

Bot: 🔍 Checking payment-gateway status...

API Backend: payment-gateway
Status: healthy ✅
Current Latency: 487ms (P95)
Error Rate: 0.2%
Uptime: 99.95%

⚠️ Latency is approaching threshold (500ms)
```

### Example 2: Alert Notification

```
Bot: 🚨 CRITICAL ALERT: api_backend_down

Backend: auth-service
Status: DOWN ❌
Error: Connection timeout after 5s
Consecutive Failures: 3

🔧 Auto-executing playbook: api_backend_down_remediation
```

---

## Troubleshooting

### Backend Always Shows "DOWN"

**Possible Causes**:
1. **URL unreachable** — Check network connectivity
2. **Timeout too short** — Increase `timeout_seconds`
3. **SSL verification fails** — Check certificate validity

**Debug**:
```bash
docker exec -it aiops-orchestrator curl -v https://api.example.com/health
docker logs aiops-orchestrator | grep api_watchloop
```

---

## Related Documentation

- [AIOps Engine Overview](aiops.md) - Rule engine, playbooks, RCA
- [Architecture](architecture.md) - System design and components
- [Monitoring & Observability](../README.md#observability) - Prometheus + Grafana setup

---

**Last Updated**: 2026-07-26  
**Version**: 1.0.0
