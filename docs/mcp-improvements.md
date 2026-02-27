# MCP Integration Improvements

## Overview

This document describes the improved MCP (Model Context Protocol) integration that follows industry standards.

## Architecture

### Stdio-based Communication

The new implementation uses stdio (stdin/stdout) for JSON-RPC 2.0 communication, following the MCP specification:

```
┌─────────────┐           ┌──────────────┐           ┌──────────┐
│   AI Agent  │  stdio    │  MCP Server  │  exec     │ kubectl  │
│  (Client)   │ ◄───────► │  (Process)   │ ────────► │          │
└─────────────┘  JSON-RPC └──────────────┘           └──────────┘
```

### Components

1. **MCPClient** (`src/services/mcp_client.py`)
   - Manages subprocess communication with MCP server
   - Sends JSON-RPC 2.0 requests over stdin
   - Receives JSON-RPC 2.0 responses from stdout
   - Handles process lifecycle (start, stop, restart)

2. **KubernetesMCPServer** (`src/mcp/kubernetes_server.py`)
   - Implements MCP protocol methods: `initialize`, `tools/list`, `tools/call`
   - Executes kubectl commands via asyncio subprocess
   - Returns results in MCP format with content[] structure

3. **StdioTransport** (`src/mcp/stdio_transport.py`)
   - Low-level stdio communication handler
   - Reads JSON-RPC requests from stdin
   - Writes JSON-RPC responses to stdout
   - Logs to stderr for debugging

4. **Server Launcher** (`scripts/mcp_server.py`)
   - Entry point for starting the MCP server
   - Can be invoked by MCPClient or standalone
   - Handles Python path configuration

## Configuration

### .mcp-config.json

```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "python3",
      "args": ["scripts/mcp_server.py"],
      "description": "Kubernetes management tools via kubectl"
    }
  },
  "env": {
    "KUBECONFIG": "~/.kube/config"
  }
}
```

## Available Tools

The Kubernetes MCP server provides 13 tools:

1. **k8s_get_pods** - List pods in a namespace
2. **k8s_get_nodes** - List cluster nodes
3. **k8s_get_deployments** - List deployments
4. **k8s_get_services** - List services
5. **k8s_get_namespaces** - List namespaces
6. **k8s_get_logs** - Get pod logs
7. **k8s_scale_deployment** - Scale a deployment
8. **k8s_describe_resource** - Describe any resource
9. **k8s_get_events** - Get cluster events
10. **k8s_top_pods** - Show pod resource usage
11. **k8s_top_nodes** - Show node resource usage
12. **k8s_get_contexts** - List kubectl contexts
13. **k8s_current_context** - Get current context

## Protocol Flow

### 1. Server Initialization

```json
Client → Server:
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "simple-ai-agent",
      "version": "1.0.0"
    }
  }
}

Server → Client:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {"tools": {}},
    "serverInfo": {
      "name": "kubernetes-mcp-server",
      "version": "1.0.0"
    }
  }
}
```

### 2. List Tools

```json
Client → Server:
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}

Server → Client:
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "k8s_get_pods",
        "description": "List pods in a Kubernetes namespace",
        "inputSchema": {
          "type": "object",
          "properties": {
            "namespace": {
              "type": "string",
              "description": "Kubernetes namespace"
            }
          }
        }
      }
    ]
  }
}
```

### 3. Call Tool

```json
Client → Server:
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "k8s_get_pods",
    "arguments": {
      "namespace": "default"
    }
  }
}

Server → Client:
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "NAME              READY   STATUS    RESTARTS   AGE\nnginx-abc123      1/1     Running   0          10m"
      }
    ]
  }
}
```

## Advantages Over HTTP

1. **Standards Compliance**: Follows MCP specification exactly
2. **Simpler Architecture**: No HTTP server required
3. **Better Isolation**: Process-level isolation for security
4. **Credential Isolation**: kubectl config stays in server process
5. **Compatibility**: Works with standard MCP clients (Claude Desktop, LobeHub, etc.)
6. **Lower Overhead**: No HTTP protocol overhead
7. **Native Integration**: Can be used as a standalone MCP server

## Security Benefits

1. **Credential Isolation**: The AI agent never sees kubectl credentials
2. **Process Isolation**: Server runs in separate process with own permissions
3. **No Network Exposure**: Communication only via stdio, no network ports
4. **Input Validation**: All arguments validated before execution
5. **Output Sanitization**: Only kubectl output is returned

## Usage

### From AI Agent

The MCPClient automatically starts the server when needed:

```python
from src.services.mcp_client import MCPClient

# Client will start server automatically
client = MCPClient()

# List available tools
tools = await client.list_tools()

# Call a tool
result = await client.call_tool("k8s_get_pods", {"namespace": "default"})

# Clean up
await client.close()
```

### Standalone Usage

The MCP server can also run standalone for testing:

```bash
# Run server (it will wait for stdin)
python scripts/mcp_server.py

# Send initialize request
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}' | python scripts/mcp_server.py

# List tools
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | python scripts/mcp_server.py

# Call tool
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"k8s_get_pods","arguments":{"namespace":"default"}}}' | python scripts/mcp_server.py
```

## Compatibility

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "python3",
      "args": ["/path/to/simple-ai-agent/scripts/mcp_server.py"]
    }
  }
}
```

### LobeHub

The server can be configured in LobeHub's MCP settings using the same command and args.

## Testing

### Test Initialization

```bash
# Terminal 1: Start server
python scripts/mcp_server.py

# Terminal 2: Send initialize
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}'
```

### Test Tool Listing

```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

### Test Tool Execution

```bash
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"k8s_get_pods","arguments":{"namespace":"default"}}}'
```

## Troubleshooting

### Server Not Starting

- Check Python path in `.mcp-config.json`
- Verify `scripts/mcp_server.py` is executable
- Check stderr logs for initialization errors

### kubectl Commands Failing

- Verify kubectl is installed: `which kubectl`
- Check kubeconfig: `kubectl config view`
- Test kubectl manually: `kubectl get pods`

### Communication Errors

- Check JSON format (must be one line per request)
- Verify newline characters (\\n) at end of each message
- Check stderr logs for transport errors

## Migration from HTTP

The old HTTP-based implementation is deprecated. To migrate:

1. Update application startup to not specify `base_url`
2. Remove HTTP-based MCP server if running
3. MCP client will automatically use stdio-based server
4. Update any custom tool integrations

## Future Enhancements

1. **Additional Servers**: Add servers for Docker, AWS, databases
2. **Tool Categories**: Group tools by functionality
3. **Resource Support**: Implement resources/list and resources/read
4. **Prompts Support**: Add prompts/list and prompts/get
5. **Notifications**: Implement server-to-client notifications
6. **Sampling**: Add sampling request support for AI model calls
