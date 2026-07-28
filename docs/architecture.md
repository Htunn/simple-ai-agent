# Architecture Design

## Overview

AIOps Orchestrator is a production-ready multi-channel conversational AI system built with a modular, layered architecture. The system follows Domain-Driven Design (DDD) principles with clear separation of concerns across presentation, application, domain, and infrastructure layers.

## Core Principles

### 1. Modularity
Each component has a single, well-defined responsibility and can be modified or replaced independently.

### 2. Async-First
All I/O operations use Python's asyncio for high concurrency and efficient resource utilization.

### 3. Type Safety
Comprehensive type hints with Pydantic for runtime validation and MyPy for static type checking.

### 4. Security by Default
- Environment-based configuration
- Input validation at boundaries
- Rate limiting
- Secure credential management

### 5. Observability
- Structured logging with context
- Health checks for all services
- Token usage tracking

## Architecture Layers

### Presentation Layer (Channels)
Handles external communication with messaging platforms.

**Components:**
- `ChannelAdapter` (Abstract Base)
- `TelegramAdapter`
- `SlackAdapter`
- `MessageRouter`

**Responsibilities:**
- Protocol translation (Telegram/Slack → ChannelMessage)
- Message sending/receiving
- Platform-specific formatting

### Application Layer (Services)
Orchestrates business logic and coordinates between layers.

**Components:**
- `MessageHandler` - Core message processing orchestration
- `SessionManager` - User session lifecycle management

**Responsibilities:**
- Command processing (`/help`, `/model`, `/reset`, `/status`)
- Message flow coordination
- Session state management

### Domain Layer (AI & Business Logic)
Contains core business logic and AI integration.

**Components:**
- `AIRouter` - Multi-backend LLM routing (4 backends: GitHub Models, Gemini, vLLM, Ollama)
- `GitHubModelsClient` - GitHub Models API integration (default backend)
- `GeminiClient` - Google Gemini API integration
- `VLLMClient` - Self-hosted vLLM server integration
- `OllamaClient` - Local Ollama server integration
- `ModelSelector` - Model preference resolution
- `ContextBuilder` - Conversation context construction
- `PromptManager` - System prompt templates

**Responsibilities:**
- AI backend selection logic (model name pattern matching)
- Model prefix stripping (vllm:, ollama:)
- Conversation context building
- Prompt engineering
- Response generation (streaming and non-streaming)

### Infrastructure Layer (Database & Cache)
Manages data persistence and caching.

**Components:**
- `PostgresConnection` - Database connection pool
- `RedisCache` - Session cache
- `Repositories` - Data access objects
- `Models` - SQLAlchemy ORM models

**Responsibilities:**
- Data persistence
- Session caching
- Database migrations
- Query optimization

### API Layer (Web Interface)
Provides HTTP endpoints for webhooks and monitoring.

**Components:**
- `FastAPI Application`
- `HealthRouter` - Health checks
- `WebhookRouter` - Channel webhooks
- `RateLimiter` - Request throttling

**Responsibilities:**
- Webhook handling
- Health monitoring
- Rate limiting
- API documentation

## Data Flow

### Message Processing Flow

1. **Ingestion**: Message arrives via Telegram/Slack
2. **Normalization**: Channel adapter converts to `ChannelMessage`
3. **Routing**: Message router forwards to message handler
4. **Session Resolution**: Session manager gets/creates session
5. **Command Check**: Handler checks for commands (`/help`, etc.)
6. **Context Building**: Load conversation history from database
7. **Model Selection**: Determine AI model based on preferences
8. **AI Generation**: Call GitHub Models API
9. **Persistence**: Save user + assistant messages
10. **Response**: Send reply through channel adapter

### Session Management Flow

1. **Cache Check**: Look for session in Redis
2. **Cache Miss**: Query PostgreSQL for user/conversation
3. **Create if Needed**: Create new user/conversation
4. **Cache Store**: Store session data in Redis with TTL
5. **Activity Update**: Update timestamps on message
6. **Expiry**: Session expires after TTL (default 1 hour)

### Model Selection Priority

```
1. Conversation.model_override (per-conversation setting via /model command)
   ↓ (if not set)
2. User.preferred_model (user preference)
   ↓ (if not set)
3. ChannelConfig.default_model (channel default)
   ↓ (if not set)
4. Settings.default_model (system default)
```

### Backend Routing Logic

```
1. Model starts with "gemini-" → GeminiClient
2. Model contains "/" or starts with "vllm:" → VLLMClient
3. Model matches Ollama patterns or starts with "ollama:" → OllamaClient
4. Everything else → GitHubModelsClient (default)
```

## Key Design Decisions

### 1. Why Async/Await?
- **Non-blocking I/O**: Handle thousands of concurrent conversations
- **Efficient Resource Usage**: Single-threaded event loop
- **Modern Python**: Native support in Python 3.12

### 2. Why PostgreSQL + Redis?
- **PostgreSQL**: ACID compliance, rich querying, JSONB support
- **Redis**: Sub-millisecond latency, perfect for session cache
- **Best of Both**: Durability + Performance

### 3. Why Message Persistence?
- **Conversation History**: Full context for AI models
- **Analytics**: Usage patterns, popular queries
- **Debugging**: Audit trail for issues
- **Compliance**: Data retention policies

### 4. Why Abstract Channel Adapters?
- **Extensibility**: Easy to add new channels (WhatsApp, Slack)
- **Testability**: Mock adapters for testing
- **Separation**: Platform logic isolated from business logic

### 5. Why GitHub Models API?
- **Multiple Models**: GPT-4, Claude, Llama in one API
- **GitHub Integration**: Seamless for developers
- **Cost Management**: Unified billing
- **Reliability**: GitHub's infrastructure

## Scalability Considerations

### Horizontal Scaling
- **Stateless Application**: No in-memory state (sessions in Redis)
- **Load Balancing**: Multiple app containers behind ALB/nginx
- **Database Connection Pooling**: Max connections configurable

### Vertical Scaling
- **PostgreSQL**: Tune work_mem, shared_buffers
- **Redis**: Increase maxmemory as needed
- **Python**: Use uvloop for faster event loop

### Bottleneck Mitigation
- **Session Cache**: Reduce database queries
- **Message Chunking**: Handle long responses
- **Rate Limiting**: Prevent API abuse
- **Connection Pooling**: Reuse database connections

## Security Architecture

### Defense in Depth

1. **Input Validation**: Pydantic schemas at API boundary
2. **Environment Isolation**: Secrets never in code
3. **Rate Limiting**: Per-IP and per-user limits
4. **SQL Injection**: Parameterized queries (SQLAlchemy)
5. **Container Security**: Non-root user, minimal image

### Credential Management
- **Development**: `.env` files (git-ignored)
- **Production**: Secrets manager (AWS/Azure/Vault)
- **Rotation**: Regular token rotation policy

### Channel Security
- **Telegram**: Webhook signature verification
- **Slack**: Signing-secret HMAC verification
- **GitHub**: Fine-grained token with minimal scope

## Deployment Architecture

### Docker Compose (Development/Small Production)
```
┌─────────────────┐
│   nginx/Traefik │  (Optional reverse proxy)
└────────┬────────┘
         │
    ┌────▼─────┐
    │   App    │  (Python 3.12 container)
    │Container │
    └────┬─────┘
         │
    ┌────┴─────┐
    │          │
┌───▼───┐  ┌──▼────┐
│Postgres│  │ Redis │
└────────┘  └───────┘
```

### Production (Cloud)
```
┌──────────────┐
│  Load Balancer│
└──────┬────────┘
       │
   ┌───┴────┬────────┬─────────┐
   │        │        │         │
┌──▼──┐  ┌─▼──┐  ┌─▼──┐   ┌──▼──┐
│App 1│  │App 2│  │App 3│...│App N│
└──┬──┘  └─┬──┘  └─┬──┘   └──┬──┘
   │       │       │          │
   └───────┴───────┴──────────┘
           │
      ┌────┴─────┐
      │          │
  ┌───▼───┐  ┌──▼────┐
  │ RDS   │  │ElastiCache│
  │Postgres│  │ Redis │
  └────────┘  └───────┘
```

## Monitoring & Observability

### Metrics to Track
- **Request Rate**: Messages per second
- **Latency**: P50, P95, P99 response times
- **Error Rate**: Failed message processing
- **Token Usage**: API costs per model
- **Session Count**: Active conversations
- **Database Connections**: Pool utilization

### Health Checks
- **Liveness**: `/health` - Is app running?
- **Readiness**: `/ready` - Can handle requests?
- **Deep Health**: Database + Redis connectivity

### Logging Strategy
- **Structured Logs**: JSON format with context
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Correlation IDs**: Track requests across services
- **Sensitive Data**: Never log tokens or personal info

## Extension Points

### Adding New Channels
1. Implement `ChannelAdapter` interface
2. Override `send_message()`, `parse_message()`, `start()`, `stop()`
3. Register in `MessageRouter`

### Adding New AI Models
1. Add model mapping to `GitHubModelsClient.SUPPORTED_MODELS`
2. Update command help in `PromptManager`

### Custom Commands
1. Add handler in `MessageHandler._handle_command()`
2. Update help text

### Webhooks
1. Add route in `src/api/webhooks.py`
2. Implement signature verification
3. Forward to channel adapter

## Performance Characteristics

### Typical Latencies
- **Session Lookup**: <5ms (Redis cache hit)
- **Database Query**: 10-50ms (PostgreSQL)
- **AI Response**: 1-5s (depends on model)
- **Total End-to-End**: 1.5-6s

### Throughput
- **Single Instance**: ~100 concurrent conversations
- **With Scaling**: 1000+ conversations (10 instances)

### Resource Usage
- **Memory**: ~200MB per instance
- **CPU**: <10% idle, 50-70% under load
- **Database**: ~10 connections per instance

---

## AIOps Architecture

The AIOps subsystem transforms the agent from a reactive chatbot into a **proactive SRE assistant** that watches the Kubernetes cluster 24/7 and autonomously (or with human approval) remediates detected issues.

### AIOps Data Flow

```
Kubernetes API
      │  (poll every 30s)
      ▼
 K8sWatchLoop  ──────────────────────────────────────────────────┐
      │ ClusterEvent                                              │
      │ (crash_loop / oom_killed                                  │
      │  not_ready_node / replication_failure)                    │
      ▼                                                           │
 RuleEngine                                                       │
      │ matching rules → playbook_ids                            │
      ▼                                                           │
 PlaybookExecutor  ──────── LOW risk ──▶ MCPManager ──▶ K8s API  │
      │                                                           │
      └── MEDIUM/HIGH risk ──▶ ApprovalManager                   │
                                    │ Redis (TTL)                 │
                                    │ Approval message            │
                                    ▼                             │
                              Chat User (SRE)                     │
                                    │ approve / reject            │
                                    ▼                             │
                              MCPManager ──▶ K8s API              │
                                                                   │
 Alertmanager Webhook ──────────────────────────────────────────▶ │
 (Prometheus → /api/webhook/alertmanager)                         │
                                                                   │
 RCAEngine (GPT-4o) ◀──────────────────────────── on demand ──────┘
 LogAnalyzer (regex + GPT-4o-mini)
```

### AIOps Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `K8sWatchLoop` | `src/monitoring/watchloop.py` | Background polling; emits `ClusterEvent` |
| `RuleEngine` | `src/aiops/rule_engine.py` | Event-to-playbook matching with filters |
| `PlaybookRegistry` | `src/aiops/playbooks.py` | Library of 5 built-in remediation playbooks |
| `PlaybookExecutor` | `src/aiops/playbooks.py` | Runs steps: LOW→immediate, MED/HIGH→approval gate |
| `ApprovalManager` | `src/services/approval_manager.py` | Redis-backed human-in-the-loop gate |
| `RCAEngine` | `src/aiops/rca_engine.py` | GPT-4o root cause analysis with structured output |
| `LogAnalyzer` | `src/aiops/log_analyzer.py` | 14-pattern regex scan + AI enrichment |
| `KubernetesHandler` | `src/services/kubernetes_handler.py` | NLP-to-kubectl command dispatch |
| `KubernetesClient` | `src/k8s/client.py` | Async kubernetes-asyncio singleton |

### Risk Level Routing

```
RiskLevel.LOW    → PlaybookExecutor calls MCP immediately, notifies user of output
RiskLevel.MEDIUM → ApprovalManager: 🟠 posts approval request, pauses execution
RiskLevel.HIGH   → ApprovalManager: 🔴 posts HIGH RISK warning, pauses execution
```

### Built-in Remediation Playbooks

| Playbook | Trigger | Auto-runs | Requires Approval |
|----------|---------|-----------|-------------------|
| `crash_loop_remediation` | CrashLoopBackOff | Describe + logs | Pod restart |
| `oom_kill_remediation` | OOMKilled | Describe | Memory patch (HIGH) |
| `deployment_rollback` | 0 replicas | Rollout history | Rollback (HIGH) |
| `node_not_ready_remediation` | NotReady node | Describe | Cordon (MED) + Drain (HIGH) |
| `scale_up_on_load` | HPA maxReplicas | — | Scale (MED) |

### Event Deduplication

The watchloop tracks `_known_issues` (a dict keyed by `resource_kind/namespace/name`) to ensure each incident fires **exactly one alert**, regardless of poll frequency. When a resource recovers, its entry is removed and the next occurrence fires a fresh alert.

```python
# Example keys
"pod/prod/nginx-abc"        # cleared when pod exits crash state
"node/k3s-node-1"           # cleared when node becomes Ready
"deployment/prod/api-svc"   # cleared when replicas > 0
```

→ For full sequence diagrams see [sequence-diagrams.md](./sequence-diagrams.md) (diagrams 7–11)  
→ For complete AIOps docs see [aiops.md](./aiops.md)

---

## Future Enhancements

### Planned Features
- [ ] WhatsApp Business API integration
- [ ] Conversation search and analytics dashboard
- [ ] Multi-language support
- [ ] Voice message transcription
- [ ] Image generation integration
- [ ] Custom training data fine-tuning
- [ ] A/B testing for prompts
- [ ] Conversation export (PDF, JSON)

### Technical Debt
- [ ] Comprehensive test coverage (unit + integration)
- [ ] OpenTelemetry instrumentation
- [ ] Distributed tracing
- [ ] Circuit breaker pattern for AI API
- [ ] Database read replicas
- [ ] Redis Sentinel for HA

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Python Telegram Bot](https://python-telegram-bot.readthedocs.io/)
- [GitHub Models](https://github.com/marketplace/models)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

---

## Agent-to-Agent (A2A) Architecture

### Overview

The A2A layer enables multi-agent orchestration by providing a standardized protocol for agent registration, discovery, and task delegation. This allows the AIOps Orchestrator to coordinate with specialized external agents for complex workflows.

### A2A Components

```
┌─────────────────────────────────────────────────────────────┐
│                    AIOps Orchestrator                        │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐  │
│  │Message Handler│──│Task Delegator │──│Agent Registry   │  │
│  └──────┬───────┘  └───────┬───────┘  └─────────┬───────┘  │
│         │                   │                     │          │
│  ┌──────▼───────┐  ┌───────▼───────┐  ┌─────────▼───────┐  │
│  │@agent parser │  │Capability     │  │PostgreSQL       │  │
│  │(NL & struct) │  │Matcher        │  │+ Redis Cache    │  │
│  └──────────────┘  └───────┬───────┘  └─────────────────┘  │
│                             │                                │
│                     ┌───────▼───────┐                        │
│                     │A2A Client     │                        │
│                     │(HTTP + JWT)   │                        │
│                     └───────┬───────┘                        │
└─────────────────────────────┼─────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
        ┌───────────▼──────────┐  ┌─────▼──────────────┐
        │External Agent 1      │  │External Agent 2    │
        │(K8s Operator)        │  │(Log Analyzer)      │
        │                      │  │                    │
        │Capabilities:         │  │Capabilities:       │
        │• kubernetes.scale    │  │• logs.search       │
        │• kubernetes.restart  │  │• logs.patterns     │
        └──────────────────────┘  └────────────────────┘
```

### A2A Data Flow

#### 1. Agent Registration

```
External Agent           A2A API            Agent Registry       Database
      │                    │                      │                  │
      ├─POST /a2a/register─►                     │                  │
      │  {agent_id, name,  │                     │                  │
      │   capabilities[],  │                     │                  │
      │   url, version}    │                     │                  │
      │                    │                      │                  │
      │                    ├──register_agent()───►                  │
      │                    │                      ├──INSERT agents──►
      │                    │                      │                  │
      │                    │                      ◄──agent record───┤
      │                    │                      │                  │
      │                    │                      ├──Cache (Redis)──►
      │                    │                      │   TTL: 5min      │
      │                    │                      │                  │
      │◄───201 Created─────┤                     │                  │
      │  {agent_info,      │                     │                  │
      │   api_key: "xyz"}  │                     │                  │
      │  ⚠️ SAVE API KEY\!   │                     │                  │
```

#### 2. Task Delegation (Sync Mode)

```
User     Message Handler   Task Delegator   Capability Matcher   A2A Client   External Agent
  │            │                  │                 │                │              │
  ├─@k8s-op    │                  │                 │                │              │
  │ scale app  │                  │                 │                │              │
  ├────────────►                  │                 │                │              │
  │            │                  │                 │                │              │
  │            ├──delegate()──────►                 │                │              │
  │            │                  │                 │                │              │
  │            │                  ├─find_agents()───►                │              │
  │            │                  │                 │                │              │
  │            │                  │◄──[agents]──────┤                │              │
  │            │                  │                 │                │              │
  │            │                  ├──score_agents()─►                │              │
  │            │                  │  capability +   │                │              │
  │            │                  │  params         │                │              │
  │            │                  │                 │                │              │
  │            │                  │◄──ranked list───┤                │              │
  │            │                  │  (1.0, agent1)  │                │              │
  │            │                  │                 │                │              │
  │            │                  ├──create_jwt()───►                │              │
  │            │                  │                 ├─POST /delegate─►              │
  │            │                  │                 │  + JWT token   │              │
  │            │                  │                 │                │              │
  │            │                  │                 │                ◄──execute────┤
  │            │                  │                 │                │  kubectl...  │
  │            │                  │                 │                │              │
  │            │                  │                 │◄──200 OK───────┤              │
  │            │                  │                 │  {result}      │              │
  │            │                  │                 │                │              │
  │            │                  │◄──response──────┤                │              │
  │            │                  │                 │                │              │
  │            │◄──result─────────┤                 │                │              │
  │            │                  │                 │                │              │
  │◄──response─┤                  │                 │                │              │
  │ ✅ Scaled   │                  │                 │                │              │
```

#### 3. Task Delegation (Async Mode with Webhook)

```
User   Message Handler   Task Delegator   A2A Client   External Agent   Webhook Endpoint
  │           │                 │              │              │                │
  ├─@log-analyzer             │              │              │                │
  │  find errors (24h)         │              │              │                │
  ├────────────►               │              │              │                │
  │           │                │              │              │                │
  │           ├─delegate()─────►              │              │                │
  │           │  async=True    │              │              │                │
  │           │  callback_url  │              │              │                │
  │           │                ├─POST /delegate──────────────►                │
  │           │                │  async:true  │              │                │
  │           │                │  callback_url│              │                │
  │           │                │              │              │                │
  │           │                │              ├─queue task───┤                │
  │           │                │              │              │                │
  │           │                │◄──200 OK─────┤              │                │
  │           │                │  status:queued│             │                │
  │           │                │              │              │                │
  │           │◄──queued───────┤              │              │                │
  │           │                │              │              │                │
  │◄──response─┤                │              │              │                │
  │ ⏳ Queued   │                │              │              │                │
  │ (will notify)              │              │              │                │
  │           │                │              │              │                │
  │           │                │              │   [Background processing...]  │
  │           │                │              │              │                │
  │           │                │              ◄─POST /webhook─────────────────┤
  │           │                │              │              │  {task_id,     │
  │           │                │              │              │   status:done, │
  │           │                │              │              │   result}      │
  │           │                │              ├──update DB───►                │
  │           │                │              │              │                │
  │           │                ◄──notify user─┤              │                │
  │◄──notification             │              │              │                │
  │ ✅ Analysis complete\!       │              │              │                │
  │ Found 42 errors...         │              │              │                │
```

### A2A Security Model

#### Authentication Flow

```
1. Registration:
   External Agent              A2A API
        │                        │
        ├─POST /register─────────►
        │ {agent_id, ...}        │
        │                        ├─generate_api_key()
        │                        │  (32-byte hex)
        │                        │
        │                        ├─hash_api_key()
        │                        │  (SHA-256)
        │                        │
        │                        ├─store(hash)
        │                        │
        │◄─201 Created───────────┤
        │ {api_key: "plaintext"} │
        │ ⚠️ SAVE THIS\!           │

2. Task Delegation:
   Agent A                  A2A Auth                Agent B
        │                     │                       │
        ├─create_jwt()────────►                      │
        │  (agent_id, caps)   ├─sign with HS256──────►
        │                     │  exp: now + 1h       │
        │                     │                       │
        │◄─JWT token──────────┤                      │
        │                     │                       │
        ├─POST /delegate──────────────────────────────►
        │  Authorization:     │                       │
        │  Bearer <jwt>       │                       │
        │                     │                       │
        │                     │         ┌─────────────┤
        │                     │         │verify_jwt()  │
        │                     │         │• signature   │
        │                     │         │• expiry      │
        │                     │         │• capabilities│
        │                     │         └─────────────►
        │                     │                       │
        │                     │          ┌────────────┤
        │                     │          │execute task │
        │                     │          └────────────►
        │                     │                       │
        │◄──200 OK {result}────────────────────────────┤
```

#### Authorization Model (Capability-Based Access Control)

```yaml
# Agent capabilities define what it CAN DO
agent:
  capabilities:
    - name: "kubernetes.scale"
      parameters_schema:
        namespace: string
        deployment: string
        replicas: integer

# JWT token includes capability claims
jwt_payload:
  sub: "k8s-operator-agent"
  exp: 1706184000
  capabilities:
    - "kubernetes.scale"
    - "kubernetes.restart"

# Request validation checks:
# 1. Token signature valid?
# 2. Token not expired?
# 3. Requested capability in token claims?
# 4. Parameters match schema?
```

### A2A Capability Matching Algorithm

```python
def match_capability(
    agent_capabilities: list[Capability],
    requested_capability: str,
    parameters: dict
) -> float:
    """
    Returns score 0.0-1.0:
    - 1.0: Exact match + valid parameters
    - 0.8: Exact match, no schema validation
    - 0.6: Partial name match
    - 0.4: Tag match
    - 0.0: No match
    """
    for cap in agent_capabilities:
        if cap.name == requested_capability:
            if cap.parameters_schema:
                if validate_params(parameters, cap.parameters_schema):
                    return 1.0  # Perfect match
                else:
                    return 0.8  # Match but invalid params
            return 0.8  # Match, no schema

        if requested_capability in cap.name or cap.name in requested_capability:
            return 0.6  # Partial match

        if any(tag in requested_capability for tag in cap.tags):
            return 0.4  # Tag match

    return 0.0  # No match
```

### A2A Performance Characteristics

| Operation | Latency | Caching | Notes |
|---|---|---|---|
| **Agent Registration** | 50-100ms | No | One-time operation |
| **Agent Discovery** | <5ms (cached) | 5min TTL | Redis cache hit |
| **Agent Discovery** | 20-50ms (miss) | N/A | PostgreSQL query |
| **Capability Matching** | <1ms | In-memory | Scoring algorithm |
| **JWT Creation** | <1ms | No | In-memory signing |
| **JWT Verification** | <1ms | No | In-memory validation |
| **Sync Delegation** | 1-30s | No | Depends on agent task |
| **Async Delegation** | 50-200ms | No | Returns immediately |
| **Webhook Delivery** | 100-500ms | Retries 3x | Exponential backoff |

### A2A Failure Modes & Handling

#### 1. No Capable Agent Found

```
Error: A2ACapabilityNotFoundError
Reason: No agents registered with requested capability
Handling:
  - Return error to user with available capabilities
  - Suggest similar capabilities (fuzzy matching)
  - Log for admin review
```

#### 2. Task Timeout

```
Error: A2ATimeoutError
Reason: Agent did not respond within timeout window
Handling:
  - Sync mode: Return timeout error after 60s (default)
  - Async mode: Task remains "queued" in database
  - User can check status with /a2a status
  - Metrics: aiagent_a2a_task_duration_seconds
```

#### 3. Agent Authentication Failure

```
Error: A2AAuthenticationError
Reason: Invalid/expired JWT or missing capabilities
Handling:
  - Return 401 Unauthorized
  - Increment aiagent_a2a_auth_failures_total{reason="invalid_token"}
  - Agent must re-authenticate
```

#### 4. Webhook Delivery Failure

```
Error: A2AWebhookDeliveryError
Reason: Callback URL unreachable or rejected
Handling:
  - Retry 3 times with exponential backoff (1s, 2s, 4s)
  - Mark task as "completed" but log delivery failure
  - Increment aiagent_a2a_webhooks_sent_total{status="failure"}
  - Admin notification for repeated failures
```

### A2A Observability

#### Metrics

```prometheus
# Agent health
aiagent_a2a_agents_registered 4
aiagent_a2a_agents_online{agent_id="k8s-operator"} 1

# Task lifecycle
aiagent_a2a_tasks_delegated_total{to_agent="k8s-operator",capability="kubernetes.scale",status="completed"} 127
aiagent_a2a_tasks_received_total{from_agent="aiops-orchestrator",capability="logs.search"} 89
aiagent_a2a_task_duration_seconds{capability="kubernetes.scale",status="completed",quantile="0.95"} 2.5

# Authentication
aiagent_a2a_auth_failures_total{reason="invalid_token"} 3
aiagent_a2a_auth_failures_total{reason="missing_capability"} 1

# Webhooks
aiagent_a2a_webhooks_sent_total{status="success"} 89
aiagent_a2a_webhooks_received_total{task_status="completed"} 76
```

#### Health Endpoints

```bash
# GET /health/a2a
{
  "enabled": true,
  "registered_agents": 4,
  "online_agents": 3,
  "capabilities": [
    "kubernetes.scale",
    "kubernetes.restart",
    "logs.search",
    "database.query"
  ],
  "recent_delegations_24h": 127
}
```

### A2A Integration Points

The A2A layer integrates with existing AIOps components:

| Component | Integration | Purpose |
|---|---|---|
| **Message Handler** | `@agent` syntax detection | Natural language delegation from chat |
| **Message Handler** | `/a2a` commands | Agent discovery and status |
| **Metrics** | A2A-specific metrics | Monitor agent health and delegation |
| **Health Check** | `/health/a2a` endpoint | System status reporting |
| **PostgreSQL** | `agents`, `agent_tasks` tables | Persistence layer |
| **Redis** | Agent registry cache | Fast lookups (5min TTL) |

### A2A Extension Points

#### Adding New Agents

1. **External Agent Registration**:
   ```bash
   curl -X POST http://localhost:8000/api/a2a/register \
     -H "Content-Type: application/json" \
     -d '{
       "agent_id": "my-custom-agent",
       "name": "Custom Agent",
       "url": "https://my-agent.example.com",
       "capabilities": [
         {
           "name": "custom.action",
           "description": "Performs custom action",
           "parameters_schema": {...},
           "tags": ["custom"]
         }
       ],
       "version": "1.0.0"
     }'
   ```

2. **Auto-Registration** (config/agents.yml):
   ```yaml
   api_backends:
     - agent_id: "my-custom-agent"
       name: "Custom Agent"
       url: "${CUSTOM_AGENT_URL:-http://localhost:9000}"
       # ... rest of config
   ```

#### Building A2A-Compatible Agents

See [docs/a2a-integration.md](a2a-integration.md) for:
- Agent implementation guide
- REST API specification
- Authentication setup
- Capability definition best practices
- Example implementations

---

**Last Updated**: 2026-07-26  
**Version**: 1.0.0 (A2A Integration Added)
