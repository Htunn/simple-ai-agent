# Changelog

All notable changes to AIOps Orchestrator are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
This project uses [Semantic Versioning](https://semver.org/).

---

## [2.0.0] — 2026-07-26

### 🚀 Major Release: Multi-Agent Orchestration & API Backend Monitoring

This is a **major release** introducing Agent-to-Agent (A2A) integration and external API backend monitoring capabilities, transforming the AIOps Orchestrator into a complete multi-agent orchestration platform.

### Added

#### 🤖 Agent-to-Agent (A2A) Integration
- **Agent Registry** with PostgreSQL persistence and Redis caching (5min TTL)
  - Dynamic agent registration via REST API
  - Auto-registration from `config/agents.yml`
  - Agent health tracking and status monitoring
- **Capability Discovery & Matching**
  - Intelligent capability scoring (0.0-1.0 scale)
  - JSON Schema parameter validation
  - Tag-based fallback matching
- **Task Delegation Framework**
  - Synchronous mode: wait for task completion (default 60s timeout)
  - Asynchronous mode: webhook callbacks for long-running tasks
  - Automatic agent selection by capability score
- **Natural Language Delegation**
  - `@agent-name <task description>` syntax in chat
  - AI-powered capability and parameter extraction (Gemini 2.0 Flash)
  - Structured syntax: `@capability: param1=val1, param2=val2`
- **A2A Chat Commands**
  - `/a2a agents [capability]` - List registered agents
  - `/a2a agent <id>` - Show detailed agent info
  - `/a2a status` - System status and metrics
  - `/a2a help` - Command reference
- **JWT Authentication**
  - HS256 token signing with 1-hour expiry
  - API key generation (SHA-256 hashed storage)
  - Capability-based access control (CBAC)
- **A2A REST API** (7 endpoints)
  - `POST /api/a2a/register` - Agent registration (returns API key once)
  - `GET /api/a2a/agents` - List agents with filters
  - `GET /api/a2a/agents/{agent_id}` - Agent details
  - `DELETE /api/a2a/agents/{agent_id}` - Deregister (self-only)
  - `POST /api/a2a/delegate` - Receive task delegations
  - `GET /api/a2a/tasks/{task_id}` - Task status
  - `POST /api/a2a/webhook` - Async completion callbacks
- **Database Schema**
  - `agents` table with JSONB capabilities, indexed status
  - `agent_tasks` table for delegation audit trail
  - `agent_messages` table for message history
- **Prometheus Metrics** (9 A2A metrics)
  - `aiagent_a2a_agents_registered` (Gauge)
  - `aiagent_a2a_agents_online` (Gauge)
  - `aiagent_a2a_tasks_delegated_total` (Counter with labels)
  - `aiagent_a2a_tasks_received_total` (Counter)
  - `aiagent_a2a_task_duration_seconds` (Histogram)
  - `aiagent_a2a_webhooks_sent_total` (Counter)
  - `aiagent_a2a_webhooks_received_total` (Counter)
  - `aiagent_a2a_auth_failures_total` (Counter with reason)
  - `aiagent_a2a_capability_requests_total` (Counter)
- **Health Endpoint**: `GET /health/a2a` for system status

#### 🌐 API Backend Monitoring
- **API Backend Watch-Loop**
  - Background polling for external service health
  - Configurable check intervals (default: 60s)
  - Timeout and retry handling
- **Monitoring Capabilities**
  - Downtime detection (HTTP errors, timeouts, connection failures)
  - High latency alerts (P95 response time tracking)
  - Elevated error rate detection (4xx/5xx responses)
  - SSL certificate expiration warnings
- **Configuration** (`config/api_backends.yml`)
  - Per-endpoint thresholds (latency, error rate, SSL days)
  - Environment variable substitution: `${VAR:-default}`
  - Custom timeout and check intervals
- **Alert Rules** (4 new conditions)
  - `API_BACKEND_DOWN` - Service unavailable
  - `API_HIGH_LATENCY` - P95 latency exceeds threshold
  - `API_HIGH_ERROR_RATE` - Error percentage too high
  - `API_SSL_EXPIRING` - Certificate expiring soon
- **Remediation Playbooks** (3 new playbooks)
  - `api_backend_down_remediation` - Diagnostic playbook (DNS, curl, SSL, traceroute)
  - `api_latency_investigation` - Latency analysis with timing breakdown
  - `api_error_rate_analysis` - Error pattern investigation
- **MCP Diagnostic Tools** (4 tools)
  - `api_dns_lookup` - DNS resolution testing
  - `api_curl_test` - HTTP connectivity and timing
  - `api_ssl_check` - SSL certificate validation
  - `api_traceroute` - Network path analysis
- **Prometheus Metrics** (4 API metrics)
  - `aiagent_api_backend_up` (Gauge) - 1=up, 0=down
  - `aiagent_api_backend_latency_seconds` (Histogram)
  - `aiagent_api_backend_errors_total` (Counter with error_type)
  - `aiagent_api_backend_checks_total` (Counter with status)
- **Health Endpoints**
  - Extended `/health` with `api_backends` section
  - New `/health/api-backends` for detailed status

### Changed
- **Message Handler** - Extended with A2A delegation support
  - `@agent` syntax detection and routing
  - `/a2a` command handler (130+ lines)
  - Natural language extraction via AI
- **Main Application** - A2A initialization in lifespan
  - Agent registry setup
  - Task delegator exposure to message handler
  - Auto-registration from config
- **Development Status** - Upgraded from "Beta" to "Production/Stable"

### Documentation
- **New Documentation** (~52KB total)
  - `docs/a2a-integration.md` (20KB) - Complete A2A guide
  - `docs/a2a-sequence-diagrams.md` (19KB) - 8 Mermaid sequence diagrams
  - `docs/api-backend-monitoring.md` (13KB) - API monitoring guide
- **Updated Documentation**
  - `docs/architecture.md` - Added A2A architecture section
  - `README.md` - Added A2A features and updated doc index

### Dependencies
- Added `PyJWT==2.8.0` for JWT authentication

### Migration Notes

#### Database Migration Required
Run Alembic migration `003_a2a_tables` to create A2A schema:

```bash
docker exec -it aiops-orchestrator alembic upgrade head
```

This creates:
- `agents` table
- `agent_tasks` table  
- `agent_messages` table

#### Configuration

**Enable A2A** (optional, disabled by default):

```bash
export A2A_ENABLED=true
export A2A_AGENT_ID="aiops-orchestrator"
export A2A_AGENT_NAME="AIOps Orchestrator"
export A2A_JWT_SECRET="your-secret-key-here"  # CHANGE IN PRODUCTION
export A2A_WEBHOOK_URL="https://your-domain.com/api/a2a/webhook"
```

**Enable API Backend Monitoring**:

```bash
export API_BACKEND_MONITORING_ENABLED=true
# Edit config/api_backends.yml to add endpoints
```

### Security Considerations

⚠️ **IMPORTANT**: Change default JWT secret in production:

```bash
export A2A_JWT_SECRET="$(openssl rand -hex 32)"
```

### Breaking Changes

**None** - All new features are opt-in and backward compatible.

---

## [Unreleased]

### Added
- Future features will be listed here

---

## [0.4.0] — 2026-03-02

### Added
- **AIOps Engine** — full proactive monitoring subsystem
  - `K8sWatchLoop` background task polling cluster every 30s (configurable)
  - Detects: `CrashLoopBackOff`, `OOMKilled`, `NotReady` nodes, zero-replica deployments
  - `RuleEngine` for severity-mapped alert rule matching
  - `PlaybookExecutor` for ordered remediation step sequences
  - `RCAEngine` — LLM-powered root-cause analysis with structured JSON output (SRE prompt)
  - `LogAnalyzer` — pattern recognition on pod/container logs
- **Approval Manager** — human-in-the-loop gate for MEDIUM/HIGH risk playbook steps
  - Redis-backed pending approvals with configurable TTL (default 5 min)
  - Chat-native approval: `approve <id>` / `reject <id>`
  - Risk levels: `LOW` (auto), `MEDIUM` (approve), `HIGH` (warn + approve)
- **Alertmanager webhook receiver** — `POST /api/alert/webhook` ingests Prometheus alerts
- **Enhanced `/health` endpoint** — now reports K8s, Prometheus, watchloop status, pending approvals, active incidents
- Grafana monitoring integration helper (`src/monitoring/grafana.py`)
- Prometheus metrics integration (`src/monitoring/prometheus.py`)
- `config/` directory with Prometheus, Alertmanager, and Grafana provisioning configs

### Changed
- Application name: **AIOps Orchestrator**
- Database defaults updated to use `aiagent` database name
- `lifespan()` now initialises ApprovalManager and PlaybookExecutor at startup

---

## [0.3.0] — 2026-02-28

### Added
- **Multi-transport MCP (Model Context Protocol)** architecture
  - `MCPManager` with lifecycle management for multiple servers
  - `StdioTransport` — subprocess-based local servers (Kubernetes)
  - `SSETransport` — HTTP/SSE for cloud services (SimplePortChecker)
  - `.mcp-config.json` for declarative server configuration
- **Security scanning** via SimplePortChecker MCP SSE server (8 tools)
  - `scan_ports`, `analyze_certificate`, `detect_l7_protection`
  - `check_mtls`, `check_security_headers`, `scan_owasp_vulnerabilities`
  - `full_security_scan`, `check_hybrid_identity`
- **Slack bot** adapter (`slack_bolt`) with Events API, app-mention, IM history
- `MCP_CONFIG_PATH` environment variable support
- Kubernetes kubectl bundled in Docker image (v1.28)
- Multi-stage Docker build with OCI labels and non-root user

### Changed
- MCP server initialisation migrated from single server to `MCPManager` pattern
- Docker Compose: kubeconfig now mounted from `./data/kube/config`

---

## [0.2.0] — 2026-02-20

### Added
- **Kubernetes integration** with 13 MCP tools
  - `k8s_get_pods`, `k8s_get_nodes`, `k8s_get_deployments`, `k8s_get_services`
  - `k8s_scale_deployment`, `k8s_describe_resource`, `k8s_get_logs`
  - `k8s_get_events`, `k8s_top_pods`, `k8s_top_nodes`
  - `k8s_get_namespaces`, `k8s_get_contexts`, `k8s_current_context`
- **Natural language Kubernetes queries** — intent detection with status filters
  - Filters: `error/failed/crash`, `unhealthy/not ready`, `pending`, `running`
- `KubernetesHandler` service for NL-to-kubectl translation
- `/k8s` command routing in `MessageHandler`
- Redis-backed session manager with TTL expiry
- Alembic migration support

### Changed
- `MessageHandler` refactored to support K8s intent routing alongside AI responses

---

## [0.1.0] — 2026-02-10

### Added
- Initial release
- **FastAPI** application with async lifespan management
- **Telegram** adapter (python-telegram-bot, webhook + long-poll)
- Channel router for fan-out/fan-in message routing
- **GitHub Models API** client (openai-compatible SDK)
  - Models: GPT-4o, Claude-3 Opus, Llama-3-70B
- Per-user and per-channel model selection (`/model` command)
- Conversation history stored in **PostgreSQL 16**
- **Redis 7** session caching with TTL
- SQLAlchemy async models: `User`, `Conversation`, `Message`, `ChannelConfig`
- Docker Compose stack: app + PostgreSQL + Redis
- Rate limiting via `slowapi`
- Structured JSON logging via `structlog`
- `/health`, `/ready` endpoints
- Pydantic Settings for all configuration
- `.env.example` template

---

[Unreleased]: https://github.com/YOUR_USERNAME/aiops-orchestrator/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/YOUR_USERNAME/aiops-orchestrator/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/YOUR_USERNAME/aiops-orchestrator/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/YOUR_USERNAME/aiops-orchestrator/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/YOUR_USERNAME/aiops-orchestrator/releases/tag/v0.1.0
