# AIOps Orchestrator

> A production-ready, multi-channel AI agent for AIOps, Kubernetes management, and automated remediation — built on FastAPI with support for **GitHub Models** and **Google Gemini** LLM backends.

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](Dockerfile)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psycopg/black)
[![Version](https://img.shields.io/badge/version-2.0.0-brightgreen.svg)](RELEASE_v2.0.0.md)
[![Status](https://img.shields.io/badge/status-Production--Stable-success.svg)](RELEASE_v2.0.0.md)

---

## 🎉 Latest Release: v2.0.0 (July 26, 2026)

**Status**: Production Ready ✅ | **[Full Release Notes →](RELEASE_v2.0.0.md)**

### Major Features

#### 🤖 Agent-to-Agent (A2A) Integration
Multi-agent orchestration platform with intelligent task delegation:
- **Natural Language Delegation**: `@agent-name do something` in chat
- **Structured API**: `@capability: param1=val1, param2=val2`
- **Chat Commands**: `/a2a agents`, `/a2a status`
- **JWT Authentication**: Secure agent-to-agent communication with capability-based access control
- **Agent Registry**: PostgreSQL + Redis backed with dynamic discovery (0.0-1.0 capability scoring)
- **Task Modes**: Synchronous (wait for result) & Asynchronous (webhook callbacks)
- **REST API**: 7 endpoints for external agent integration
- **Metrics**: 9 Prometheus metrics for complete observability

#### 🌐 API Backend Monitoring
Proactive external service monitoring:
- **Health Checks**: Downtime, latency (P95), error rates, SSL certificate expiration
- **Smart Alerts**: 4 alert conditions with auto-remediation playbooks
- **MCP Tools**: DNS lookup, curl test, SSL check, traceroute
- **Metrics**: 4 Prometheus metrics for Grafana dashboards
- **Configuration**: Per-endpoint thresholds and check intervals

### Release Statistics
- **32 New Components** | **8,500+ Lines of Code** | **52KB Documentation**
- **33 Unit Tests** | **8 Sequence Diagrams** | **13 New Prometheus Metrics**
- **+7 REST Endpoints** | **+3 Database Tables** | **Production/Stable**

### Quick Start (v2.0.0)

```bash
# Enable A2A Integration (optional)
export A2A_ENABLED=true
export A2A_AGENT_ID="aiops-orchestrator"
export A2A_JWT_SECRET="$(openssl rand -hex 32)"

# Run database migrations
docker compose exec aiops-orchestrator alembic upgrade head

# Deploy
docker compose up -d

# Verify health
curl http://localhost:8000/health
curl http://localhost:8000/health/a2a
curl http://localhost:8000/health/api-backends
```

**📚 Documentation**: [A2A Integration Guide](docs/a2a-integration.md) | [Sequence Diagrams](docs/a2a-sequence-diagrams.md) | [API Monitoring](docs/api-backend-monitoring.md)

---

## Table of Contents

- [Overview](#overview)
- [Feature Matrix](#feature-matrix)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Channel Setup](#channel-setup)
- [AI Backends](#ai-backends)
- [AIOps Engine](#aiops-engine)
- [Kubernetes Integration](#kubernetes-integration)
- [Monitoring & Observability](#monitoring--observability)
- [Configuration Reference](#configuration-reference)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Development](#development)
- [Production Deployment](#production-deployment)
- [Contributing](#contributing)

---

## Overview

AIOps Orchestrator connects **Telegram and Slack** to a powerful backend engine for proactive Kubernetes management and AIOps automation. It uses a dual-LLM architecture that routes requests to either **GitHub Models** (GPT-4o, Claude-3, Llama) or **Google Gemini** (2.5 Pro, 2.5 Flash, 2.0 Flash) based on user or system preference.

| Capability | Technology |
|---|---|
| LLM inference | GitHub Models API + Google Gemini API |
| AI routing | `AIRouter` — selects backend from model prefix |
| Chat persistence | PostgreSQL 16 (ACID, JSONB, Alembic migrations) |
| Session caching | Redis 7 (sub-ms access, TTL expiry) |
| Cluster ops | `kubectl` subprocess — 13 natural-language tools |
| AIOps | Watch-loop -> Rule engine -> Playbooks -> RCA |
| Approvals | Human-in-the-loop via chat message |
| Alerting | Prometheus + Alertmanager webhook receiver |
| Observability | Grafana dashboards, structlog JSON, `/metrics` |

---

## Feature Matrix

### Messaging Channels
- **Telegram** — Webhook mode, privacy-mode support, group and private chat
- **Slack** — Events API, app-mention, IM history, signing-secret verification

### AI / LLM

- **Dual-backend routing** — `AIRouter` dispatches to GitHub Models or Gemini based on model name prefix
- **GitHub Models** — GPT-4o, GPT-4, Claude-3 Opus, Llama-3-70B via `models.inference.ai.azure.com`
- **Google Gemini** — Gemini 2.5 Pro, 2.5 Flash, 2.0 Flash, 1.5 Pro, 1.5 Flash
- **Model selection priority** — conversation override -> user pref -> channel default -> system default
- **Conversation history** — stored in PostgreSQL, windowed into context
- **Streaming-compatible** — openai-compatible SDK for GitHub Models; native Gemini async client

### Kubernetes Management (13 tools)
- **Full CRUD** — pods, deployments, services, namespaces, nodes, events
- **Natural language** — "show me error pods in production"
- **Status filters** — error/failed/crash, unhealthy/not-ready, pending, running
- **Follow-up queries** — ask "show details" after a pod listing; context is cached in Redis
- **Scaling** — `/k8s scale <deployment> <replicas> [ns]`
- **Logs** — streaming and snapshot log retrieval
- **Resource usage** — `top pods`, `top nodes`
- **Multi-context** — switch between clusters

### AIOps Engine
- **K8s Watch-Loop** — background polling every 30 s (configurable)
  - Detects: `CrashLoopBackOff`, `OOMKilled`, `NotReady` nodes, zero-replica deployments
- **API Backend Watch-Loop** — external service health monitoring
  - Detects: downtime, high latency (p95), elevated error rates, SSL expiration
  - Configurable per-endpoint thresholds and check intervals
- **Rule Engine** — YAML-defined alert rules with severity mapping
- **Playbook Executor** — ordered step sequences with risk-gated execution
  - `LOW risk` — auto-execute, notify after
  - `MEDIUM risk` — post approval request, await chat response
  - `HIGH risk` — warn + require explicit confirmation
- **RCA Engine** — LLM-powered root-cause analysis (SRE prompt -> JSON report)
- **Log Analyzer** — structured log pattern matching
- **Approval Manager** — Redis-backed TTL approvals; chat-native `approve/reject`
- **Alertmanager receiver** — `POST /api/alert/webhook` ingests Prometheus alerts

### Agent-to-Agent (A2A) Integration
- **Agent Registry** — PostgreSQL + Redis-cached registry of AI agents
- **Dynamic Discovery** — Capability-based agent discovery with scoring (0.0-1.0)
- **Task Delegation** — Sync and async modes with automatic agent selection
- **Natural Language** — `@agent-name do something` syntax in chat
- **Structured API** — REST endpoints for registration, delegation, status
- **JWT Authentication** — Secure agent-to-agent communication
- **Webhook Callbacks** — Async task completion notifications
- **Multi-Agent Workflows** — Chain tasks across specialized agents

### Data & Performance
- **PostgreSQL 16** — users, conversations, messages, channel configs, JSONB metadata
- **Redis 7** — session cache (sub-ms), K8s context cache (30 min TTL), pending approvals (TTL 5 min)
- **Alembic migrations** — versioned schema management
- **Connection pooling** — async SQLAlchemy + asyncpg

### Production Hardening
- **Multi-stage Docker build** — kubectl bundled, OCI labels, non-root UID 1000
- **Security options** — `no-new-privileges`, isolated network, non-root container
- **Resource limits** — CPU and memory limits/reservations on every Compose service
- **Health endpoint** — DB, Redis, K8s, Prometheus, watchloop, pending approvals
- **Rate limiting** — `slowapi` per-IP rate limiter on all endpoints
- **Structured logging** — JSON via `structlog`, Docker log rotation (10 MB/3 files)

---

## Architecture

### High-Level Design

The full traffic-flow diagram is maintained as a D2 source file at [`docs/hld.d2`](docs/hld.d2).

**Render to PNG/SVG (requires [D2](https://d2lang.com)):**
```bash
d2 docs/hld.d2 docs/hld.svg
d2 docs/hld.d2 docs/hld.png --theme=0
```

#### Traffic Flow Summary

```
Users
  |
  +-- Telegram Webhook  --> /api/webhook     -+
  +-- Slack Events API  --> /api/webhook     -+
                                              |
                                      Channel Router
                                              |
                                     Message Handler
                          +----------+-----------+----------+
                          |          |           |          |
                   Session Mgr   AI Router   K8s Handler   Task Delegator
                     (Redis)       |         (NL parser)    (@agent cmds)
                               +---+---+         |              |
                               |       |      kubectl     Capability Matcher
                        GitHub Models  |    subprocess          |
                         (GPT-4o/   Gemini                Agent Registry
                          Claude)  (2.5 Pro/              (PostgreSQL+Redis)
                                   2.0 Flash)                   |
                                      |                    A2A Client (JWT)
                                 PostgreSQL                     |
                                 (history)              External AI Agents
                                                        (K8s, Logs, DB, etc.)

AIOps (async background):
  K8s Watch-Loop --+
  API Watch-Loop --+--> Rule Engine --> Playbook Executor --> Approval Manager
       |            |         |               |                     |
  K8s Cluster  External APIs  |         kubectl cmds            Redis TTL
                               |               |
                          Alert Rules    RCA Engine --> AIRouter (SRE prompt)

A2A Integration:
  External Agents --> POST /api/a2a/register --> Agent Registry
                  --> POST /api/a2a/delegate --> Task Delegator
                  --> POST /api/a2a/webhook  --> Message Handler (async results)

Observability:
  App /metrics --> Prometheus --> Grafana dashboards
                        |
                   Alertmanager --> POST /api/alert/webhook --> Rule Engine
```

### Layered Component Model

```
+-----------------------------------------------------+
|                   Channel Layer                      |  Telegram / Slack adapters
+-----------------------------------------------------+
|                     API Layer                        |  FastAPI, rate-limiter, webhooks
+-----------------------------------------------------+
|                 Business Logic Layer                 |  Message handler, session, K8s, approvals
+------------------------+----------------------------+
|        AI Layer        |       AIOps Layer          |  AIRouter (Gemini+GitHub) | watchloop, rules, RCA
+------------------------+----------------------------+
|                    A2A Layer                         |  Task delegator, agent registry, capability matcher
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
| [`docs/sequence-diagrams.md`](docs/sequence-diagrams.md) | Message flows and startup sequence |
| [`docs/database-architecture.md`](docs/database-architecture.md) | PostgreSQL & Redis schema + performance |
| [`docs/kubernetes-integration.md`](docs/kubernetes-integration.md) | K8s guide — NL queries, status filters |
| [`docs/aiops.md`](docs/aiops.md) | AIOps engine — watch-loop, rules, playbooks, RCA |
| [`docs/api-backend-monitoring.md`](docs/api-backend-monitoring.md) | External API health monitoring |
| [`docs/a2a-integration.md`](docs/a2a-integration.md) | Agent-to-Agent integration guide |
| [`docs/a2a-sequence-diagrams.md`](docs/a2a-sequence-diagrams.md) | A2A interaction flows |
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
git clone https://github.com/YOUR_USERNAME/aiops-orchestrator.git
cd aiops-orchestrator

python3.12 -m venv .venv
source .venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env — minimum required:
#   GITHUB_TOKEN or GEMINI_API_KEY + at least one bot token
```

### 3. Start Infrastructure

```bash
docker compose up -d postgres redis
```

### 4. Run the Agent

```bash
./scripts/start_server.sh
# Or directly:
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Verify

```bash
curl http://localhost:8000/health
# {"status":"healthy","database":"healthy","redis":"healthy",...}
```

---

## Channel Setup

### GitHub Token (Required for GitHub Models)

1. Visit <https://github.com/settings/tokens> -> **Fine-grained personal access token**
2. Enable **Models API** permission
3. Set `GITHUB_TOKEN` in `.env`

### Telegram

1. Message **@BotFather** -> `/newbot`
2. Copy token -> `TELEGRAM_TOKEN`
3. **Groups:** Disable privacy mode via @BotFather -> Bot Settings -> Group Privacy -> OFF

### Slack

1. <https://api.slack.com/apps> -> New App -> From scratch
2. OAuth scopes: `app_mentions:read`, `chat:write`, `im:history`, `users:read`
3. Install to workspace -> copy Bot User OAuth Token -> `SLACK_BOT_TOKEN`
4. Event Subscriptions webhook: `https://your-domain.com/api/webhook/slack`
5. Subscribe to: `app_mention`, `message.im`

See [`docs/slack-setup.md`](docs/slack-setup.md) for the full walkthrough.

---

## AI Backends

AIOps Orchestrator supports two LLM backends, selectable per-conversation with `/model`.

### GitHub Models

Accessed via `https://models.inference.ai.azure.com` using your GitHub fine-grained PAT.

| Alias | Model |
|---|---|
| `gpt-4o` | GPT-4o |
| `gpt-4` | GPT-4 |
| `claude-3-opus` | Claude 3 Opus |
| `llama-3-70b` | Meta Llama 3 70B Instruct |

**Requires:** `GITHUB_TOKEN` in `.env`

### Google Gemini

Accessed via the `google-generativeai` SDK with your Gemini API key.

| Alias | Model |
|---|---|
| `gemini-2.5-pro` | Gemini 2.5 Pro |
| `gemini-2.5-flash` | Gemini 2.5 Flash |
| `gemini-2.0-flash` | Gemini 2.0 Flash |
| `gemini-1.5-pro` | Gemini 1.5 Pro |
| `gemini-1.5-flash` | Gemini 1.5 Flash |

**Requires:** `GEMINI_API_KEY` in `.env`
**Get a key at:** <https://aistudio.google.com/app/apikey>

### Switching Models

Send in any chat:
```
/model gemini-2.5-flash
/model gpt-4o
/model claude-3-opus
```

The `AIRouter` selects the backend automatically: model names beginning with `gemini` route to Gemini; all others route to GitHub Models.

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
       Risk: MEDIUM — type 'approve abc123' or 'reject abc123'"
        |
   +----+----+
approve    reject
   |           |
Execute     Cancel
step        playbook
```

### AIOps Configuration

```env
K8S_WATCHLOOP_ENABLED=true
K8S_WATCHLOOP_INTERVAL=30
AUTO_REMEDIATION_ENABLED=false
AIOPS_NOTIFICATION_CHANNEL=telegram:YOUR_CHAT_ID
APPROVAL_TIMEOUT_SECONDS=300
ALERTMANAGER_WEBHOOK_SECRET=your-secret
```

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
| `/k8s top pods/nodes` | Resource usage |
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

### Follow-up Queries

After any pod listing, ask follow-up questions without repeating the namespace:

```
> show me pods in production
[list of pods]

> can you show details of the error pods
[full details using cached context]
```

### Status Filters

| Keywords | Shows |
|---|---|
| `error`, `failed`, `crash` | CrashLoopBackOff, Error, ImagePullBackOff |
| `unhealthy`, `not ready` | Containers not ready |
| `pending` | Pending, ContainerCreating |
| `running`, `healthy` | Only healthy running pods |

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
| Jaeger | 16686 | Distributed tracing (opt-in) |
| pgAdmin | 5050 | DB admin (debug profile) |
| redis-commander | 8081 | Redis admin (debug profile) |

```bash
docker compose up -d prometheus grafana alertmanager
docker compose --profile debug up -d
```

### Alertmanager Integration

```yaml
receivers:
  - name: aiops-orchestrator
    webhook_configs:
      - url: http://aiops-orchestrator:8000/api/alert/webhook
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
| `GITHUB_TOKEN` | one of | — | GitHub fine-grained PAT with Models access |
| `GEMINI_API_KEY` | one of | — | Google Gemini API key |
| `TELEGRAM_TOKEN` | one of | — | Telegram bot token |
| `SLACK_BOT_TOKEN` | one of | — | Slack bot token |
| `SLACK_SIGNING_SECRET` | one of | — | Slack signing secret |
| `DATABASE_URL` | — | postgres DSN | PostgreSQL async DSN |
| `REDIS_URL` | — | `redis://localhost:6379/0` | Redis DSN |
| `LOG_LEVEL` | — | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `ENVIRONMENT` | — | `development` | `development` or `production` |
| `DEFAULT_MODEL` | — | `gpt-4` | `gpt-4`, `gemini-2.0-flash`, etc. |
| `RATE_LIMIT_PER_MINUTE` | — | `60` | Per-IP rate limit |
| `K8S_WATCHLOOP_ENABLED` | — | `true` | Enable AIOps background poller |
| `K8S_WATCHLOOP_INTERVAL` | — | `30` | Poll interval in seconds |
| `AUTO_REMEDIATION_ENABLED` | — | `false` | Skip approvals for LOW-risk steps |
| `AIOPS_NOTIFICATION_CHANNEL` | — | — | `telegram:CHAT_ID` or `slack:CHANNEL_ID` |
| `APPROVAL_TIMEOUT_SECONDS` | — | `300` | Seconds before approval auto-expires |
| `PROMETHEUS_URL` | — | — | `http://prometheus:9090` |
| `GRAFANA_URL` | — | — | `http://grafana:3000` |
| `GRAFANA_API_KEY` | — | — | Grafana API key for annotations |
| `ALERTMANAGER_WEBHOOK_SECRET` | — | — | Webhook receiver validation secret |
| `OTEL_ENABLED` | — | `false` | Enable OpenTelemetry tracing |
| `OTLP_ENDPOINT` | — | `http://jaeger:4317` | OTLP gRPC endpoint |
| `OTEL_SERVICE_NAME` | — | `aiops-orchestrator` | Service name in traces |
| `A2A_ENABLED` | — | `false` | Enable Agent-to-Agent integration |
| `A2A_AGENT_ID` | — | — | This orchestrator's A2A agent ID |
| `A2A_AGENT_NAME` | — | `aiops-orchestrator` | Display name for A2A |
| `A2A_AGENTS_CONFIG_PATH` | — | `config/agents.yml` | Agent registry config file |
| `A2A_JWT_SECRET` | — | `change-me-in-production` | JWT signing secret ⚠️ **MUST change in prod** |
| `A2A_WEBHOOK_URL` | — | — | Callback URL for async task results |
| `A2A_TOKEN_EXPIRY_HOURS` | — | `1` | JWT token expiration time |
| `API_BACKENDS_CONFIG_PATH` | — | `config/api_backends.yml` | API monitoring config |
| `API_WATCHLOOP_ENABLED` | — | `false` | Enable external API monitoring |
| `API_WATCHLOOP_INTERVAL` | — | `60` | API health check interval (seconds) |

---

## API Reference

### Core Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Root — name, version, environment |
| `GET` | `/health` | Full health (DB, Redis, K8s, Prometheus, watchloop, A2A) |
| `GET` | `/health/a2a` | A2A subsystem health (agents, registry, tasks) |
| `GET` | `/health/api-backends` | External API monitoring status |
| `GET` | `/ready` | Readiness probe |
| `GET` | `/metrics` | Prometheus metrics endpoint |

### Webhook Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/webhook/telegram` | Telegram update webhook |
| `POST` | `/api/webhook/slack` | Slack Events API webhook |
| `POST` | `/api/alert/webhook` | Alertmanager webhook receiver |
| `GET` | `/api/webhook/test` | Webhook connectivity test |

### A2A Endpoints (v2.0.0)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/a2a/register` | Register new AI agent |
| `GET` | `/api/a2a/agents` | List all registered agents |
| `GET` | `/api/a2a/agents/{agent_id}` | Get agent details |
| `DELETE` | `/api/a2a/agents/{agent_id}` | Deregister agent |
| `POST` | `/api/a2a/delegate` | Delegate task to agent |
| `GET` | `/api/a2a/tasks/{task_id}` | Get task status |
| `POST` | `/api/a2a/webhook` | Receive async task completion |

---

## Chat Commands

### General Commands

| Command | Description |
|---|---|
| `/help` | Show available commands |
| `/model <name>` | Switch AI model (`gpt-4o`, `gemini-2.5-flash`, `claude-3-opus`, etc.) |
| `/health` | Check system health status |

### Kubernetes Commands

| Command | Description |
|---|---|
| `/k8s pods [namespace]` | List pods |
| `/k8s deployments [namespace]` | List deployments |
| `/k8s services [namespace]` | List services |
| `/k8s nodes` | List cluster nodes |
| `/k8s namespaces` | List all namespaces |
| `/k8s scale <deployment> <replicas> [namespace]` | Scale deployment |
| `/k8s logs <pod> [namespace]` | Get pod logs |
| `/k8s describe <resource> <name> [namespace]` | Describe resource |
| `/k8s events [namespace]` | Show recent events |

### A2A Commands (v2.0.0)

| Command | Description |
|---|---|
| `/a2a help` | Show A2A command reference |
| `/a2a agents [capability]` | List registered agents (optional filter by capability) |
| `/a2a agent <id>` | Show detailed agent information |
| `/a2a status` | Show A2A system status |
| `@agent-name <task>` | Natural language task delegation |
| `@capability: param=value, param2=value2` | Structured task delegation |

### Approval Commands

| Command | Description |
|---|---|
| `approve <id>` | Approve pending remediation action |
| `reject <id>` | Reject pending remediation action |

### Natural Language Examples

```
# Kubernetes queries
"show me all error pods in production"
"what pods are not ready?"
"scale the api deployment to 10 replicas"

# A2A delegation
"@k8s-operator restart the api-server pods in production"
"@log-analyzer find errors in api-service from last 24 hours"
"@database.query: database=analytics, query=SELECT COUNT(*) FROM errors"
```

---

## Project Structure

```
aiops-orchestrator/
├── src/
│   ├── main.py                   # Application entry point & lifespan
│   ├── config.py                 # Pydantic Settings (env vars)
│   ├── exceptions.py             # Custom exception classes
│   ├── ai/
│   │   ├── base_client.py        # BaseAIClient ABC
│   │   ├── ai_router.py          # Route by model prefix to GitHub/Gemini
│   │   ├── github_models.py      # GitHub Models API client
│   │   ├── gemini_client.py      # Google Gemini API client
│   │   ├── model_selector.py     # Per-user/channel model selection
│   │   ├── context_builder.py    # Conversation window builder
│   │   └── prompt_manager.py     # System prompt templates
│   ├── channels/
│   │   ├── base.py               # BaseAdapter interface
│   │   ├── telegram_adapter.py   # python-telegram-bot adapter
│   │   ├── slack_adapter.py      # slack_bolt adapter
│   │   └── router.py             # Fan-out / fan-in router
│   ├── api/
│   │   ├── health.py             # /health, /ready, /health/a2a, /health/api-backends
│   │   ├── webhooks.py           # /api/webhook/* endpoints
│   │   ├── a2a_endpoints.py      # /api/a2a/* REST API (7 endpoints)
│   │   └── middleware.py         # Rate limiter setup
│   ├── services/
│   │   ├── message_handler.py    # Intent detection & routing + A2A delegation
│   │   ├── session_manager.py    # Redis TTL sessions
│   │   ├── kubernetes_handler.py # NL K8s query handler
│   │   ├── approval_manager.py   # Human-in-the-loop approvals
│   │   ├── agent_registry.py     # A2A agent registration & discovery
│   │   ├── task_delegator.py     # A2A task delegation orchestrator
│   │   ├── capability_matcher.py # A2A capability scoring (0.0-1.0)
│   │   ├── a2a_auth.py           # JWT & API key authentication
│   │   ├── a2a_client.py         # HTTP client for agent-to-agent calls
│   │   ├── mcp_client.py         # MCP client for tool invocation
│   │   └── mcp_registry.py       # MCP server registry
│   ├── models/
│   │   ├── agent.py              # A2A Pydantic models (10 classes)
│   │   └── api_backend.py        # API backend config & status models
│   ├── aiops/
│   │   ├── rule_engine.py        # Alert rule matching (K8s + API backends)
│   │   ├── playbooks.py          # Playbook registry & executor
│   │   ├── rca_engine.py         # LLM-powered root-cause analysis
│   │   └── log_analyzer.py       # Log pattern analysis
│   ├── monitoring/
│   │   ├── watchloop.py          # K8s background watch-loop
│   │   ├── api_watchloop.py      # External API health monitoring
│   │   ├── metrics.py            # Prometheus metrics definitions
│   │   ├── prometheus.py         # Prometheus metrics helpers
│   │   ├── grafana.py            # Grafana annotation helper
│   │   └── tracing.py            # OpenTelemetry setup
│   ├── mcp/
│   │   ├── base_transport.py     # Base MCP transport interface
│   │   ├── stdio_transport.py    # Stdio MCP transport
│   │   ├── sse_transport.py      # SSE MCP transport
│   │   ├── kubernetes_server.py  # MCP Kubernetes server (13 tools)
│   │   ├── api_tools.py          # API diagnostic tools (4 tools)
│   │   └── mcp_manager.py        # MCP server lifecycle manager
│   ├── k8s/
│   │   └── client.py             # Kubernetes client wrapper
│   ├── utils/
│   │   └── logger.py             # Structured logging setup
│   └── database/
│       ├── models.py             # SQLAlchemy ORM models (+ A2A tables)
│       ├── postgres.py           # Async engine + session factory
│       ├── redis.py              # Redis connection pool
│       ├── migrations/           # Alembic migration versions
│       └── repositories/         # Data-access layer (CRUD)
├── scripts/
│   ├── init_db.py                # Manual DB init helper
│   ├── start_server.sh           # Dev server launcher
│   ├── start_production.sh       # Production launcher
│   └── stop_server.sh            # Graceful stop
├── config/
│   ├── prometheus.yml            # Prometheus scrape config
│   ├── alertmanager.yml          # Alertmanager routing config
│   ├── alert_rules.yml           # Prometheus alert rules (K8s + API)
│   ├── api_backends.yml          # External API monitoring config
│   ├── agents.yml                # A2A agent registry config
│   └── grafana/                  # Grafana provisioning
├── helm/
│   └── aiops-orchestrator/       # Helm chart for Kubernetes deployment
├── docs/                         # Architecture and integration guides
├── tests/
├── Dockerfile                    # Multi-stage, non-root, kubectl bundled
├── docker-compose.yml            # Full stack: app + postgres + redis + observability
├── .env.example                  # Environment template (safe to commit)
├── .env.production.example       # Production environment template
├── alembic.ini                   # Migration config
├── pyproject.toml                # Build + tool config
└── requirements.txt              # Python dependencies
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

### Run with Docker Compose (Development)

```bash
docker compose up -d postgres redis app
docker compose up -d prometheus grafana alertmanager
docker compose --profile debug up -d
docker compose logs -f app
```

---

## Production Deployment

### Production Checklist

**Before deploy:**
- [ ] Set `GITHUB_TOKEN` and/or `GEMINI_API_KEY`
- [ ] Set at least one bot token (`TELEGRAM_TOKEN` or `SLACK_BOT_TOKEN`)
- [ ] Set strong `POSTGRES_PASSWORD` (never use default)
- [ ] Mount kubeconfig at `./data/kube/config` for K8s features
- [ ] Set `AIOPS_NOTIFICATION_CHANNEL` for proactive alerts
- [ ] Set `ALERTMANAGER_WEBHOOK_SECRET`
- [ ] Review CPU/memory limits in `docker-compose.yml`
- [ ] Set up TLS termination (nginx / Caddy / Cloudflare Tunnel) in front of port 8000
- [ ] Set `CLOUDFLARE_TUNNEL_TOKEN` if using Cloudflare Tunnel

**After deploy:**
- [ ] `GET /health` returns all subsystems healthy
- [ ] Test a message in each configured channel
- [ ] Test `/k8s pods` command
- [ ] Verify `"watchloop": "running"` in `/health`
- [ ] Monitor `docker compose logs -f app` for warnings

### Build & Deploy

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

# 3. Start full stack
docker compose --env-file .env.production up -d

# 4. Run database migrations
docker compose --env-file .env.production exec app alembic upgrade head

# 5. Verify
curl http://localhost:8000/health
```

### Production-Only Start

```bash
docker compose --env-file .env.production up -d \
  app postgres redis cloudflared prometheus grafana alertmanager
```

### Kubernetes (Helm)

```bash
helm install aiops-orchestrator ./helm/aiops-orchestrator \
  --namespace aiops \
  --create-namespace \
  --set secrets.githubToken="$GITHUB_TOKEN" \
  --set secrets.telegramToken="$TELEGRAM_TOKEN"
```

### Resource Requirements

| Environment | CPU | RAM | Disk |
|---|---|---|---|
| Development | 1 core | 2 GB | 10 GB |
| Production (minimum) | 2 cores | 4 GB | 50 GB SSD |
| Production (recommended) | 4 cores | 8 GB | 100 GB SSD |

### Security Notes

- The app container runs as non-root UID 1000 (`appuser`)
- All services use `no-new-privileges:true` security option
- PostgreSQL and Redis ports are bound to `127.0.0.1` only
- Cloudflare Tunnel is used for public webhook exposure without opening inbound ports

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
