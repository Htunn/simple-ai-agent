# MCP Server Integration Guide

This guide explains how to integrate your AI Agent with a custom MCP (Model Context Protocol) server for business logic execution.

## What is MCP?

Model Context Protocol (MCP) is an open standard created by Anthropic that enables AI models to securely interact with external tools, data sources, and business logic. MCP provides:

- **Standardized tool definitions** - Consistent schema for tools
- **Resource access** - Read data from external sources
- **Security** - Controlled access to business logic
- **Extensibility** - Easy to add new capabilities

## Architecture

```
AI Agent → MCP Client → MCP Server → Your Business Logic
    ↓                       ↓
User Message         Tool Execution
    ↓                       ↓
AI Response  ←  Tool Result
```

## MCP Server Requirements

Your MCP server must implement the following JSON-RPC 2.0 endpoints:

### 1. List Tools
```
POST /mcp/tools/list
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 1
}

Response:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "get_customer_info",
        "description": "Retrieve customer information by ID",
        "inputSchema": {
          "type": "object",
          "properties": {
            "customer_id": {
              "type": "string",
              "description": "The customer ID"
            }
          },
          "required": ["customer_id"]
        }
      }
    ]
  }
}
```

### 2. Call Tool
```
POST /mcp/tools/call
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_customer_info",
    "arguments": {
      "customer_id": "12345"
    }
  },
  "id": 2
}

Response:
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"name\": \"John Doe\", \"email\": \"john@example.com\"}"
      }
    ]
  }
}
```

### 3. List Resources (Optional)
```
POST /mcp/resources/list
{
  "jsonrpc": "2.0",
  "method": "resources/list",
  "id": 3
}
```

### 4. Read Resource (Optional)
```
POST /mcp/resources/read
{
  "jsonrpc": "2.0",
  "method": "resources/read",
  "params": {
    "uri": "file://data/customers.json"
  },
  "id": 4
}
```

## Configuration

### 1. Set MCP Server URL

Add to your `.env` file:

```env
# MCP Server Configuration
MCP_SERVER_URL=http://localhost:3000
```

Or set via environment variable:
```bash
export MCP_SERVER_URL=http://your-mcp-server:3000
```

### 2. Restart Application

The AI Agent will automatically:
1. Connect to the MCP server on startup
2. Load available tools
3. Include tool descriptions in AI prompts
4. Execute tools when requested by the AI

## Creating a Simple MCP Server

Here's a minimal MCP server example using Node.js/Express:

```javascript
// server.js
const express = require('express');
const app = express();
app.use(express.json());

// Tool definitions
const tools = [
  {
    name: "get_weather",
    description: "Get current weather for a city",
    inputSchema: {
      type: "object",
      properties: {
        city: { type: "string", description: "City name" }
      },
      required: ["city"]
    }
  }
];

// List tools endpoint
app.post('/mcp/tools/list', (req, res) => {
  res.json({
    jsonrpc: "2.0",
    id: req.body.id,
    result: { tools }
  });
});

// Call tool endpoint
app.post('/mcp/tools/call', async (req, res) => {
  const { name, arguments: args } = req.body.params;
  
  if (name === 'get_weather') {
    // Your business logic here
    const weather = await getWeatherForCity(args.city);
    
    res.json({
      jsonrpc: "2.0",
      id: req.body.id,
      result: {
        content: [
          { type: "text", text: JSON.stringify(weather) }
        ]
      }
    });
  } else {
    res.json({
      jsonrpc: "2.0",
      id: req.body.id,
      error: { code: -32601, message: "Tool not found" }
    });
  }
});

app.listen(3000, () => console.log('MCP server on port 3000'));
```

Python/FastAPI example:

```python
# mcp_server.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, List

app = FastAPI()

class ToolCall(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = {}
    id: int

@app.post("/mcp/tools/list")
async def list_tools(request: ToolCall):
    return {
        "jsonrpc": "2.0",
        "id": request.id,
        "result": {
            "tools": [
                {
                    "name": "get_weather",
                    "description": "Get weather for a city",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "City name"
                            }
                        },
                        "required": ["city"]
                    }
                }
            ]
        }
    }

@app.post("/mcp/tools/call")
async def call_tool(request: ToolCall):
    tool_name = request.params.get("name")
    arguments = request.params.get("arguments", {})
    
    if tool_name == "get_weather":
        # Your business logic
        city = arguments.get("city")
        result = {"temp": 72, "condition": "sunny", "city": city}
        
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "result": {
                "content": [
                    {"type": "text", "text": str(result)}
                ]
            }
        }
    
    return {
        "jsonrpc": "2.0",
        "id": request.id,
        "error": {"code": -32601, "message": "Tool not found"}
    }

# Run with: uvicorn mcp_server:app --port 3000
```

## How It Works

### 1. Tool Discovery
On startup, the AI Agent:
- Connects to your MCP server
- Fetches available tools via `/mcp/tools/list`
- Caches tool definitions

### 2. Prompt Augmentation
When processing messages:
- Tool descriptions are added to the system prompt
- AI model learns what tools are available
- AI can decide when to use tools

### 3. Tool Execution
When AI requests a tool:
- Pattern detected: `TOOL_CALL: tool_name(arg1="value1")`
- Arguments parsed from AI response
- Tool executed via `/mcp/tools/call`
- Result returned to user

### Example Conversation

```
User: What's the weather in San Francisco?

AI (internal): I need to use the get_weather tool
TOOL_CALL: get_weather(city="San Francisco")

MCP Server: {"temp": 65, "condition": "foggy"}

AI Response: The weather in San Francisco is currently 65°F and foggy.
```

## Use Cases

### Customer Support
```javascript
{
  name: "get_customer_info",
  description: "Retrieve customer account information",
  // ... queries your CRM
}
```

### Order Management
```javascript
{
  name: "check_order_status",
  description: "Check status of an order",
  // ... queries your order database
}
```

### Inventory Lookup
```javascript
{
  name: "check_inventory",
  description: "Check product availability",
  // ... queries your inventory system
}
```

### Ticket Creation
```javascript
{
  name: "create_support_ticket",
  description: "Create a customer support ticket",
  // ... creates ticket in your system
}
```

## Security Considerations

### Authentication
Implement API key authentication:

```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != "your-secret-key":
        raise HTTPException(status_code=401)

@app.post("/mcp/tools/call", dependencies=[Depends(verify_api_key)])
async def call_tool(request: ToolCall):
    # ... tool execution
```

Update MCP client configuration:
```python
# In src/services/mcp_client.py
self.client = httpx.AsyncClient(
    base_url=self.base_url,
    timeout=30.0,
    headers={
        "Content-Type": "application/json",
        "X-API-Key": settings.mcp_api_key,
    },
)
```

### Rate Limiting
Protect your MCP server:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/mcp/tools/call")
@limiter.limit("10/minute")
async def call_tool(request: Request, ...):
    # ... tool execution
```

### Input Validation
Always validate tool arguments:

```python
def validate_customer_id(customer_id: str) -> bool:
    return len(customer_id) == 5 and customer_id.isdigit()

if not validate_customer_id(arguments.get("customer_id")):
    return error_response("Invalid customer ID format")
```

## Testing

### Test MCP Server Locally

```bash
# Start your MCP server
cd mcp-server
npm start  # or python -m uvicorn mcp_server:app --port 3000

# Test tool listing
curl -X POST http://localhost:3000/mcp/tools/list \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# Test tool execution
curl -X POST http://localhost:3000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params":{
      "name":"get_weather",
      "arguments":{"city":"San Francisco"}
    },
    "id":2
  }'
```

### Integration Testing

```python
# tests/test_mcp_integration.py
import pytest
from src.services.mcp_client import MCPClient

@pytest.mark.asyncio
async def test_mcp_tools_list():
    client = MCPClient("http://localhost:3000")
    tools = await client.list_tools()
    assert len(tools) > 0
    assert tools[0]["name"] == "get_weather"

@pytest.mark.asyncio
async def test_mcp_tool_call():
    client = MCPClient("http://localhost:3000")
    result = await client.call_tool(
        "get_weather",
        {"city": "San Francisco"}
    )
    assert result is not None
    await client.close()
```

## Monitoring

Monitor MCP integration health:

```python
# Add to your health check endpoint
@router.get("/health")
async def health_check():
    mcp_status = "not_configured"
    
    if settings.mcp_server_url:
        try:
            # Quick health check
            client = MCPClient()
            tools = await client.list_tools()
            mcp_status = "healthy" if tools else "unhealthy"
        except:
            mcp_status = "error"
    
    return {
        "status": "ok",
        "mcp": mcp_status
    }
```

## Troubleshooting

### Connection Errors
- Verify MCP_SERVER_URL is correct
- Check MCP server is running
- Verify network/firewall settings

### Tool Not Found
- Confirm tool name matches exactly
- Check tool is returned by `/mcp/tools/list`
- Review MCP server logs

### Empty Tool Results
- Add logging to MCP server
- Verify business logic is executing
- Check database connections

## Resources

- [MCP Specification](https://modelcontextprotocol.io/)
- [Anthropic MCP Documentation](https://docs.anthropic.com/claude/docs/model-context-protocol)
- [Example MCP Servers](https://github.com/modelcontextprotocol/servers)
