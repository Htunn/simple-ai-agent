# MCP Registry

## Overview

The MCP (Model Context Protocol) Registry is an extensible tool management system that allows the AI agent to discover, register, and execute tools from various sources including native implementations, MCP servers, and external APIs.

## Architecture

```
┌─────────────────────────────────────────────────┐
│            Message Handler                      │
│  (Detects K8s queries, routes to handlers)     │
└────────────────┬────────────────────────────────┘
                 │
         ┌───────▼────────┐
         │  MCP Registry  │
         │  - Tool Index  │
         │  - Categories  │
         │  - Metadata    │
         └───────┬────────┘
                 │
     ┌───────────┴───────────┐
     │                       │
┌────▼────────────┐   ┌──────▼──────────────┐
│ Native Handlers │   │   MCP Clients       │
│ - Kubernetes    │   │ - HTTP MCP Server   │
│ - kubectl exec  │   │ - VS Code MCP Tools │
└─────────────────┘   └─────────────────────┘
```

## Components

### 1. MCPToolsRegistry

Located in `src/services/mcp_registry.py`, the registry manages tool discovery and execution:

```python
class MCPToolsRegistry:
    """
    Central registry for MCP tools.
    
    Supports:
    - Tool registration from multiple sources
    - Tool discovery and lookup
    - Category-based organization
    - Kubernetes-specific tools
    """
    
    def register_tool(self, name: str, handler: Callable, category: str = "general")
    def get_tool(self, name: str) -> Optional[Callable]
    def list_tools(self, category: Optional[str] = None) -> List[str]
    def has_kubernetes_tools(self) -> bool
    def get_kubernetes_tools(self) -> Dict[str, Callable]
```

### 2. Kubernetes Handler

Located in `src/services/kubernetes_handler.py`, provides Kubernetes-specific operations:

```python
class KubernetesHandler:
    """
    Handles Kubernetes operations via kubectl commands.
    
    Features:
    - Natural language query parsing
    - Status filtering (error, pending, healthy)
    - Namespace extraction
    - kubectl command execution
    - Output formatting
    """
    
    def is_kubernetes_query(self, message: str) -> bool
    async def handle_query(self, message: str, context: Optional[str] = None) -> str
```

### 3. Native kubectl Integration

The current implementation uses **direct kubectl execution** for reliability and simplicity:

**Benefits:**
- ✅ No additional dependencies
- ✅ Works with any cluster kubectl can access
- ✅ Consistent with kubectl behavior
- ✅ Easy to debug and troubleshoot
- ✅ Full feature parity with kubectl

**Implementation:**
```python
async def _run_kubectl_command(self, args: list[str]) -> tuple[bool, str]:
    """Execute kubectl command and return results."""
    cmd = ["kubectl"] + args
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    # ... handle output
```

## Tool Categories

### Kubernetes Tools

Currently implemented tools:

| Tool | Command | Description |
|------|---------|-------------|
| `list_pods` | `/k8s pods [namespace]` | List pods with optional filtering |
| `get_logs` | `/k8s logs <pod> [namespace]` | Get pod logs (last 50 lines) |
| `scale_deployment` | `/k8s scale <deployment> <replicas> [namespace]` | Scale deployment |
| `list_nodes` | `/k8s nodes` | List cluster nodes |
| `list_deployments` | `/k8s deployments [namespace]` | List deployments |
| `list_services` | `/k8s services [namespace]` | List services |
| `list_namespaces` | `/k8s namespaces` | List all namespaces |
| `list_events` | `/k8s events [namespace]` | Show cluster events |
| `describe_resource` | `/k8s describe <type> <name> [namespace]` | Describe resource |
| `top_resources` | `/k8s top pods\|nodes [namespace]` | Show resource usage |
| `list_contexts` | `/k8s contexts` | List kubectl contexts |
| `view_config` | `/k8s config` | View kubeconfig |

### Natural Language Processing

The registry supports intelligent query parsing:

**Intent Detection:**
```python
# Detects: pods, deployments, services, nodes, logs, scale, events
query = "show me error pods in production"
# Extracts:
# - intent: list_pods
# - namespace: production
# - filter: error
```

**Status Filtering:**
- `error/failed/crash` → Shows pods with issues
- `unhealthy/not ready` → Shows pods not fully ready
- `pending` → Shows pending pods
- `running/healthy` → Shows only healthy pods

**Namespace Extraction:**
```python
# Patterns recognized:
"in production namespace"
"namespace staging"
"in pos-order4u"
"-n production"
```

## Extending the Registry

### Adding New Tools

1. **Create Handler Function:**

```python
# In src/services/custom_handler.py
async def handle_custom_operation(params: dict) -> str:
    """Custom tool implementation."""
    # Your logic here
    return result
```

2. **Register Tool:**

```python
# In src/services/mcp_registry.py or src/main.py
registry = MCPToolsRegistry()
registry.register_tool(
    name="custom_operation",
    handler=handle_custom_operation,
    category="custom"
)
```

3. **Add Natural Language Support:**

```python
# In src/services/message_handler.py
async def _handle_custom_query(self, message: ChannelMessage) -> None:
    if self._is_custom_query(message.content):
        result = await handle_custom_operation(...)
        await self.router.send_message(...)
```

### Adding New Categories

Categories help organize tools:

```python
# Existing categories
- "kubernetes"   # K8s cluster management
- "general"      # General-purpose tools
- "monitoring"   # Observability tools

# Add new category
registry.register_tool(
    name="check_database",
    handler=check_db_handler,
    category="database"
)
```

## MCP Server Integration

While the current implementation uses native kubectl, the registry is designed to support external MCP servers:

### Future MCP Server Support

```python
# Example: Connect to external MCP server
from src.services.mcp_client import MCPClient

mcp_client = MCPClient("https://your-mcp-server.com")
tools = await mcp_client.list_tools()

for tool in tools:
    registry.register_tool(
        name=tool["name"],
        handler=lambda **kwargs: mcp_client.call_tool(tool["name"], kwargs),
        category=tool.get("category", "general")
    )
```

### Benefits of MCP Server Integration

- 🔌 **Pluggable Architecture** - Add new capabilities without code changes
- 🔄 **Hot Reload** - Update tools without restarting the bot
- 🌐 **Remote Execution** - Run tools on specialized servers
- 🔒 **Isolation** - Separate sensitive operations
- 📊 **Centralized Logic** - Share tools across multiple bots

## Configuration

### Environment Variables

```bash
# Current implementation (native kubectl)
# No additional configuration needed - uses ~/.kube/config

# Future MCP server integration
MCP_SERVER_URL=https://your-mcp-server.com
MCP_API_KEY=your-api-key
MCP_TIMEOUT=30
```

### Registry Configuration

```python
# src/config.py
class Settings(BaseSettings):
    # MCP Registry settings
    mcp_registry_enabled: bool = True
    mcp_server_url: Optional[str] = None
    mcp_api_key: Optional[str] = None
    
    # Kubernetes settings
    kubectl_path: str = "kubectl"
    kubectl_timeout: int = 30
    k8s_log_lines: int = 50  # Default log lines to show
```

## Security Considerations

### kubectl Execution

- ✅ Commands are validated before execution
- ✅ No shell injection - uses subprocess with argument list
- ✅ Respects kubeconfig permissions
- ✅ Logs all executed commands
- ✅ Error messages don't expose sensitive data

### RBAC Permissions

Ensure the bot's kubeconfig has appropriate permissions:

```yaml
# Recommended ClusterRole for bot
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: ai-agent-viewer
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["pods", "deployments", "services", "nodes", "namespaces", "events"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments/scale"]
  verbs: ["get", "update"]
```

### MCP Server Security (Future)

- 🔐 API key authentication
- 🔒 TLS/HTTPS only
- ⏱️ Request timeouts
- 📝 Audit logging
- 🚫 Input validation

## Monitoring

### Metrics

Track tool usage:

```python
# In message_handler.py
logger.info("k8s_command_executed", 
    command=subcommand, 
    namespace=namespace,
    success=success,
    execution_time_ms=elapsed
)
```

### Error Handling

All tools include comprehensive error handling:

```python
try:
    result = await execute_tool(...)
except FileNotFoundError:
    return "kubectl not found. Please install kubectl."
except subprocess.TimeoutExpired:
    return "Command timed out. Cluster may be unreachable."
except Exception as e:
    logger.error("tool_execution_failed", error=str(e))
    return f"Error: {str(e)}"
```

## Best Practices

1. **Always Validate Input** - Sanitize user input before passing to tools
2. **Use Async Operations** - All tools should be async for non-blocking execution
3. **Implement Timeouts** - Prevent hanging operations
4. **Log Everything** - Track tool usage and errors
5. **Format Output** - Make results readable in chat
6. **Handle Errors Gracefully** - Provide helpful error messages
7. **Respect Permissions** - Check RBAC before executing commands
8. **Truncate Large Output** - Limit response size for chat

## Troubleshooting

### Common Issues

**kubectl not found:**
```bash
# Install kubectl
brew install kubectl  # macOS
apt install kubectl   # Debian/Ubuntu

# Verify installation
which kubectl
kubectl version
```

**Permission denied:**
```bash
# Check kubeconfig
kubectl config view

# Test connection
kubectl get nodes

# Verify RBAC permissions
kubectl auth can-i get pods
```

**Command timeouts:**
- Check cluster connectivity
- Increase timeout in settings
- Verify kubeconfig is current

**Registry not finding tools:**
- Check tool registration
- Verify imports
- Review logs for registration errors

## Future Enhancements

- [ ] Add MCP HTTP server integration
- [ ] Support for custom MCP protocols
- [ ] Tool versioning and updates
- [ ] Tool dependencies and prerequisites
- [ ] Tool caching and rate limiting
- [ ] Multi-cluster support
- [ ] Tool permissions and access control
- [ ] Interactive tool flows (multi-step operations)
- [ ] Tool marketplace/discovery

## References

- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Kubernetes API Reference](https://kubernetes.io/docs/reference/)
- [kubectl Command Reference](https://kubernetes.io/docs/reference/kubectl/)
- [MCP Integration Guide](mcp-integration.md)
- [Kubernetes Integration Guide](kubernetes-integration.md)

## Related Files

- `src/services/mcp_registry.py` - Registry implementation
- `src/services/kubernetes_handler.py` - Kubernetes operations
- `src/services/message_handler.py` - Query parsing and routing
- `src/services/mcp_client.py` - MCP server client (future use)
- `docs/kubernetes-integration.md` - K8s usage guide
- `docs/mcp-integration.md` - MCP server integration

---

Last Updated: February 27, 2026
