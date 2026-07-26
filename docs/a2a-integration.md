# Agent-to-Agent (A2A) Integration

## Overview

The A2A (Agent-to-Agent) integration enables the AIOps Orchestrator to communicate and collaborate with other AI agents in a distributed multi-agent system. This allows for:

- **Task delegation** to specialized agents with specific capabilities
- **Dynamic capability discovery** via agent registry
- **Secure authentication** using JWT tokens and API keys
- **Sync and async execution** modes for delegated tasks
- **Webhook callbacks** for long-running async operations

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    AIOps Orchestrator                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐     ┌──────────────────┐              │
│  │  Agent Registry │────▶│  Capability       │              │
│  │  (PostgreSQL +  │     │  Matcher          │              │
│  │   Redis Cache)  │     └──────────────────┘              │
│  └─────────────────┘              │                          │
│           │                        │                          │
│           │                        ▼                          │
│           │             ┌──────────────────┐                 │
│           └────────────▶│ Task Delegator   │                 │
│                         └──────────────────┘                 │
│                                  │                            │
│                                  ▼                            │
│                         ┌──────────────────┐                 │
│                         │   A2A Client     │                 │
│                         │ (HTTP + JWT Auth)│                 │
│                         └──────────────────┘                 │
│                                  │                            │
└──────────────────────────────────┼────────────────────────────┘
                                   │
                                   │ HTTP POST /api/a2a/delegate
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
        ┌─────────────────────┐      ┌─────────────────────┐
        │  K8s Operator Agent │      │  Log Analyzer Agent │
        │                     │      │                     │
        │  Capabilities:      │      │  Capabilities:      │
        │  - k8s.scale        │      │  - logs.search      │
        │  - k8s.restart      │      │  - logs.patterns    │
        └─────────────────────┘      └─────────────────────┘
```

### Key Components

1. **Agent Registry** (`src/services/agent_registry.py`)
   - Central registry for all registered agents
   - PostgreSQL for persistence, Redis for caching
   - Tracks agent status (online/offline/degraded)
   - Capability-based discovery

2. **Task Delegator** (`src/services/task_delegator.py`)
   - Selects best agent for a given task
   - Manages sync vs async execution
   - Handles timeouts and retries

3. **Capability Matcher** (`src/services/capability_matcher.py`)
   - Scores agents based on capability match
   - Validates parameters against JSON Schema
   - Supports exact and partial matching

4. **A2A Client** (`src/services/a2a_client.py`)
   - HTTP client for agent-to-agent communication
   - Automatic retry with exponential backoff
   - Webhook delivery for async tasks

5. **A2A Authentication** (`src/services/a2a_auth.py`)
   - JWT token generation and validation
   - API key hashing and verification
   - Capability-based authorization

6. **A2A Endpoints** (`src/api/a2a_endpoints.py`)
   - REST API for agent registration
   - Task delegation endpoints
   - Webhook receiver for async callbacks

## Getting Started

### 1. Enable A2A Integration

In your environment or `config/.env`:

```bash
# Enable A2A integration
A2A_ENABLED=true

# Agent identification
A2A_AGENT_ID=aiops-orchestrator
A2A_AGENT_NAME="AIOps Orchestrator"

# JWT secret (use strong random value in production)
A2A_JWT_SECRET=your-very-secret-key-change-me

# Optional: Public webhook URL for async callbacks
A2A_WEBHOOK_URL=https://your-domain.com/api/a2a/webhook

# Token expiry (hours)
A2A_TOKEN_EXPIRY_HOURS=1
```

### 2. Configure Agents

Create `config/agents.yml`:

```yaml
agents:
  - agent_id: k8s-operator-agent
    name: Kubernetes Operations Agent
    url: ${K8S_OPERATOR_URL:-http://k8s-operator:8080}
    capabilities:
      - name: kubernetes.scale
        description: Scale Kubernetes deployments
        parameters_schema:
          type: object
          required: [namespace, deployment, replicas]
          properties:
            namespace:
              type: string
            deployment:
              type: string
            replicas:
              type: integer
              minimum: 0
        tags:
          - kubernetes
          - scaling

    api_key: ${K8S_OPERATOR_API_KEY}
    webhook_url: ${K8S_OPERATOR_WEBHOOK_URL}
    version: "1.0.0"
    metadata:
      environment: production
      owner: platform-team

settings:
  auto_register_on_startup: true
  health_check_enabled: true
  health_check_interval_seconds: 60
  stale_threshold_hours: 24
  default_task_timeout_seconds: 30
  max_concurrent_delegations: 10
```

### 3. Run Database Migration

```bash
# Apply A2A database schema
alembic upgrade head
```

This creates:
- `agents` table (agent registry)
- `agent_tasks` table (task delegation history)
- `agent_messages` table (communication audit trail)

### 4. Start the Orchestrator

```bash
python -m src.main
```

The orchestrator will:
1. Initialize the agent registry
2. Load and register agents from `config/agents.yml`
3. Start periodic health checks
4. Enable A2A endpoints at `/api/a2a/*`

## Agent Registration

### Option 1: Auto-register from config

Agents defined in `config/agents.yml` with `auto_register_on_startup: true` are registered automatically.

### Option 2: Dynamic registration via API

```bash
POST /api/a2a/register
Content-Type: application/json

{
  "agent_id": "custom-agent",
  "name": "Custom Agent",
  "url": "http://custom-agent:8080",
  "capabilities": [
    {
      "name": "custom.action",
      "description": "Perform custom action",
      "parameters_schema": {
        "type": "object",
        "required": ["param1"],
        "properties": {
          "param1": {"type": "string"}
        }
      },
      "tags": ["custom"]
    }
  ],
  "webhook_url": "http://custom-agent:8080/webhook",
  "version": "1.0.0",
  "metadata": {
    "owner": "custom-team"
  }
}
```

**Response:**

```json
{
  "agent_id": "custom-agent",
  "name": "Custom Agent",
  "url": "http://custom-agent:8080",
  "capabilities": [...],
  "status": "unknown",
  "api_key": "a1b2c3d4e5f6...",  // Only returned once!
  "version": "1.0.0",
  "registered_at": "2025-01-15T10:30:00Z",
  "last_seen": "2025-01-15T10:30:00Z"
}
```

⚠️ **Important**: Store the `api_key` securely. It won't be retrievable later.

## Task Delegation

### Synchronous Delegation

Waits for task completion before returning:

```python
from src.services.task_delegator import get_task_delegator

delegator = get_task_delegator()

# Delegate task and wait for result
result = await delegator.delegate(
    capability="kubernetes.scale",
    parameters={
        "namespace": "production",
        "deployment": "api-server",
        "replicas": 5
    },
    context={
        "incident_id": "inc-123",
        "severity": "high"
    },
    async_mode=False,  # Synchronous
    timeout_seconds=30
)

print(f"Task {result.task_id} status: {result.status}")
if result.status == "completed":
    print(f"Result: {result.result}")
```

### Asynchronous Delegation

Returns immediately, use webhooks for completion:

```python
# Delegate task asynchronously
response = await delegator.delegate(
    capability="logs.error_patterns",
    parameters={
        "service": "api-server",
        "time_range_hours": 24
    },
    async_mode=True,  # Asynchronous
    timeout_seconds=300  # Only for initial response
)

print(f"Task {response.task_id} queued, status: {response.status}")

# Later, check status
from src.services.a2a_client import get_a2a_client

client = get_a2a_client()
status = await client.get_task_status(
    agent_url="http://log-analyzer:8080",
    task_id=response.task_id
)

if status.status == "completed":
    print(f"Result: {status.result}")
```

### Webhook Callbacks

For async tasks, the executor agent sends a webhook when complete:

```json
POST /api/a2a/webhook
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
  "task_id": "task-abc-123",
  "status": "completed",
  "result": {
    "errors_found": 42,
    "patterns": ["ConnectionTimeout", "DatabaseError"]
  },
  "error": null,
  "started_at": "2025-01-15T10:30:05Z",
  "completed_at": "2025-01-15T10:32:15Z"
}
```

## Capability Discovery

### List All Agents

```bash
GET /api/a2a/agents
```

**Response:**

```json
[
  {
    "agent_id": "k8s-operator-agent",
    "name": "Kubernetes Operations Agent",
    "url": "http://k8s-operator:8080",
    "capabilities": [...],
    "status": "online",
    "version": "1.0.0",
    "last_seen": "2025-01-15T10:35:00Z"
  }
]
```

### Filter by Capability

```bash
GET /api/a2a/agents?capability=kubernetes.scale
```

### Find Best Agent for Task

```python
from src.services.agent_registry import get_agent_registry

registry = get_agent_registry()

# Find agents with specific capability
agents = await registry.find_agents_by_capability(
    capability="kubernetes.scale",
    db=db
)

# Agents are scored and sorted by match quality
best_agent = agents[0]
```

## Authentication

### JWT Tokens

Each request to another agent includes a JWT token:

```python
from src.services.a2a_auth import get_a2a_auth

auth = get_a2a_auth()

# Create token
token = auth.create_jwt_token(
    agent_id="aiops-orchestrator",
    capabilities=["kubernetes.scale"],
    metadata={"version": "1.0.0"}
)

# Verify token
payload = auth.verify_jwt_token(token)
agent_id = payload["sub"]
```

### API Keys

Agents authenticate with API keys (hashed in database):

```python
# Generate new API key
api_key = auth.generate_api_key()  # "a1b2c3d4e5f6..."

# Hash for storage
api_key_hash = auth.hash_api_key(api_key)

# Verify later
is_valid = auth.verify_api_key(api_key, api_key_hash)
```

## Observability

### Health Check

```bash
GET /health/a2a
```

**Response:**

```json
{
  "enabled": true,
  "registered_agents": 4,
  "online_agents": 3,
  "capabilities": [
    "kubernetes.scale",
    "kubernetes.restart",
    "database.query",
    "logs.search"
  ],
  "recent_delegations_24h": 127
}
```

### Prometheus Metrics

```prometheus
# Agent registry
aiagent_a2a_agents_registered 4
aiagent_a2a_agents_online 3

# Task delegation
aiagent_a2a_tasks_delegated_total{to_agent="k8s-operator",capability="kubernetes.scale",status="completed"} 45
aiagent_a2a_tasks_received_total{from_agent="aiops-orchestrator",capability="logs.search",status="completed"} 23

# Task duration
aiagent_a2a_task_duration_seconds{capability="kubernetes.scale",status="completed"} 2.5

# Webhooks
aiagent_a2a_webhooks_sent_total{status="success"} 67
aiagent_a2a_webhooks_received_total{task_status="completed"} 56

# Authentication
aiagent_a2a_auth_failures_total{reason="invalid_token"} 3

# Capabilities
aiagent_a2a_capability_requests_total{capability="kubernetes.scale",found="true"} 89
```

## Building an A2A-Compatible Agent

### Minimum Requirements

1. **Implement A2A endpoints:**
   - `POST /api/a2a/delegate` - Receive task delegations
   - `GET /api/a2a/tasks/{task_id}` - Return task status
   - `POST /api/a2a/webhook` - Optional, for receiving callbacks

2. **Authentication:**
   - Validate JWT tokens from the `Authorization: Bearer <token>` header
   - Return 401 if authentication fails

3. **Task execution:**
   - Parse `TaskDelegationRequest` from request body
   - Execute the requested capability with provided parameters
   - Return `TaskDelegationResponse` with `task_id` and initial status

4. **Async mode (optional):**
   - If `async_mode: true`, queue the task and return immediately
   - Send webhook to `callback_url` when complete

### Example Agent (Python)

```python
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

app = FastAPI()

class TaskDelegationRequest(BaseModel):
    capability: str
    parameters: dict
    context: dict = {}
    async_mode: bool = False
    callback_url: str | None = None

class TaskDelegationResponse(BaseModel):
    task_id: str
    status: str
    message: str = ""

@app.post("/api/a2a/delegate")
async def delegate_task(
    request: TaskDelegationRequest,
    authorization: str = Header(None)
):
    # Validate JWT token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization[7:]
    # ... verify token ...
    
    # Execute capability
    if request.capability == "my.capability":
        task_id = str(uuid.uuid4())
        
        # For sync mode, execute and return result
        if not request.async_mode:
            result = execute_capability(request.parameters)
            return TaskDelegationResponse(
                task_id=task_id,
                status="completed",
                message="Task completed successfully"
            )
        
        # For async mode, queue and callback later
        else:
            queue_task(task_id, request)
            return TaskDelegationResponse(
                task_id=task_id,
                status="queued",
                message="Task queued for execution"
            )
    
    raise HTTPException(status_code=404, detail=f"Capability {request.capability} not found")
```

## Security Best Practices

### 1. JWT Secret Management

```bash
# Generate strong random secret
openssl rand -hex 32

# Store in environment variables (NOT in code)
export A2A_JWT_SECRET="your-generated-secret"
```

### 2. API Key Storage

- **Never** store plaintext API keys in the database
- Use `A2AAuth.hash_api_key()` before storing
- Only return API keys once during registration

### 3. Token Expiry

- Keep token expiry short (1 hour default)
- Rotate tokens regularly
- Implement token refresh for long-lived sessions

### 4. Rate Limiting

The orchestrator already includes rate limiting (60 req/min per IP). Consider:

```python
# Per-agent rate limiting
from slowapi import Limiter

limiter = Limiter(key_func=lambda: request.headers.get("X-Agent-ID"))

@app.post("/api/a2a/delegate")
@limiter.limit("100/minute")
async def delegate_task(...):
    ...
```

### 5. Network Security

- Use HTTPS in production
- Whitelist agent IPs if possible
- Consider mutual TLS for agent-to-agent communication

## Troubleshooting

### Agent Not Registered

**Symptom**: `No agents found with capability: X`

**Solutions**:
1. Check `config/agents.yml` and ensure `auto_register_on_startup: true`
2. Verify agent URL is reachable
3. Check logs for registration errors

```bash
# List registered agents
curl http://localhost:8000/api/a2a/agents | jq
```

### Task Delegation Timeout

**Symptom**: `A2ATimeoutError: Task did not complete within 30s`

**Solutions**:
1. Increase timeout: `timeout_seconds=60`
2. Use async mode for long-running tasks
3. Check agent health

```bash
# Check agent health
curl http://k8s-operator:8080/health
```

### Authentication Failures

**Symptom**: `401 Unauthorized` or `Token has expired`

**Solutions**:
1. Verify JWT secret matches across agents
2. Check token expiry settings
3. Ensure clocks are synchronized (use NTP)

```python
# Debug token payload
from src.services.a2a_auth import get_a2a_auth

auth = get_a2a_auth()
payload = auth.verify_jwt_token(token)
print(payload)
```

### Capability Not Found

**Symptom**: `A2ACapabilityNotFoundError`

**Solutions**:
1. Check capability name is exact match
2. Verify agent capabilities in registry
3. Use partial matching if needed

```python
# Find available capabilities
registry = get_agent_registry()
agents = await registry.list_agents(db=db)
for agent in agents:
    print(f"{agent.agent_id}: {[c.name for c in agent.capabilities]}")
```

## Migration Guide

### From Manual Agent Calls to A2A

**Before:**

```python
# Manual HTTP call to specific agent
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://k8s-operator:8080/scale",
        json={"namespace": "prod", "deployment": "api", "replicas": 5}
    )
    result = response.json()
```

**After:**

```python
# A2A delegation (automatic agent selection)
from src.services.task_delegator import get_task_delegator

delegator = get_task_delegator()
result = await delegator.delegate(
    capability="kubernetes.scale",
    parameters={"namespace": "prod", "deployment": "api", "replicas": 5},
    async_mode=False
)
```

**Benefits:**
- Automatic agent discovery
- Capability-based routing
- Built-in retry and timeout
- Authentication handled automatically
- Metrics and observability

## API Reference

### Agent Registration

#### `POST /api/a2a/register`

Register a new agent.

**Request:**
```json
{
  "agent_id": "string",
  "name": "string",
  "url": "string",
  "capabilities": [AgentCapability],
  "webhook_url": "string?",
  "version": "string",
  "metadata": {}
}
```

**Response:** `201 Created`
```json
{
  ...AgentInfo,
  "api_key": "string"  // Only returned once
}
```

#### `GET /api/a2a/agents`

List all agents.

**Query Parameters:**
- `status`: Filter by status (online, offline, degraded, unknown)
- `capability`: Filter by capability name

**Response:** `200 OK`
```json
[AgentInfo]
```

#### `GET /api/a2a/agents/{agent_id}`

Get agent details.

**Response:** `200 OK`
```json
AgentInfo
```

#### `DELETE /api/a2a/agents/{agent_id}`

Deregister an agent (requires authentication).

**Response:** `204 No Content`

### Task Delegation

#### `POST /api/a2a/delegate`

Delegate a task to this orchestrator (receive from other agents).

**Request:**
```json
{
  "capability": "string",
  "parameters": {},
  "context": {},
  "async_mode": false,
  "callback_url": "string?",
  "timeout_seconds": 30,
  "priority": 5
}
```

**Response:** `200 OK`
```json
{
  "task_id": "string",
  "status": "queued|running|completed|failed",
  "message": "string"
}
```

#### `GET /api/a2a/tasks/{task_id}`

Get task status.

**Response:** `200 OK`
```json
{
  "task_id": "string",
  "status": "string",
  "result": {},
  "error": "string?",
  "created_at": "datetime",
  "started_at": "datetime?",
  "completed_at": "datetime?"
}
```

#### `POST /api/a2a/webhook`

Receive async task completion webhook.

**Request:**
```json
{
  "task_id": "string",
  "status": "completed|failed|timeout|cancelled",
  "result": {},
  "error": "string?",
  "completed_at": "datetime"
}
```

**Response:** `200 OK`
```json
{
  "status": "acknowledged",
  "task_id": "string"
}
```

## Examples

See `examples/` directory for:
- Simple Python agent implementation
- Docker Compose setup for multi-agent system
- Integration tests

## Changelog

### v1.0.0 (2025-01-15)

- Initial A2A integration
- Agent registry with PostgreSQL + Redis
- JWT authentication
- Sync and async task delegation
- Capability-based discovery
- Prometheus metrics
- Health checks
- Documentation

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup and guidelines.

## License

See [LICENSE](../LICENSE).
