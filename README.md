# Simple AI Agent

> A production-ready, multi-channel AI agent with AIOps, Kubernetes management, security scanning, and human-in-the-loop remediation — built on FastAPI, GitHub Models, and the Model Context Protocol (MCP).

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](Dockerfile)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psycopg/black)

---

## Table of Contents

- [Overview](#overview)
- [Feature Matrix](#feature-matrix)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Channel Setup](#channel-setup)
- [AIOps Engine](#aiops-engine)
- [MCP Integration](#mcp-integration)
- [Kubernetes Integration](#kubernetes-integration)
- [Security Scanning](#security-scanning)
- [Monitoring & Observability](#monitoring--observability)
- [Configuration Reference](#configuration-reference)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Development](#development)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## Overview

Simple AI Agent is a conversational AI agent that connects **Discord, Telegram, and Slack** to powerful backend capabilities:

| Capability | Technology |
|---|---|
| LLM inference | GitHub Models API (GPT-4o, Claude-3 Opus, Llama-3-70B) |
| Chat persistence | PostgreSQL 16 (ACID, JSONB, Alembic migrations) |
| Session caching | Redis 7 (sub-ms access, TTL expiry) |
| Tool execution | MCP — stdio (Kubernetes) + SSE (cloud services) |
| Cluster ops | kubectl — 13 natural-language Kubernetes tools |
| Security scans | SimplePortChecker MCP — 8 security tools |
| AIOps | Watch-loop → Rule engine → Playbooks → RCA |
| Approvals | Human-in-the-loop via chat message |
| Alerting | Prometheus + Alertmanager webhook receiver |
| Observability | Grafana dashboards, structlog JSON, /metrics |

---

## Feature Matrix

### Messaging Channels
- **Discord** — Gateway WebSocket, slash commands, message-intent detection
- **Telegram** — Webhook mode, privacy-mode support, group and private chat
- **Slack** — Events API, app-mention, IM history, signing-secret verification

### AI / LLM
- **Multiple models** — GPT-4o, Claude-3 Opus, Llama-3-70B via GitHub Models
- **Model selection priority** — conversation override → user pref → channel default → system default
- **Conversation history** — stored in PostgreSQL, windowed into context
- **Streaming-compatible** — openai-compatible SDK with GitHub Models endpoint

### Kubernetes Management (13 tools)
- **Full CRUD** — pods, deployments, services, namespaces, nodes, events
- **Natural language** — "show me error pods in production"
- **Status filters** — error/failed/crash, unhealthy/not-ready, pending, running
- **Scaling** — `/k8s scale <deployment> <replicas> [ns]`
- **Logs** — streaming and snapshot log retrieval
- **Resource usage** — `top pods`, `top nodes`
- **Multi-context** — switch between clusters

### Security Scanning (8 tools via MCP SSE)
- **Port scanning** — TCP/UDP port enumeration
- **Certificate analysis** — TLS issuer, expiry, SANs, protocol
- **WAF/CDN detection** — Cloudflare, AWS WAF, Azure Front Door, Akamai
- **mTLS verification** — mutual TLS support check
- **Security headers** — HSTS, CSP, X-Frame-Options
- **OWASP scan** — common vulnerability detection
- **Full security scan** — combined assessment report
- **Hybrid identity** — identity provider detection

### AIOps Engine
- **K8s Watch-Loop** — background polling every 30 s (configurable)
  - Detects: `CrashLoopBackOff`, `OOMKilled`, `NotReady` nodes, zero-replica deployments
- **Rule Engine** — YAML-defined alert rules with severity mapping
- **Playbook Executor** — ordered step sequences with risk-gated execution
  - `LOW risk` — auto-execute, notify after
  - `MEDIUM risk` — post approval request, await chat response
  - `HIGH risk` — warn + require explicit confirmation
- **RCA Engine** — LLM-powered root-cause analysis (SRE prompt → JSON report)
- **Log Analyzer** — structured log pattern matching
- **Approval Manager** — Redis-backed TTL approvals; chat-native `approve/reject`
- **Alertmanager receiver** — `POST /api/alert/webhook` ingests Prometheus alerts

### Data & Performance
- **PostgreSQL 16** — users, conversations, messages, channel configs, JSONB metadata
- **Redis 7** — session cache (sub-ms), pending approvals (TTL 5 min), AOF persistence
- **Alembic migrations** — versioned schema management
- **Connection pooling** — async SQLAlchemy + asyncpg

### Production Hardening
- **Multi-stage Docker build** — kubectl bundled, OCI labels, non-root UID 1000
- **Security options** — `no-new-privileges`, isolated network, non-root container
- **Resource limits** — CPU and memory limits/reservations in Compose
- **Rich health endpoint** — DB, Redis, K8s, Prometheus, watchloop, pending approvals
- **Rate limiting** — `slowapi` per-IP rate limiter on all endpoints
- **Structured logging** — JSON via `structlog`, Docker log rotation

---

## Architecture

### High-Level Design

The full traffic-flow diagram is maintained as a D2 source file at [`docs/hld.d2`](docs/hld.d2).

**Render to PNG/SVG (requires [D2](https://d2lang.com)):**
```bash
# Install D2: https://d2lang.com/tour/install
d2 docs/hld.d2 docs/hld.svg
# or PNG
d2 docs/hld.d2 docs/hld.png --theme=0
```
The rendered diagram is committed at [`docs/hld.svg`](docs/hld.svg):

![Simple AI Agent — High-Level Design](docs/hld.svg)

> To regenerate after edits: `d2 docs/hld.d2 docs/hld.svg --theme=0`
#### Traffic Flow Summary

```
Users
  |
  +-- Discord WebSocket --> Discord Adapter  -+
  +-- Telegram Webhook  --> /api/webhook     -+
  +-- Slack Events API  --> /api/webhook     -+
                                              |
                                      Channel Router
                                              |
                                     Message Handler
                                  +----------+-----------+
                                  |          |           |
                           Session Mgr   AI Layer   K8s Handler
                             (Redis)   (GitHub      (NL parser)
                                        Models)          |
                                  |          |      MCP Manager
                                  |          |     +-----+------+
                             PostgreSQL    LLM   stdio(K8s)  SSE(Security)
                             (history)   tokens      |             |
                                                  kubectl   SimplePortChecker
                                                (subprocess)    (HTTPS)

AIOps (async background):
  Watch-Loop --> Rule Engine --> Playbook Executor --> Approval Manager
       |                                  |                    |
  K8s Cluster                       MCP tools             Redis TTL
                                          |
                                    RCA Engine --> GitHub Models (SRE prompt)

Observability:
  App /metrics --> Prometheus --> Grafana dashboards
                        |
                   Alertmanager --> POST /api/alert/webhook --> Rule Engine
```

### Layered Component Model

```
+-----------------------------------------------------+
|                   Channel Layer                      |  Discord / Telegram / Slack adapters
+-----------------------------------------------------+
|                     API Layer                        |  FastAPI, rate-limiter, webhooks
+-----------------------------------------------------+
|                 Business Logic Layer                 |  Message handler, session, K8s, approvals
+------------------------+----------------------------+
|        AI Layer        |       AIOps Layer          |  LLM client | watch-loop, rules, playbooks, RCA
+------------------------+----------------------------+
|                    MCP Layer                         |  MCP Manager -> stdio + SSE transports
+-----------------------------------------------------+
|                    Data Layer                        |  PostgreSQL + Redis
+-----------------------------------------------------+
|               Observability Layer                    |  Prometheus metrics, structlog JSON, Grafana
+-----------------------------------------------------+
```

### Documentation Index

| Document | Description |
|---|---|
| [`docs/hld.d2`](docs/hld.d2) | Full HLD traffic-flow diagram (D2 source) |
| [`docs/architecture.md`](docs/architecture.md) | Layered architecture, design decisions |
| [`docs/component-diagram.md`](docs/component-diagram.md) | Mermaid component interactions |
| [`docs/sequence-diagrams.md`](docs/sequence-diagrams.md) | Message flows, startup, MCP flows |
| [`docs/database-architecture.md`](docs/database-architecture.md) | PostgreSQL & Redis schema + performance |
| [`docs/kubernetes-integration.md`](docs/kubernetes-integration.md) | K8s guide — NL queries, status filters |
| [`docs/mcp-integration.md`](docs/mcp-integration.md) | MCP multi-transport architecture |
| [`docs/mcp-registry.md`](docs/mcp-registry.md) | Tool registry and routing |
| [`docs/aiops.md`](docs/aiops.md) | AIOps engine — watch-loop, rules, playbooks, RCA |
| [`docs/slack-setup.md`](docs/slack-setup.md) | Slack bot setup guide |

---

## Quick Start

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.12+ |
| Docker + Compose | v24+ |
| kubectl | 1.28+ (K8s features) |
| GitHub Account | Models API access |

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/simple-ai-agent.git
cd simple-ai-agent

python3.12 -m venv .venv
source .venv/bin/activate       # macOS / Linux
# .venv\Scripts\activate        # Windows

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env -- minimum required: GITHUB_TOKEN + at least one bot token
```

### 3. Start Infrastructure

```bash
# PostgreSQL and Redis -- schema auto-created on first boot
docker compose up -d postgres redis
```

### 4. Run the Agent

```bash
./scripts/start_server.sh
# Or manually:
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Verify

```bash
curl http://localhost:8000/health
# {"status":"healthy","database":"healthy","redis":"healthy",...}
```

---

## Channel Setup

### GitHub Token (Required)

1. Visit <https://github.com/settings/tokens> -> **Fine-grained personal access token**
2. Enable **Models API** permission
3. Set `GITHUB_TOKEN` in `.env`

### Discord

1. <https://discord.com/developers/applications> -> New Application -> Bot
2. Enable **Message Content Intent** under Privileged Gateway Intents
3. Copy token -> `DISCORD_TOKEN`
4. Invite URL: `https://discord.com/oauth2/authorize?client_id=CLIENT_ID&permissions=2048&scope=bot`

### Telegram

1. Message **@BotFather** -> `/newbot`
2. Copy token -> `TELEGRAM_TOKEN`
3. **Groups (recommended):** Disable privacy mode via @BotFather -> Bot Settings -> Group Privacy -> OFF

### Slack

1. <https://api.slack.com/apps> -> New App -> From scratch
2. OAuth scopes: `app_mentions:read`, `chat:write`, `im:history`, `users:read`
3. Install to workspace -> copy Bot User OAuth Token -> `SLACK_BOT_TOKEN`
4. Event Subscriptions webhook: `https://your-domain.com/api/webhook/slack`
5. Subscribe to: `app_mention`, `message.im`

See [`docs/slack-setup.md`](docs/slack-setup.md) for the full walkthrough.

---

## AIOps Engine

The AIOps engine provides **proactive cluster health monitoring** and **automated remediation** with a human-in-the-loop approval gate.

### Components

| Component | Purpose |
|---|---|
| **K8s Watch-Loop** | Polls cluster every `K8S_WATCHLOOP_INTERVAL` seconds |
| **Rule Engine** | Matches `ClusterEvent` objects against configured rules |
| **Playbook Executor** | Runs ordered remediation steps |
| **Approval Manager** | Gates `MEDIUM`/`HIGH` risk steps via chat |
| **RCA Engine** | LLM-powered root-cause analysis with structured JSON output |
| **Log Analyzer** | Pattern recognition on pod/container logs |

### Event Types Detected

| Event | Severity |
|---|---|
| `crash_loop` | critical |
| `oom_killed` | critical |
| `not_ready_node` | critical |
| `replication_failure` | high |
| External Alertmanager alert | varies |

### Risk-Gated Approval Flow

```
Playbook step (MEDIUM / HIGH risk)
        |
        v
Approval Manager --> Redis HSET  (TTL: 5 min)
        |
        v
Chat: "Approval required [ID: abc123]
       Action: restart pod nginx-abc in production
       Risk: MEDIUM -- type 'approve abc123' or 'reject abc123'"
        |
   +----+----+
approve    reject
   |           |
Execute     Cancel
step        playbook
```

### RCA Report Example

```
Root Cause Analysis

Pattern: OOMKill
Root Cause: Container exceeded memory limit due to unbounded in-memory cache growth
Confidence: 87%

Supporting Evidence:
  - OOMKilled event at 2026-03-02T14:23:11Z
  - Memory usage reached 512Mi (limit: 512Mi)
  - 3 restarts in last 4 hours

Recommended Actions:
  1. Set JVM/app heap limit to 60% of container memory limit
  2. Increase memory limit to 768Mi and monitor
  3. Add memory usage alert at 80% threshold
```

### AIOps Configuration

```env
K8S_WATCHLOOP_ENABLED=true
K8S_WATCHLOOP_INTERVAL=30
AUTO_REMEDIATION_ENABLED=false      # true = skip approvals for LOW-risk only
AIOPS_NOTIFICATION_CHANNEL=telegram:YOUR_CHAT_ID
APPROVAL_TIMEOUT_SECONDS=300
ALERTMANAGER_WEBHOOK_SECRET=your-secret
```

---

## MCP Integration

Simple AI Agent uses **MCP (Model Context Protocol)** with two transport types:

| Transport | Server | Use Case |
|---|---|---|
| `stdio` | `scripts/mcp_server.py` | Kubernetes (local subprocess, 13 tools) |
| `SSE` | `https://mcp.simpleportchecker.com/mcp` | Security scanning (cloud, 8 tools) |

### Configuration (`.mcp-config.json`)

```json
{
  "mcpServers": {
    "kubernetes": {
      "type": "stdio",
      "command": "python3",
      "args": ["scripts/mcp_server.py"],
      "description": "Kubernetes management tools via kubectl"
    },
    "simplePortChecker": {
      "type": "sse",
      "url": "https://mcp.simpleportchecker.com/mcp",
      "description": "Security scanning and port checking tools"
    }
  }
}
```

All tools are registered in `MCPManager.tool_registry` (`tool_name -> server_name`).
The `MessageHandler` calls `MCPManager.call_tool(name, params)` which dispatches to the correct transport automatically.

See [`docs/mcp-integration.md`](docs/mcp-integration.md) for protocol details.

---

## Kubernetes Integration

### Commands

| Command | Description |
|---|---|
| `/k8s pods [ns]` | List pods |
| `/k8s logs <pod> [ns]` | Get logs |
| `/k8s scale <deploy> <n> [ns]` | Scale deployment |
| `/k8s deployments [ns]` | List deployments |
| `/k8s nodes` | List nodes |
| `/k8s services [ns]` | List services |
| `/k8s namespaces` | List namespaces |
| `/k8s events [ns]` | Recent events |
| `/k8s describe <type> <name> [ns]` | Describe resource |
| `/k8s top pods\|nodes` | Resource usage |
| `/k8s contexts` | Available contexts |

### Natural Language Examples

```
show me error pods in production
list failed pods
scale api-server to 3 replicas in staging
get logs from nginx-abc123
what are my nodes
show pending pods in development
```

### Status Filters

| Keywords | Shows |
|---|---|
| `error`, `failed`, `crash` | CrashLoopBackOff, Error, ImagePullBackOff |
| `unhealthy`, `not ready` | Containers not ready |
| `pending` | Pending, ContainerCreating |
| `running`, `healthy` | Only healthy running pods |

See [`docs/kubernetes-integration.md`](docs/kubernetes-integration.md) for the full guide.

---

## Security Scanning

Natural language queries powered by the SimplePortChecker MCP server:

```
is port 443 open on example.com
check certificate for github.com
detect waf on mysite.com
full security scan on example.com
check mtls on api.example.com
check security headers on example.com
```

---

## Monitoring & Observability

### Health Endpoint Response

```json
{
  "status": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "kubernetes": "healthy (5 namespaces)",
  "prometheus": "healthy",
  "watchloop": "running",
  "pending_approvals": 0,
  "active_incidents": 0
}
```

### Observability Stack

| Component | Default Port | Purpose |
|---|---|---|
| Prometheus | 9090 | Metrics scraping |
| Grafana | 3000 | Dashboards |
| Alertmanager | 9093 | Alert routing |
| pgAdmin | 5050 | DB admin (debug profile) |
| redis-commander | 8081 | Redis admin (debug profile) |

```bash
# Start observability stack
docker compose up -d prometheus grafana alertmanager

# With debug tools
docker compose --profile debug up -d
```

### Alertmanager Integration

Add to `alertmanager.yml`:

```yaml
receivers:
  - name: simple-ai-agent
    webhook_configs:
      - url: http://simple-ai-agent:8000/api/alert/webhook
        send_resolved: true
        http_config:
          authorization:
            credentials: "your-alertmanager-webhook-secret"
```

---

## Configuration Reference

Copy `.env.example` to `.env`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `GITHUB_TOKEN` | yes | -- | GitHub fine-grained PAT with Models access |
| `DISCORD_TOKEN` | one of | -- | Discord bot token |
| `TELEGRAM_TOKEN` | one of | -- | Telegram bot token |
| `SLACK_BOT_TOKEN` | one of | -- | Slack bot token |
| `SLACK_SIGNING_SECRET` | one of | -- | Slack signing secret |
| `DATABASE_URL` | -- | postgres DSN | PostgreSQL async DSN |
| `REDIS_URL` | -- | `redis://localhost:6379/0` | Redis DSN |
| `LOG_LEVEL` | -- | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `ENVIRONMENT` | -- | `development` | `development` or `production` |
| `DEFAULT_MODEL` | -- | `gpt-4` | `gpt-4`, `claude-3-opus`, `llama-3-70b` |
| `RATE_LIMIT_PER_MINUTE` | -- | `60` | Per-IP rate limit |
| `K8S_WATCHLOOP_ENABLED` | -- | `true` | Enable AIOps background poller |
| `K8S_WATCHLOOP_INTERVAL` | -- | `30` | Poll interval in seconds |
| `AUTO_REMEDIATION_ENABLED` | -- | `false` | Skip approvals for LOW-risk steps |
| `AIOPS_NOTIFICATION_CHANNEL` | -- | -- | `telegram:CHAT_ID` or `discord:CHANNEL_ID` |
| `APPROVAL_TIMEOUT_SECONDS` | -- | `300` | Seconds before approval auto-expires |
| `PROMETHEUS_URL` | -- | -- | `http://prometheus:9090` |
| `GRAFANA_URL` | -- | -- | `http://grafana:3000` |
| `GRAFANA_API_KEY` | -- | -- | Grafana API key for annotations |
| `ALERTMANAGER_WEBHOOK_SECRET` | -- | -- | Webhook receiver validation secret |

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Root -- name, version, environment |
| `GET` | `/health` | Full health (DB, Redis, K8s, Prometheus, watchloop) |
| `GET` | `/ready` | Readiness probe |
| `POST` | `/api/webhook/telegram` | Telegram update webhook |
| `POST` | `/api/webhook/slack` | Slack Events API webhook |
| `POST` | `/api/alert/webhook` | Alertmanager webhook receiver |
| `GET` | `/api/webhook/test` | Webhook connectivity test |

---

## Project Structure

```
simple-ai-agent/
+-- src/
|   +-- main.py                   # Application entry point & lifespan
|   +-- config.py                 # Pydantic Settings (env vars)
|   +-- ai/
|   |   +-- github_models.py      # GitHub Models API client
|   |   +-- model_selector.py     # Per-user/channel model selection
|   |   +-- context_builder.py    # Conversation window builder
|   |   +-- prompt_manager.py     # System prompt templates
|   +-- channels/
|   |   +-- base.py               # BaseAdapter interface
|   |   +-- discord_adapter.py    # Discord.py adapter
|   |   +-- telegram_adapter.py   # python-telegram-bot adapter
|   |   +-- slack_adapter.py      # slack_bolt adapter
|   |   +-- router.py             # Fan-out / fan-in router
|   +-- api/
|   |   +-- health.py             # /health, /ready endpoints
|   |   +-- webhooks.py           # /api/webhook/* endpoints
|   |   +-- middleware.py         # Rate limiter setup
|   +-- services/
|   |   +-- message_handler.py    # Intent detection & routing
|   |   +-- session_manager.py    # Redis TTL sessions
|   |   +-- kubernetes_handler.py # NL K8s query handler
|   |   +-- approval_manager.py   # Human-in-the-loop approvals
|   |   +-- mcp_client.py         # Low-level MCP client helper
|   |   +-- mcp_registry.py       # Tool registry helpers
|   +-- mcp/
|   |   +-- mcp_manager.py        # Lifecycle + routing manager
|   |   +-- base_transport.py     # Transport ABC
|   |   +-- stdio_transport.py    # stdio (subprocess) transport
|   |   +-- sse_transport.py      # SSE (HTTP) transport
|   |   +-- kubernetes_server.py  # K8s MCP server implementation
|   +-- aiops/
|   |   +-- rule_engine.py        # Alert rule matching
|   |   +-- playbooks.py          # Playbook registry & executor
|   |   +-- rca_engine.py         # LLM-powered root-cause analysis
|   |   +-- log_analyzer.py       # Log pattern analysis
|   +-- monitoring/
|   |   +-- watchloop.py          # K8s background watch-loop
|   |   +-- prometheus.py         # Prometheus metrics helpers
|   |   +-- grafana.py            # Grafana annotation helper
|   +-- k8s/
|   |   +-- client.py             # Kubernetes API client wrapper
|   +-- database/
|       +-- models.py             # SQLAlchemy ORM models
|       +-- postgres.py           # Async engine + session factory
|       +-- redis.py              # Redis connection pool
|       +-- repositories/         # Data-access layer
|       +-- migrations/           # Alembic migration scripts
+-- scripts/
|   +-- mcp_server.py             # stdio MCP server (K8s tools)
|   +-- init_db.py                # Manual DB init helper
|   +-- start_server.sh           # Dev server launcher
|   +-- start_production.sh       # Production launcher
|   +-- stop_server.sh            # Graceful stop
+-- config/
|   +-- prometheus.yml            # Prometheus scrape config
|   +-- alertmanager.yml          # Alertmanager routing config
|   +-- alert_rules.yml           # Prometheus alert rules
|   +-- grafana/                  # Grafana provisioning
+-- docs/
|   +-- hld.d2                    # High-Level Design diagram (D2 source)
|   +-- architecture.md
|   +-- component-diagram.md
|   +-- sequence-diagrams.md
|   +-- database-architecture.md
|   +-- aiops.md
|   +-- kubernetes-integration.md
|   +-- mcp-integration.md
|   +-- mcp-registry.md
|   +-- slack-setup.md
+-- tests/
|   +-- conftest.py
+-- Dockerfile                    # Multi-stage, non-root, kubectl bundled
+-- docker-compose.yml            # Full stack: app + postgres + redis + observability
+-- .mcp-config.json              # MCP server configuration
+-- .env.example                  # Environment template (safe to commit)
+-- .env.production.example       # Production environment template
+-- alembic.ini                   # Migration config
+-- pyproject.toml                # Build + tool config
+-- requirements.txt              # Python dependencies
```

---

## Development

### Run Tests

```bash
pip install -r requirements.txt
pytest                       # all tests
pytest --cov=src             # with coverage report
pytest -k test_aiops         # filter specific tests
```

### Code Quality

```bash
black src/        # format
ruff check src/   # lint
mypy src/         # type check
```

### Database Migrations

```bash
alembic revision --autogenerate -m "add column foo"
alembic upgrade head
alembic downgrade -1
```

### Run with Docker Compose

```bash
# Full stack
docker compose up -d

# Including observability
docker compose up -d prometheus grafana alertmanager

# Debug tools (pgAdmin + redis-commander)
docker compose --profile debug up -d

# Follow logs
docker compose logs -f app
```

---

## Deployment

### Production Checklist

**Before deploy:**
- [ ] Set `GITHUB_TOKEN` and at least one bot token
- [ ] Set strong `POSTGRES_PASSWORD` and `REDIS_PASSWORD`
- [ ] Mount kubeconfig at `./data/kube/config` for K8s features
- [ ] Set `AIOPS_NOTIFICATION_CHANNEL` for alert routing
- [ ] Set `ALERTMANAGER_WEBHOOK_SECRET`
- [ ] Review CPU/memory limits in `docker-compose.yml`
- [ ] Enable TLS termination (nginx/Caddy in front)
- [ ] Configure log aggregation

**After deploy:**
- [ ] `GET /health` returns all subsystems healthy
- [ ] Test a message in each configured channel
- [ ] Test `/k8s pods` command
- [ ] Verify `"watchloop": "running"` in `/health`
- [ ] Monitor `docker compose logs -f app` for warnings

### Production Deploy

```bash
# 1. Copy and configure
cp .env.production.example .env.production
nano .env.production

# 2. Build with version metadata
export VERSION=$(git describe --tags --always)
export VCS_REF=$(git rev-parse --short HEAD)
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

docker compose build \
  --build-arg VERSION=$VERSION \
  --build-arg VCS_REF=$VCS_REF \
  --build-arg BUILD_DATE=$BUILD_DATE

# 3. Start
docker compose --env-file .env.production up -d

# 4. Verify
curl http://localhost:8000/health
```

### Resource Requirements

| Environment | CPU | RAM | Disk |
|---|---|---|---|
| Development | 1 core | 2 GB | 10 GB |
| Production (minimum) | 2 cores | 4 GB | 50 GB SSD |
| Production (recommended) | 4 cores | 8 GB | 100 GB SSD |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit using conventional commits: `feat: add X`, `fix: Y`, `docs: update Z`
4. Push and open a Pull Request against `main`

---

## Security

See [SECURITY.md](SECURITY.md) for the vulnerability disclosure policy.

**Built-in security practices:**
- All secrets via environment variables, never hardcoded
- `.env` excluded from git via `.gitignore`
- Non-root Docker user (UID 1000)
- `no-new-privileges` security option
- Pydantic validation on all inputs
- Rate limiting on all API endpoints
- Read-only kubeconfig mount
- Network isolation via Docker bridge networks

---

## License

[MIT License](LICENSE) -- Copyright 2026 Simple AI Agent Contributors

---

*Built with Python 3.12, FastAPI, discord.py, python-telegram-bot, slack_bolt, and the GitHub Models API*
