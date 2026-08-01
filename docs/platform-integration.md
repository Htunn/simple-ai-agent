# Platform Integration

Integration of multi-cloud platform management into AIOps Orchestrator.

## Overview

The platform integration enables AI-powered management of virtual machines and infrastructure across multiple cloud platforms:

- **Nutanix Prism Central** - VM and cluster management
- **VMware vCenter** - VM and ESXi host management  
- **OpenShift** - Container platform resources (Projects, Routes, Builds)

## Components

### 1. Platform Clients (`src/platforms/`)

Unified interface for multi-cloud infrastructure management.

**Features:**
- Abstract base class (`BasePlatformClient`) defining common interface
- Platform-specific implementations (Nutanix, VMware, OpenShift)
- Unified resource models (VMResource, HostResource, PlatformHealth)
- Factory pattern for dynamic client creation
- Async/await support throughout
- Context manager support for automatic cleanup

See [src/platforms/README.md](../src/platforms/README.md) for detailed documentation.

### 2. Platform Registry (`src/services/platform_registry.py`)

Centralized management of platform configurations and clients.

**Capabilities:**
- Load platform configs from database
- Lazy client initialization (create on first use)
- Client caching and connection pooling
- Health monitoring and history tracking
- Operation audit logging
- Bulk health checks across all platforms

**Usage:**
```python
from src.services import get_platform_registry

# Get registry singleton
registry = await get_platform_registry()

# Get a platform client
client = await registry.get_client("production-nutanix")
vms = await client.list_vms()

# Check health of all platforms
health_results = await registry.check_all_health()

# List configured platforms
platforms = await registry.list_platforms()
```

### 3. Platform Watchloop (`src/monitoring/platform_watchloop.py`)

Background health monitoring for all configured platforms.

**Features:**
- Periodic health checks (configurable interval, default: 60s)
- Status change detection (healthy ↔ degraded ↔ unreachable)
- Response time monitoring with thresholds
- Event generation for degraded/unreachable platforms
- Automatic retry and exponential backoff

**Usage:**
```python
from src.monitoring import PlatformWatchLoop

async def handle_platform_event(event):
    print(f"Platform {event.platform_name}: {event.event_type}")

# Start watchloop
loop = PlatformWatchLoop(event_callback=handle_platform_event)
await loop.start()

# Check status
is_running = loop.is_running()
platform_states = loop.get_platform_states()

# Stop when done
await loop.stop()
```

### 4. Platform Handler (`src/services/platform_handler.py`)

Natural language command execution for platform operations.

**Capabilities:**
- Parse natural language commands
- Execute VM power operations (start, stop, restart)
- List VMs and hosts across all platforms
- Find resources by name or ID across platforms
- Audit logging for all operations

**Supported Commands:**
```
# VM Operations
"restart the production-api VM"
"start the database VM on nutanix"
"stop VM vm-123"
"power off staging-web force"

# Queries
"list all VMs"
"show VMs in production cluster"
"list hosts on vmware"
"show VM status"
```

**Usage:**
```python
from src.services import PlatformHandler

handler = PlatformHandler()

# Execute command
result = await handler.execute_command(
    "restart the production-api VM",
    user_id=user_id
)

if result["success"]:
    print(f"Operation: {result['operation']}")
    print(f"Platform: {result['platform']}")
    print(f"VM: {result['vm_name']}")
```

### 5. Message Handler Integration

Platform commands are automatically detected and routed from chat messages.

**Detection:**
- Checks for platform keywords (vm, nutanix, vmware, etc.)
- Requires action verbs (start, stop, list, etc.)
- Seamlessly integrates with existing Kubernetes command handling

**Flow:**
```
User: "list all VMs"
  ↓
MessageHandler._is_platform_query() → True
  ↓
MessageHandler._handle_platform_query()
  ↓
PlatformHandler.execute_command()
  ↓
PlatformRegistry.get_client()
  ↓
NutanixClient.list_vms() / VMwareClient.list_vms()
  ↓
Formatted response sent to chat
```

## Database Schema

### platform_configs

Stores platform connection configurations.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | String | Unique platform name |
| platform_type | String | nutanix, vmware, openshift |
| endpoint | String | API endpoint URL |
| username | String | Username for Basic Auth |
| password_encrypted | Text | Encrypted password |
| token | Text | Bearer token (alternative to user/pass) |
| verify_ssl | Boolean | SSL certificate verification |
| timeout | Integer | Request timeout (seconds) |
| max_retries | Integer | Max retry attempts |
| enabled | Boolean | Platform enabled flag |
| extra_config | JSON | Platform-specific config |
| created_at | Timestamp | Creation time |
| updated_at | Timestamp | Last update time |
| last_health_check | Timestamp | Last health check time |
| health_status | String | healthy, degraded, unreachable |

### platform_health_history

Historical health check data.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| platform_id | UUID | Foreign key to platform_configs |
| status | String | healthy, degraded, unreachable |
| response_time_ms | Float | Response time in milliseconds |
| message | Text | Status message |
| checked_at | Timestamp | Check timestamp |

### platform_operations

Audit log for platform operations.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| platform_id | UUID | Foreign key to platform_configs |
| operation_type | String | list_vms, start_vm, stop_vm, etc. |
| resource_type | String | vm, host, cluster |
| resource_id | String | Platform-specific resource ID |
| resource_name | String | Human-readable resource name |
| initiator | String | system, user, ai_agent |
| user_id | UUID | User who initiated operation |
| status | String | pending, executing, completed, failed |
| started_at | Timestamp | Operation start time |
| completed_at | Timestamp | Operation completion time |
| result | JSON | Operation result data |
| error_message | Text | Error message if failed |

## Setup

### 1. Run Database Migration

```bash
# Apply platform tables migration
alembic upgrade head
```

### 2. Configure Platforms

Add platform configurations to the database:

```sql
-- Nutanix Prism Central
INSERT INTO platform_configs (
    id, name, platform_type, endpoint, username, password_encrypted, 
    verify_ssl, enabled
) VALUES (
    gen_random_uuid(),
    'production-nutanix',
    'nutanix',
    'https://prism-central.example.com:9440',
    'admin',
    'encrypted_password_here',  -- Use proper encryption in production
    true,
    true
);

-- VMware vCenter
INSERT INTO platform_configs (
    id, name, platform_type, endpoint, username, password_encrypted,
    verify_ssl, enabled
) VALUES (
    gen_random_uuid(),
    'production-vmware',
    'vmware',
    'https://vcenter.example.com',
    'administrator@vsphere.local',
    'encrypted_password_here',
    true,
    true
);

-- OpenShift
INSERT INTO platform_configs (
    id, name, platform_type, endpoint, token,
    verify_ssl, enabled
) VALUES (
    gen_random_uuid(),
    'production-openshift',
    'openshift',
    'https://api.openshift.example.com:6443',
    'sha256~your-token-here',
    true,
    true
);
```

### 3. Start Platform Watchloop

Add to your main.py startup:

```python
from src.monitoring import PlatformWatchLoop

# Initialize watchloop
platform_watchloop = PlatformWatchLoop(
    event_callback=handle_platform_event,
    interval=60  # Check every 60 seconds
)

await platform_watchloop.start()
```

## Testing

### Mock Server Testing

Test against mock servers without real infrastructure:

```bash
# Start mock servers
./scripts/mock_servers.sh start

# Configure mock platforms in database
INSERT INTO platform_configs (
    id, name, platform_type, endpoint, username, password_encrypted,
    verify_ssl, enabled
) VALUES (
    gen_random_uuid(),
    'mock-nutanix',
    'nutanix',
    'http://localhost:5001',
    'admin',
    'password',
    false,  -- No SSL for mocks
    true
);

# Test platform operations
pytest tests/unit/test_platform_clients.py -v
```

### Chat Command Testing

Test via Slack or other channels:

```
User: "list all VMs"
Bot: 🖥️ **Virtual Machines**
     **Summary:** 12 total (10 running, 2 stopped)
     **Platforms:** production-nutanix, production-vmware
     ...

User: "restart the production-api VM"
Bot: ✅ **VM 'production-api' restarted successfully on production-nutanix**
     **Platform:** production-nutanix
     **VM:** production-api
     **Operation:** Restart Vm

User: "show hosts on vmware"
Bot: 🖥️ **Hosts/Nodes**
     **Summary:** 6 total (6 healthy, 0 unhealthy)
     **Platforms:** production-vmware
     ...
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Chat Interface                          │
│                  (Slack, Telegram, etc.)                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Message Handler                           │
│  • Detects platform keywords                                │
│  • Routes to platform handler                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Platform Handler                           │
│  • Parses natural language commands                         │
│  • Executes operations via registry                         │
│  • Formats responses                                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                 Platform Registry                           │
│  • Loads configs from database                              │
│  • Creates and caches clients                               │
│  • Logs operations                                          │
└───────────────────────┬─────────────────────────────────────┘
                        │
            ┌───────────┴───────────┬───────────┐
            ▼                       ▼           ▼
    ┌──────────────┐      ┌──────────────┐   ┌──────────────┐
    │   Nutanix    │      │   VMware     │   │  OpenShift   │
    │    Client    │      │    Client    │   │    Client    │
    └──────┬───────┘      └──────┬───────┘   └──────�┬───────┘
           │                     │                    │
           ▼                     ▼                    ▼
    ┌──────────────┐      ┌──────────────┐   ┌──────────────┐
    │   Prism      │      │   vCenter    │   │  OpenShift   │
    │   Central    │      │   REST API   │   │     API      │
    └──────────────┘      └──────────────┘   └──────────────┘

Parallel: Platform Watchloop
    ↓ (every 60s)
┌─────────────────────────────────────────────────────────────┐
│              Platform Health Monitoring                     │
│  • Check all platforms                                      │
│  • Detect status changes                                    │
│  • Generate events                                          │
│  • Store health history                                     │
└─────────────────────────────────────────────────────────────┘
```

## Security Considerations

### 1. Password Encryption

**Current:** Passwords stored in `password_encrypted` field (placeholder)

**Production:** Use a secrets manager:
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Kubernetes Secrets with encryption at rest

### 2. Token Storage

**Current:** Tokens stored in database (plain text)

**Production:**
- Encrypt tokens before storage
- Rotate tokens regularly
- Use short-lived tokens when possible

### 3. SSL/TLS Verification

**Default:** `verify_ssl=True` for all platforms

**Development:** Can disable for mock servers (`verify_ssl=False`)

**Production:** Always enable SSL verification

### 4. Audit Logging

All operations logged to `platform_operations` table:
- Who initiated the operation (user_id)
- What was done (operation_type, resource_name)
- When it happened (started_at, completed_at)
- Result (success/failure, error_message)

## Monitoring

### Health Metrics

Track platform health over time:

```python
# Get health history
from src.database import get_db_session
from src.database.models import PlatformHealthHistory

async with get_db_session() as session:
    # Query last 24 hours of health data
    history = await session.execute(
        select(PlatformHealthHistory)
        .where(PlatformHealthHistory.checked_at >= datetime.now() - timedelta(days=1))
        .order_by(PlatformHealthHistory.checked_at.desc())
    )
```

### Response Time Tracking

Monitor API response times:
- **Warning threshold:** 2000ms
- **Critical threshold:** 5000ms

Events generated when thresholds exceeded.

### Operation Metrics

Track operations by:
- Platform
- Operation type
- Initiator (system/user/ai_agent)
- Success/failure rate

## Future Enhancements

### Planned Features

1. **Additional Platforms**
   - AWS EC2
   - Azure VMs
   - GCP Compute Engine
   - Bare metal (IPMI/Redfish)

2. **Advanced Operations**
   - VM cloning
   - Snapshot management
   - Resource scaling
   - Migration between hosts

3. **MCP Integration**
   - Expose platform operations as MCP tools
   - Enable AI agents to manage infrastructure
   - Tool schemas for LLM function calling

4. **Approval Workflow**
   - Require approval for destructive operations
   - Integration with existing approval_manager
   - Customizable approval rules per platform

5. **Cost Tracking**
   - Track resource usage
   - Cost attribution by team/project
   - Budget alerts and recommendations

## Troubleshooting

### Platform Connection Issues

```python
# Check platform health
registry = await get_platform_registry()
health = await registry.check_health("production-nutanix")

if health.status != "healthy":
    print(f"Platform unhealthy: {health.message}")
    print(f"Response time: {health.response_time_ms}ms")
```

### Client Initialization Failures

```python
# Enable debug logging
import logging
logging.getLogger("src.platforms").setLevel(logging.DEBUG)

# Try to create client
try:
    client = await registry.get_client("production-nutanix")
except ConnectionError as e:
    print(f"Connection error: {e}")
except ValueError as e:
    print(f"Configuration error: {e}")
```

### Operation Audit Trail

```python
# Query recent operations
from src.database.models import PlatformOperation

async with get_db_session() as session:
    ops = await session.execute(
        select(PlatformOperation)
        .where(PlatformOperation.status == "failed")
        .order_by(PlatformOperation.started_at.desc())
        .limit(10)
    )
    
    for op in ops.scalars():
        print(f"Failed: {op.operation_type} on {op.resource_name}")
        print(f"Error: {op.error_message}")
```

## Contributing

When adding new platform integrations:

1. Implement `BasePlatformClient` abstract interface
2. Add platform type to `PlatformType` enum
3. Register in `PlatformFactory._registry`
4. Add unit tests using mock servers
5. Update documentation with platform-specific examples
6. Add platform keywords to `PLATFORM_KEYWORDS` in message_handler.py

See [src/platforms/README.md](../src/platforms/README.md) for detailed API documentation.
