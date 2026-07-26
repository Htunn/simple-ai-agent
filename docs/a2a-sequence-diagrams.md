# A2A Integration - Sequence Diagrams

This document contains sequence diagrams illustrating the key flows in the Agent-to-Agent (A2A) integration.

## Table of Contents

- [Agent Registration Flow](#agent-registration-flow)
- [Synchronous Task Delegation](#synchronous-task-delegation)
- [Asynchronous Task Delegation with Webhook](#asynchronous-task-delegation-with-webhook)
- [Natural Language Delegation from Chat](#natural-language-delegation-from-chat)
- [Agent Discovery by Capability](#agent-discovery-by-capability)
- [Authentication Flow](#authentication-flow)
- [Multi-Agent Task Chain](#multi-agent-task-chain)

---

## Agent Registration Flow

This diagram shows how an external agent registers itself with the AIOps Orchestrator.

```mermaid
sequenceDiagram
    participant Agent as External Agent
    participant API as A2A API Endpoint
    participant Auth as A2A Auth Service
    participant Registry as Agent Registry
    participant DB as PostgreSQL
    participant Cache as Redis

    Agent->>API: POST /api/a2a/register
    Note over Agent,API: {agent_id, name, url,<br/>capabilities[], version}
    
    API->>Auth: generate_api_key()
    Auth-->>API: api_key (plaintext)
    
    API->>Auth: hash_api_key(api_key)
    Auth-->>API: api_key_hash
    
    API->>Registry: register_agent(...)
    Registry->>DB: INSERT INTO agents
    DB-->>Registry: agent record
    
    Registry->>Cache: SET agent:{agent_id}
    Note over Registry,Cache: TTL: 5 minutes
    Cache-->>Registry: OK
    
    Registry-->>API: AgentInfo + api_key
    API-->>Agent: 201 Created
    Note over Agent,API: {agent_info,<br/> api_key: "abc123..."}<br/>⚠️ Save API key!
```

**Key Points:**
- API key is returned **only once** during registration
- API key is hashed (SHA-256) before storage
- Agent info is cached in Redis with 5-minute TTL
- PostgreSQL provides persistence; Redis provides fast lookups

---

## Synchronous Task Delegation

This diagram shows the complete sync delegation flow where the orchestrator waits for task completion.

```mermaid
sequenceDiagram
    participant User as User (Chat)
    participant Handler as Message Handler
    participant Delegator as Task Delegator
    participant Matcher as Capability Matcher
    participant Registry as Agent Registry
    participant Client as A2A Client
    participant Agent as Target Agent
    participant DB as PostgreSQL

    User->>Handler: @kubernetes.scale: namespace=prod, deployment=api, replicas=5
    Handler->>Delegator: delegate(capability, params, async_mode=False)
    
    Delegator->>Registry: find_agents_by_capability("kubernetes.scale")
    Registry-->>Delegator: [agent1, agent2, agent3]
    
    Delegator->>Matcher: match_capability(agents, capability, params)
    Matcher-->>Delegator: scored_agents [(1.0, agent1), (0.8, agent2)]
    
    Delegator->>Delegator: Select best agent (score=1.0)
    
    Delegator->>Client: delegate_task(agent_url, request, api_key)
    Client->>Client: Create JWT token
    
    Client->>Agent: POST /api/a2a/delegate
    Note over Client,Agent: Authorization: Bearer <jwt><br/>{capability, parameters,<br/>async_mode: false}
    
    Agent->>Agent: Execute task
    Note over Agent: kubectl scale deployment<br/>api --replicas=5 -n prod
    
    Agent-->>Client: 200 OK {task_id, status: "completed", result}
    Client-->>Delegator: TaskDelegationResponse
    
    Delegator->>DB: INSERT INTO agent_tasks
    DB-->>Delegator: task record
    
    Delegator-->>Handler: TaskStatusResponse (completed)
    Handler-->>User: ✅ Task completed successfully<br/>Result: {scaled: "api", replicas: 5}
```

**Key Points:**
- Synchronous mode blocks until task completes or times out
- Capability matcher scores agents (1.0 = perfect match)
- JWT token created per request for authentication
- Full audit trail stored in `agent_tasks` table

---

## Asynchronous Task Delegation with Webhook

This diagram shows async delegation where the task runs in the background and notifies via webhook when complete.

```mermaid
sequenceDiagram
    participant User as User (Chat)
    participant Handler as Message Handler
    participant Delegator as Task Delegator
    participant Client as A2A Client
    participant Agent as Target Agent
    participant Webhook as Webhook Endpoint
    participant DB as PostgreSQL

    User->>Handler: @log-analyzer find errors in api-service (last 24h)
    Handler->>Delegator: delegate(capability, params, async_mode=True)
    
    Delegator->>Client: delegate_task(agent_url, request, api_key)
    Note over Client: async_mode: true<br/>callback_url: /api/a2a/webhook
    
    Client->>Agent: POST /api/a2a/delegate
    Note over Client,Agent: {capability: "logs.search",<br/>async_mode: true,<br/>callback_url: "https://..."}
    
    Agent->>Agent: Queue task
    Agent-->>Client: 200 OK {task_id, status: "queued"}
    
    Client-->>Delegator: TaskDelegationResponse (queued)
    Delegator->>DB: INSERT INTO agent_tasks (status: queued)
    
    Delegator-->>Handler: TaskDelegationResponse
    Handler-->>User: ⏳ Task queued (ID: abc-123)<br/>You'll be notified when complete
    
    Note over Agent: Task executes in background<br/>(analyzing 24h of logs...)
    
    Agent->>Agent: Task completes
    Agent->>Webhook: POST /api/a2a/webhook
    Note over Agent,Webhook: {task_id, status: "completed",<br/>result: {errors_found: 42,<br/>patterns: [...]}}
    
    Webhook->>DB: UPDATE agent_tasks SET status='completed'
    DB-->>Webhook: OK
    
    Webhook-->>Agent: 200 OK {acknowledged}
    
    Webhook->>Handler: send_message(user_id, result)
    Handler-->>User: ✅ Log analysis complete!<br/>Found 42 errors in 24h<br/>Patterns: ConnectionTimeout,<br/>DatabaseError
```

**Key Points:**
- Async mode returns immediately after queuing
- Agent calls webhook when task completes
- User receives notification in chat with results
- Supports long-running tasks (minutes to hours)

---

## Natural Language Delegation from Chat

This diagram shows the NLP extraction flow when users use natural language instead of structured syntax.

```mermaid
sequenceDiagram
    participant User as User (Chat)
    participant Handler as Message Handler
    participant AI as AI Router
    participant Delegator as Task Delegator
    participant Agent as Target Agent

    User->>Handler: @k8s-operator scale my-app to 3 replicas in production
    Note over User,Handler: Natural language request
    
    Handler->>Handler: Parse @k8s-operator
    Handler->>Handler: Extract: "scale my-app to 3 replicas in production"
    
    Handler->>AI: Extract capability and parameters
    Note over Handler,AI: Prompt: "Extract capability<br/>and parameters from:<br/>'scale my-app to 3 replicas<br/>in production'"
    
    AI-->>Handler: {capability: "kubernetes.scale",<br/>parameters: {namespace: "production",<br/>deployment: "my-app", replicas: 3}}
    
    Handler->>Delegator: delegate(capability, parameters)
    
    Delegator->>Agent: Execute task
    Note over Delegator,Agent: Same flow as sync delegation
    
    Agent-->>Delegator: Result
    Delegator-->>Handler: TaskStatusResponse
    
    Handler-->>User: ✅ Scaled my-app to 3 replicas<br/>in production namespace
```

**Key Points:**
- Users can use natural language instead of structured syntax
- AI (Gemini 2.0 Flash) extracts capability and parameters
- Falls back to structured format on extraction failure
- Provides better UX for non-technical users

---

## Agent Discovery by Capability

This diagram shows how the system discovers and ranks agents based on capability requirements.

```mermaid
sequenceDiagram
    participant User as CLI / API
    participant Registry as Agent Registry
    participant Matcher as Capability Matcher
    participant Cache as Redis
    participant DB as PostgreSQL

    User->>Registry: find_agents_by_capability("kubernetes.scale")
    
    Registry->>Cache: GET agents:by_capability:kubernetes.scale
    Cache-->>Registry: MISS
    
    Registry->>DB: SELECT * FROM agents WHERE capabilities @> 'kubernetes.scale'
    Note over Registry,DB: JSONB contains operator
    DB-->>Registry: [agent1, agent2, agent3]
    
    loop For each agent
        Registry->>Matcher: match_capability(agent.capabilities, "kubernetes.scale", params)
        
        alt Exact capability match
            Matcher->>Matcher: Validate params against JSON Schema
            alt Schema valid
                Matcher-->>Registry: score = 1.0 (perfect)
            else Schema invalid
                Matcher-->>Registry: score = 0.8 (match, bad params)
            end
        else Partial name match
            Matcher-->>Registry: score = 0.6
        else Tag match
            Matcher-->>Registry: score = 0.4
        else No match
            Matcher-->>Registry: score = 0.0
        end
    end
    
    Registry->>Registry: Sort by score (descending)
    Registry->>Cache: SET agents:by_capability:kubernetes.scale
    Note over Registry,Cache: TTL: 5 minutes
    
    Registry-->>User: Ranked agents<br/>[(1.0, agent1), (0.8, agent2), (0.6, agent3)]
```

**Key Points:**
- JSONB queries in PostgreSQL for capability filtering
- Scoring algorithm: 1.0 (perfect) → 0.8 → 0.6 → 0.4 → 0.0
- Results cached in Redis for 5 minutes
- JSON Schema validation for parameter checking

---

## Authentication Flow

This diagram shows the JWT authentication flow for agent-to-agent requests.

```mermaid
sequenceDiagram
    participant Agent1 as Agent A (Caller)
    participant Auth as A2A Auth Service
    participant API as A2A API
    participant Agent2 as Agent B (Target)

    Note over Agent1: Has API key from registration
    
    Agent1->>Auth: create_jwt_token(agent_id, capabilities)
    Auth->>Auth: Generate JWT
    Note over Auth: Payload: {sub: agent_id,<br/>exp: now + 1h,<br/>capabilities: [...]}<br/>Sign with HS256
    Auth-->>Agent1: JWT token
    
    Agent1->>Agent2: POST /api/a2a/delegate
    Note over Agent1,Agent2: Authorization: Bearer <jwt>
    
    Agent2->>Auth: validate_request(authorization_header, required_caps)
    
    Auth->>Auth: Extract token from header
    
    alt Token valid
        Auth->>Auth: Verify signature & expiry
        Auth->>Auth: Extract agent_id from subject
        Auth->>Auth: Check required capabilities
        
        alt Capabilities sufficient
            Auth-->>Agent2: agent_id (validated)
            Agent2->>Agent2: Execute task
            Agent2-->>Agent1: 200 OK {result}
        else Missing capabilities
            Auth-->>Agent2: A2AAuthenticationError
            Agent2-->>Agent1: 401 Unauthorized<br/>"Missing required capabilities"
        end
    else Token invalid/expired
        Auth-->>Agent2: A2AAuthenticationError
        Agent2-->>Agent1: 401 Unauthorized<br/>"Invalid or expired token"
    end
```

**Key Points:**
- JWT tokens expire after 1 hour (configurable)
- Tokens include capability claims for authorization
- HS256 algorithm (symmetric signing)
- Capability-based access control (CBAC)

---

## Multi-Agent Task Chain

This diagram shows how multiple agents can be chained together for complex workflows.

```mermaid
sequenceDiagram
    participant User as User
    participant Orchestrator as AIOps Orchestrator
    participant LogAgent as Log Analyzer Agent
    participant K8sAgent as K8s Operator Agent
    participant NotifyAgent as Notification Agent

    User->>Orchestrator: "Investigate and fix high error rate in production"
    
    Note over Orchestrator: Complex workflow requires<br/>multiple agent capabilities
    
    Orchestrator->>LogAgent: @logs.error_patterns: service=api, time_range=24h
    LogAgent->>LogAgent: Analyze logs
    LogAgent-->>Orchestrator: {patterns: ["ConnectionTimeout", "DatabaseError"],<br/>affected_pods: ["api-abc", "api-xyz"]}
    
    Orchestrator->>Orchestrator: RCA: Database connection pool exhausted
    
    Orchestrator->>K8sAgent: @kubernetes.scale: namespace=prod,<br/>deployment=api, replicas=10
    Note over Orchestrator,K8sAgent: Scale up to handle load
    K8sAgent->>K8sAgent: kubectl scale
    K8sAgent-->>Orchestrator: {scaled: true, new_replicas: 10}
    
    Orchestrator->>NotifyAgent: @notify.send: channel=slack,<br/>message="Scaled API to 10 replicas..."
    NotifyAgent->>NotifyAgent: Send Slack message
    NotifyAgent-->>Orchestrator: {sent: true, channel: "incidents"}
    
    Orchestrator-->>User: ✅ Issue resolved:<br/>1. Analyzed logs (2 error patterns)<br/>2. Scaled API from 5→10 replicas<br/>3. Notified #incidents channel
```

**Key Points:**
- Orchestrator chains multiple agent calls
- Each agent specializes in one capability
- Results from one agent feed into next step
- Full workflow automation with human oversight

---

## Complete System Flow with All Components

This comprehensive diagram shows how all A2A components work together in the AIOps Orchestrator.

```mermaid
graph TB
    %% User Interaction
    User[👤 User via Chat] -->|@agent or /a2a| MH[Message Handler]
    
    %% Message Handler Decision
    MH -->|Command| CMD{Command Type?}
    CMD -->|/a2a agents| AREG[Agent Registry]
    CMD -->|/a2a status| HEALTH[Health Check API]
    CMD -->|@delegation| DEL[Task Delegator]
    
    %% Agent Registry Flow
    AREG -->|Query| DB[(PostgreSQL)]
    AREG -->|Cache| Redis[(Redis)]
    DB -->|Agent List| AREG
    Redis -->|Cached Data| AREG
    AREG -->|Response| User
    
    %% Health Check Flow
    HEALTH -->|Status Query| REG2[Agent Registry]
    REG2 -->|Stats| HEALTH
    HEALTH -->|Response| User
    
    %% Delegation Flow
    DEL -->|Find Agents| REG3[Agent Registry]
    REG3 -->|Candidates| MATCH[Capability Matcher]
    MATCH -->|Scored Agents| DEL
    DEL -->|Best Match| CLIENT[A2A Client]
    
    %% Authentication
    CLIENT -->|Generate Token| AUTH[A2A Auth]
    AUTH -->|JWT| CLIENT
    
    %% External Agent Communication
    CLIENT -->|HTTP + JWT| AGENT[🤖 External Agent]
    AGENT -->|Result| CLIENT
    CLIENT -->|Response| DEL
    
    %% Audit & Notification
    DEL -->|Log Task| DB
    DEL -->|Update Metrics| PROM[Prometheus]
    DEL -->|Result| MH
    MH -->|Formatted Response| User
    
    %% Async Flow (Webhook)
    AGENT -.->|Webhook Callback| WEBHOOK[Webhook Endpoint]
    WEBHOOK -->|Update Status| DB
    WEBHOOK -->|Notify User| MH
    
    %% Monitoring
    PROM -->|Scrape| METRICS[/metrics Endpoint]
    METRICS -->|Expose| PROM
    PROM -->|Visualize| GRAFANA[📊 Grafana]
    
    style User fill:#e1f5ff
    style AGENT fill:#ffe1e1
    style DB fill:#fff4e1
    style Redis fill:#ffe1f5
    style PROM fill:#e1ffe1
    style GRAFANA fill:#e1ffe1
```

**Component Responsibilities:**

| Component | Responsibility |
|---|---|
| **Message Handler** | Routes @mentions and /a2a commands |
| **Task Delegator** | Orchestrates task delegation lifecycle |
| **Agent Registry** | Manages agent registration and discovery |
| **Capability Matcher** | Scores agents by capability match |
| **A2A Client** | HTTP communication with external agents |
| **A2A Auth** | JWT generation and validation |
| **Webhook Endpoint** | Receives async task completion callbacks |
| **PostgreSQL** | Persists agents, tasks, audit trail |
| **Redis** | Caches agent info (5min TTL) |
| **Prometheus** | Collects A2A metrics |

---

## Usage Examples

### Example 1: Natural Language Delegation

```
User: @k8s-operator restart the api-server pods in production

Flow:
1. Message Handler detects @ prefix
2. AI extracts: capability="kubernetes.restart", params={namespace: "production", deployment: "api-server"}
3. Task Delegator finds k8s-operator-agent (score: 1.0)
4. A2A Client sends request with JWT
5. Agent executes: kubectl rollout restart deployment api-server -n production
6. User receives: "✅ Restarted api-server pods in production"
```

### Example 2: Structured Delegation

```
User: @database.query: database=analytics, query="SELECT COUNT(*) FROM errors WHERE created_at > NOW() - INTERVAL '1 hour'"

Flow:
1. Message Handler parses structured format
2. Capability: "database.query"
3. Parameters: {database: "analytics", query: "SELECT..."}
4. Delegator finds db-ops-agent
5. Agent executes query
6. User receives: "✅ Query result: 1,247 errors in last hour"
```

### Example 3: List Available Agents

```
User: /a2a agents kubernetes

Response:
🤖 Registered Agents (2 total)

🟢 **K8s Operator Agent** (`k8s-operator-agent`)
   • Capabilities: kubernetes.scale, kubernetes.restart, kubernetes.describe
   • Status: online

🟡 **K8s Monitor Agent** (`k8s-monitor-agent`)
   • Capabilities: kubernetes.health, kubernetes.events
   • Status: degraded
```

---

## Metrics & Observability

All A2A operations emit Prometheus metrics for monitoring:

```prometheus
# Agent registration
aiagent_a2a_agents_registered 4
aiagent_a2a_agents_online 3

# Task delegation
aiagent_a2a_tasks_delegated_total{to_agent="k8s-operator",capability="kubernetes.scale",status="completed"} 127
aiagent_a2a_task_duration_seconds{capability="kubernetes.scale",status="completed"} 2.5

# Authentication
aiagent_a2a_auth_failures_total{reason="invalid_token"} 3

# Webhooks
aiagent_a2a_webhooks_sent_total{status="success"} 89
aiagent_a2a_webhooks_received_total{task_status="completed"} 76
```

---

## Error Handling

### Scenario: No Capable Agent Found

```mermaid
sequenceDiagram
    participant User
    participant Delegator as Task Delegator
    participant Registry as Agent Registry

    User->>Delegator: @notification.sms: phone="+1234", message="Alert"
    Delegator->>Registry: find_agents_by_capability("notification.sms")
    Registry-->>Delegator: [] (empty list)
    
    Delegator-->>User: ❌ A2ACapabilityNotFoundError<br/>"No agents found with capability: notification.sms"<br/><br/>Available capabilities:<br/>• kubernetes.scale<br/>• database.query<br/>• logs.search
```

### Scenario: Task Timeout

```mermaid
sequenceDiagram
    participant User
    participant Delegator
    participant Agent

    User->>Delegator: @complex.analysis: dataset=huge (timeout=30s)
    Delegator->>Agent: Execute task
    
    Note over Delegator,Agent: 30 seconds pass...
    
    Delegator->>Delegator: Timeout reached
    Delegator-->>User: ❌ A2ATimeoutError<br/>"Task did not complete within 30s"<br/><br/>Try:<br/>• Increase timeout: timeout_seconds=120<br/>• Use async mode for long tasks
```

---

## Best Practices

1. **Use Async for Long Tasks**: Tasks >30s should use `async_mode=True`
2. **Provide Webhook URL**: Set `A2A_WEBHOOK_URL` for async callbacks
3. **Monitor Metrics**: Alert on `aiagent_a2a_auth_failures_total`
4. **Cache Busting**: Redis TTL is 5 minutes; manual flush if needed
5. **Capability Naming**: Use dot notation: `domain.action` (e.g., `kubernetes.scale`)
6. **JSON Schema**: Always provide `parameters_schema` for validation
7. **Error Handling**: Implement retries for `A2ATimeoutError`

---

## Related Documentation

- [A2A Integration Guide](a2a-integration.md) - Complete setup and API reference
- [Architecture Overview](architecture.md) - System design and component interactions
- [API Reference](../README.md#api-reference) - All REST endpoints
- [Deployment Checklist](../DEPLOYMENT_CHECKLIST.md) - Production deployment steps

---

**Last Updated**: 2026-07-26  
**Version**: 1.0.0
