# Changelog

All notable changes to Simple AI Agent are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
This project uses [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- Initial public release preparation

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
- Application name: **Simple AI Agent**
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
- **Discord** adapter (discord.py, gateway WebSocket)
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

[Unreleased]: https://github.com/YOUR_USERNAME/simple-ai-agent/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/YOUR_USERNAME/simple-ai-agent/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/YOUR_USERNAME/simple-ai-agent/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/YOUR_USERNAME/simple-ai-agent/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/YOUR_USERNAME/simple-ai-agent/releases/tag/v0.1.0
