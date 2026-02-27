# Sequence Diagrams

This document contains sequence diagrams showing the interactions between components for key use cases.

## 1. User Message Processing Flow

This diagram shows the complete flow of processing a user message and generating an AI response.

```mermaid
sequenceDiagram
    actor User
    participant Discord
    participant DiscordAdapter
    participant Router
    participant MessageHandler
    participant SessionManager
    participant Redis
    participant ContextBuilder
    participant ModelSelector
    participant GitHubClient
    participant GitHub
    participant MessageRepo
    participant PostgreSQL

    User->>Discord: Send message: "Hello!"
    Discord->>DiscordAdapter: on_message event
    DiscordAdapter->>DiscordAdapter: parse_message()
    DiscordAdapter->>Router: handle_incoming_message(ChannelMessage)
    Router->>MessageHandler: handle_message(message)
    
    %% Session Management
    MessageHandler->>SessionManager: get_or_create_session(channel, user_id)
    SessionManager->>Redis: HGETALL session:discord:user123
    alt Session in cache
        Redis-->>SessionManager: session_data
    else Session not in cache
        Redis-->>SessionManager: null
        SessionManager->>PostgreSQL: SELECT user WHERE channel_user_id=?
        alt User exists
            PostgreSQL-->>SessionManager: user_data
        else User doesn't exist
            SessionManager->>PostgreSQL: INSERT INTO users
            PostgreSQL-->>SessionManager: new_user
        end
        SessionManager->>PostgreSQL: SELECT conversation WHERE user_id=?
        PostgreSQL-->>SessionManager: conversation_data
        SessionManager->>Redis: HSET session:discord:user123
        Redis-->>SessionManager: OK
    end
    SessionManager-->>MessageHandler: session_data

    %% Save user message
    MessageHandler->>MessageRepo: create(conversation_id, "user", "Hello!")
    MessageRepo->>PostgreSQL: INSERT INTO messages
    PostgreSQL-->>MessageRepo: message_id
    MessageRepo-->>MessageHandler: user_message

    %% Build context
    MessageHandler->>ContextBuilder: build_context(conversation_id)
    ContextBuilder->>MessageRepo: get_conversation_history(conversation_id, limit=20)
    MessageRepo->>PostgreSQL: SELECT * FROM messages WHERE conversation_id=?
    PostgreSQL-->>MessageRepo: message_list
    MessageRepo-->>ContextBuilder: messages
    ContextBuilder->>ContextBuilder: format messages for AI
    ContextBuilder-->>MessageHandler: context_messages

    %% Select model
    MessageHandler->>ModelSelector: select_model(user_id, conversation_id, channel)
    ModelSelector->>PostgreSQL: Check conversation.model_override
    PostgreSQL-->>ModelSelector: null
    ModelSelector->>PostgreSQL: Check user.preferred_model
    PostgreSQL-->>ModelSelector: "gpt-4"
    ModelSelector-->>MessageHandler: "gpt-4"

    %% Generate AI response
    MessageHandler->>GitHubClient: generate_response(messages, model="gpt-4")
    GitHubClient->>GitHub: POST /chat/completions
    Note over GitHub: AI Processing<br/>(1-5 seconds)
    GitHub-->>GitHubClient: {choices: [{message: {content: "Hi! How can I help?"}}]}
    GitHubClient-->>MessageHandler: ("Hi! How can I help?", 45 tokens)

    %% Save assistant message
    MessageHandler->>MessageRepo: create(conversation_id, "assistant", response)
    MessageRepo->>PostgreSQL: INSERT INTO messages
    PostgreSQL-->>MessageRepo: message_id
    MessageRepo-->>MessageHandler: assistant_message

    %% Update session
    MessageHandler->>SessionManager: update_session_activity(channel, user_id)
    SessionManager->>PostgreSQL: UPDATE conversations SET last_activity=NOW()
    PostgreSQL-->>SessionManager: OK
    SessionManager->>Redis: EXPIRE session:discord:user123 3600
    Redis-->>SessionManager: OK

    %% Send response
    MessageHandler->>Router: send_message(channel, user_id, response)
    Router->>DiscordAdapter: send_message(user_id, "Hi! How can I help?")
    DiscordAdapter->>Discord: channel.send("Hi! How can I help?")
    Discord->>User: Display response
```

## 2. Command Processing Flow (/model)

This diagram shows how a user changes their preferred AI model.

```mermaid
sequenceDiagram
    actor User
    participant Telegram
    participant TelegramAdapter
    participant Router
    participant MessageHandler
    participant SessionManager
    participant ModelSelector
    participant UserRepo
    participant PostgreSQL

    User->>Telegram: Send "/model claude-3-opus"
    Telegram->>TelegramAdapter: handle_message(update)
    TelegramAdapter->>TelegramAdapter: parse_message()
    TelegramAdapter->>Router: handle_incoming_message(ChannelMessage)
    Router->>MessageHandler: handle_message(message)
    
    MessageHandler->>MessageHandler: Check if command (starts with /)
    Note over MessageHandler: Detected: /model command
    
    MessageHandler->>SessionManager: get_or_create_session(telegram, user456)
    SessionManager-->>MessageHandler: session_data
    
    MessageHandler->>MessageHandler: Parse command: ["model", "claude-3-opus"]
    MessageHandler->>MessageHandler: Validate model is supported
    
    MessageHandler->>ModelSelector: set_user_model(user_id, "claude-3-opus")
    ModelSelector->>UserRepo: update_preferred_model(user_id, "claude-3-opus")
    UserRepo->>PostgreSQL: UPDATE users SET preferred_model=?
    PostgreSQL-->>UserRepo: 1 row updated
    UserRepo-->>ModelSelector: updated_user
    ModelSelector-->>MessageHandler: true
    
    MessageHandler->>Router: send_message(telegram, user456, "Model set to: claude-3-opus")
    Router->>TelegramAdapter: send_message(user456, response)
    TelegramAdapter->>Telegram: bot.send_message(chat_id, text)
    Telegram->>User: "Model set to: claude-3-opus"
```

## 3. Session Reset Flow (/reset)

This diagram shows how a conversation is reset.

```mermaid
sequenceDiagram
    actor User
    participant Discord
    participant DiscordAdapter
    participant Router
    participant MessageHandler
    participant SessionManager
    participant ConversationRepo
    participant Redis
    participant PostgreSQL

    User->>Discord: Send "/reset"
    Discord->>DiscordAdapter: on_message event
    DiscordAdapter->>Router: handle_incoming_message(message)
    Router->>MessageHandler: handle_message(message)
    
    MessageHandler->>MessageHandler: Check command: /reset
    
    MessageHandler->>SessionManager: get_or_create_session(discord, user789)
    SessionManager-->>MessageHandler: session_data{conversation_id: "abc-123"}
    
    MessageHandler->>SessionManager: clear_session(discord, user789)
    
    %% Deactivate conversation
    SessionManager->>ConversationRepo: deactivate(conversation_id)
    ConversationRepo->>PostgreSQL: UPDATE conversations SET is_active=false
    PostgreSQL-->>ConversationRepo: OK
    ConversationRepo-->>SessionManager: deactivated_conversation
    
    %% Clear cache
    SessionManager->>Redis: DEL session:discord:user789
    Redis-->>SessionManager: 1 key deleted
    SessionManager-->>MessageHandler: session cleared
    
    MessageHandler->>Router: send_message(discord, user789, "Conversation reset!")
    Router->>DiscordAdapter: send_message(user789, response)
    DiscordAdapter->>Discord: channel.send("Conversation reset! Starting fresh.")
    Discord->>User: Display confirmation
```

## 4. Application Startup Flow

This diagram shows the initialization sequence when the application starts.

```mermaid
sequenceDiagram
    participant Docker
    participant Main
    participant FastAPI
    participant Logger
    participant Database
    participant Redis
    participant Router
    participant DiscordAdapter
    participant TelegramAdapter
    participant GitHubClient
    participant MessageHandler

    Docker->>Main: python -m uvicorn src.main:app
    Main->>FastAPI: Create FastAPI app
    FastAPI->>Main: lifespan startup
    
    Main->>Logger: configure_logging(LOG_LEVEL)
    Logger-->>Main: logging configured
    
    Main->>Database: init_db()
    Database->>Database: Create async engine
    Database->>Database: Run Alembic migrations
    Database-->>Main: Database ready
    
    Main->>Redis: init_redis()
    Redis->>Redis: Connect to Redis
    Redis->>Redis: Test connection (PING)
    Redis-->>Main: Redis ready
    
    Main->>Router: create_router()
    Router->>DiscordAdapter: __init__(DISCORD_TOKEN)
    DiscordAdapter->>DiscordAdapter: Setup intents & bot
    DiscordAdapter-->>Router: adapter created
    Router->>TelegramAdapter: __init__(TELEGRAM_TOKEN)
    TelegramAdapter->>TelegramAdapter: Create application
    TelegramAdapter-->>Router: adapter created
    Router-->>Main: router with adapters
    
    Main->>GitHubClient: __init__(GITHUB_TOKEN)
    GitHubClient->>GitHubClient: Create AsyncOpenAI client
    GitHubClient-->>Main: client ready
    
    Main->>MessageHandler: __init__(router, ai_client)
    MessageHandler-->>Main: handler ready
    
    Main->>Router: set_message_handler(handler.handle_message)
    Router-->>Main: handler registered
    
    Main->>Router: start_all()
    par Start Discord
        Router->>DiscordAdapter: start()
        DiscordAdapter->>DiscordAdapter: bot.start(token)
        Note over DiscordAdapter: WebSocket connection<br/>to Discord
    and Start Telegram
        Router->>TelegramAdapter: start()
        TelegramAdapter->>TelegramAdapter: application.run_polling()
        Note over TelegramAdapter: Long polling for updates
    end
    
    Main->>FastAPI: Start serving
    Note over FastAPI: Listening on 0.0.0.0:8000
    FastAPI-->>Docker: Application ready
```

## 5. Health Check Flow

This diagram shows the health check endpoint operation.

```mermaid
sequenceDiagram
    actor Monitor
    participant FastAPI
    participant HealthRouter
    participant PostgreSQL
    participant Redis

    Monitor->>FastAPI: GET /health
    FastAPI->>HealthRouter: health_check()
    
    par Check Database
        HealthRouter->>PostgreSQL: SELECT 1
        alt Database healthy
            PostgreSQL-->>HealthRouter: Result: 1
            Note over HealthRouter: db_status = "healthy"
        else Database error
            PostgreSQL-->>HealthRouter: Connection error
            Note over HealthRouter: db_status = "unhealthy: ..."
        end
    and Check Redis
        HealthRouter->>Redis: PING
        alt Redis healthy
            Redis-->>HealthRouter: PONG
            Note over HealthRouter: redis_status = "healthy"
        else Redis error
            Redis-->>HealthRouter: Connection error
            Note over HealthRouter: redis_status = "unhealthy: ..."
        end
    end
    
    HealthRouter->>HealthRouter: Determine overall status
    alt All healthy
        HealthRouter-->>FastAPI: {status: "healthy", database: "healthy", redis: "healthy"}
        FastAPI-->>Monitor: 200 OK + JSON
    else Any unhealthy
        HealthRouter-->>FastAPI: HTTPException(503)
        FastAPI-->>Monitor: 503 Service Unavailable
    end
```

## 6. Telegram Webhook Flow

This diagram shows how Telegram webhooks are processed (alternative to polling).

```mermaid
sequenceDiagram
    participant Telegram
    participant FastAPI
    participant WebhookRouter
    participant TelegramAdapter
    participant Router
    participant MessageHandler

    Telegram->>FastAPI: POST /api/webhook/telegram
    Note over Telegram,FastAPI: Headers:<br/>X-Telegram-Bot-Api-Secret-Token
    
    FastAPI->>WebhookRouter: telegram_webhook(request)
    WebhookRouter->>WebhookRouter: Verify signature (TODO)
    
    WebhookRouter->>WebhookRouter: Parse request body
    Note over WebhookRouter: {update_id: 123,<br/>message: {...}}
    
    WebhookRouter->>Router: get_adapter("telegram")
    Router-->>WebhookRouter: telegram_adapter
    
    WebhookRouter->>TelegramAdapter: Update.de_json(body)
    TelegramAdapter-->>WebhookRouter: update_object
    
    WebhookRouter->>TelegramAdapter: handle_incoming_message(update)
    TelegramAdapter->>TelegramAdapter: parse_message()
    TelegramAdapter->>Router: route message
    Router->>MessageHandler: handle_message()
    Note over MessageHandler: Process message<br/>(see Diagram 1)
    
    WebhookRouter-->>FastAPI: {status: "ok"}
    FastAPI-->>Telegram: 200 OK
```

## Key Observations

### Performance Optimizations

1. **Session Caching**: Redis cache prevents database queries on every message
2. **Connection Pooling**: Reuse database connections across requests
3. **Async I/O**: Non-blocking operations allow high concurrency
4. **Message Batching**: Can batch database writes for better throughput

### Error Handling

1. **Retry Logic**: GitHub API calls retry with exponential backoff
2. **Graceful Degradation**: If AI fails, send error message to user
3. **Health Checks**: Continuous monitoring of dependencies
4. **Circuit Breaker**: (Future) Prevent cascading failures

### Security Measures

1. **Input Validation**: All user input validated at adapter layer
2. **Rate Limiting**: FastAPI middleware limits request rate
3. **Signature Verification**: Webhook signatures verified
4. **SQL Injection**: Parameterized queries via SQLAlchemy

### Scalability Patterns

1. **Stateless Design**: No in-memory state, can scale horizontally
2. **Load Balancing**: Multiple app instances behind load balancer
3. **Database Read Replicas**: (Future) Separate read/write workloads
4. **Cache Warming**: (Future) Pre-populate cache for active users

## 7. MCP Multi-Server Initialization Flow

This diagram shows the new multi-transport MCP architecture supporting both stdio and SSE servers.

```mermaid
sequenceDiagram
    participant Main
    participant MCPManager
    participant ConfigFile
    participant StdioTransport
    participant SSETransport
    participant K8sServer
    participant PortChecker

    Main->>MCPManager: __init__()
    MCPManager->>ConfigFile: load .mcp-config.json
    ConfigFile-->>MCPManager: {kubernetes: {type: "stdio"}, simplePortChecker: {type: "sse"}}
    
    Main->>MCPManager: start()
    Note over MCPManager: Initialize all configured servers
    
    par Kubernetes Server (stdio)
        MCPManager->>StdioTransport: _create_stdio_transport("kubernetes")
        StdioTransport->>StdioTransport: Create MCPClient(subprocess)
        StdioTransport-->>MCPManager: stdio_transport
        
        MCPManager->>StdioTransport: start()
        StdioTransport->>K8sServer: subprocess.create("python3 scripts/mcp_server.py")
        Note over K8sServer: Server process starts<br/>Listens on stdin/stdout
        K8sServer-->>StdioTransport: Process running (PID)
        StdioTransport-->>MCPManager: Started
        
        MCPManager->>StdioTransport: initialize()
        StdioTransport->>K8sServer: {"jsonrpc": "2.0", "method": "initialize"}
        K8sServer-->>StdioTransport: {"result": {"serverInfo": {...}, "capabilities": {...}}}
        StdioTransport-->>MCPManager: Initialized
        
        MCPManager->>StdioTransport: list_tools()
        StdioTransport->>K8sServer: {"jsonrpc": "2.0", "method": "tools/list"}
        K8sServer-->>StdioTransport: {"result": {"tools": [13 k8s tools]}}
        StdioTransport-->>MCPManager: [k8s_get_pods, k8s_get_nodes, ...]
        
    and SimplePortChecker Server (SSE)
        MCPManager->>SSETransport: _create_sse_transport("simplePortChecker")
        SSETransport->>SSETransport: Create httpx.AsyncClient()
        SSETransport-->>MCPManager: sse_transport
        
        MCPManager->>SSETransport: start()
        SSETransport->>SSETransport: Configure headers (Accept: application/json, text/event-stream)
        SSETransport-->>MCPManager: Started
        
        MCPManager->>SSETransport: initialize()
        SSETransport->>PortChecker: POST https://mcp.simpleportchecker.com/mcp
        Note over SSETransport,PortChecker: Headers:<br/>Accept: application/json, text/event-stream<br/>Content-Type: application/json
        PortChecker-->>SSETransport: event: message\ndata: {"result": {"serverInfo": {...}}}
        SSETransport->>SSETransport: Parse SSE format (extract data: lines)
        SSETransport-->>MCPManager: Initialized
        
        MCPManager->>SSETransport: list_tools()
        SSETransport->>PortChecker: POST /mcp {"method": "tools/list"}
        PortChecker-->>SSETransport: event: message\ndata: {"result": {"tools": [8 security tools]}}
        SSETransport-->>MCPManager: [scan_ports, analyze_certificate, detect_l7_protection, ...]
    end
    
    MCPManager->>MCPManager: Build tool registry
    Note over MCPManager: tool_registry = {<br/>"scan_ports": "simplePortChecker",<br/>"k8s_get_pods": "kubernetes"<br/>}
    
    MCPManager->>Main: get_server_info()
    Main->>Main: Log: "mcp_servers_started servers=2 total_tools=21"
```

## 8. Security Scanning with SSE MCP Server

This diagram shows how security queries are routed to the simplePortChecker MCP server.

```mermaid
sequenceDiagram
    actor User
    participant Telegram
    participant TelegramAdapter
    participant MessageHandler
    participant MCPManager
    participant SSETransport
    participant PortChecker as SimplePortChecker<br/>(SSE Server)

    User->>Telegram: "is port 443 open on lobehub.com"
    Telegram->>TelegramAdapter: handle_message(update)
    TelegramAdapter->>MessageHandler: handle_message(ChannelMessage)
    
    MessageHandler->>MessageHandler: _is_security_query()
    Note over MessageHandler: Detected: port, open keywords
    
    MessageHandler->>MessageHandler: Parse query with regex
    Note over MessageHandler: port_pattern matches:<br/>port=443, host=lobehub.com
    
    MessageHandler->>MCPManager: list_all_tools()
    MCPManager-->>MessageHandler: [{name: "scan_ports", _server: "simplePortChecker"}, ...]
    
    MessageHandler->>MessageHandler: Filter tools by server="simplePortChecker"
    MessageHandler->>MessageHandler: Select tool: scan_ports
    
    MessageHandler->>MCPManager: call_tool("scan_ports", {target: "lobehub.com", ports: [443]})
    
    MCPManager->>MCPManager: Lookup tool_registry["scan_ports"]
    Note over MCPManager: Found server: simplePortChecker
    
    MCPManager->>SSETransport: call_tool("scan_ports", arguments)
    
    SSETransport->>SSETransport: Build JSON-RPC request<br/>{method: "tools/call", params: {...}}
    
    SSETransport->>PortChecker: POST /mcp<br/>Headers: Accept: application/json, text/event-stream
    
    Note over PortChecker: Port scanning in progress...
    
    PortChecker-->>SSETransport: event: message\ndata: {"method": "notifications/message", "params": {"level": "info"}}
    Note over SSETransport: Progress notification (ignored)
    
    PortChecker-->>SSETransport: event: message\ndata: {"method": "notifications/message", "params": {"level": "info"}}
    Note over SSETransport: Another progress notification
    
    PortChecker-->>SSETransport: event: message\ndata: {"jsonrpc": "2.0", "id": 3, "result": {content: [...]}}
    Note over SSETransport: Final result with matching ID
    
    SSETransport->>SSETransport: Parse SSE response:<br/>1. Split by newlines<br/>2. Find lines with "data: "<br/>3. Parse JSON<br/>4. Match request ID
    
    SSETransport-->>MCPManager: {"content": [{"type": "text", "text": "{...}"}], "isError": false}
    
    MCPManager-->>MessageHandler: Tool result
    
    MessageHandler->>MessageHandler: _format_tool_result()
    Note over MessageHandler: Format with icon and title:<br/>"🔌 Port Scan"
    
    MessageHandler->>TelegramAdapter: send_message(response)
    TelegramAdapter->>Telegram: bot.send_message()
    Telegram->>User: "🔌 Port Scan\n\nTarget: lobehub.com\n\nPort 443: open (https)"
```

## 9. Kubernetes Query with Natural Language Processing

This diagram shows the enhanced Kubernetes integration with NLP query parsing.

```mermaid
sequenceDiagram
    actor User
    participant Discord
    participant DiscordAdapter
    participant MessageHandler
    participant MCPManager
    participant StdioTransport
    participant K8sServer
    participant Kubectl

    User->>Discord: "show me error pods in pos-order4u"
    Discord->>DiscordAdapter: on_message event
    DiscordAdapter->>MessageHandler: handle_message(ChannelMessage)
    
    MessageHandler->>MessageHandler: _is_kubernetes_query()
    Note over MessageHandler: Detected: pods keyword
    
    MessageHandler->>MessageHandler: _handle_kubernetes_query()
    MessageHandler->>MessageHandler: Parse natural language query
    Note over MessageHandler: Extracted:<br/>- action: "show/list"<br/>- resource: "pods"<br/>- namespace: "pos-order4u"<br/>- filter: "error"
    
    MessageHandler->>MCPManager: call_tool("k8s_get_pods", {namespace: "pos-order4u"})
    
    MCPManager->>MCPManager: Lookup tool in registry
    Note over MCPManager: Found: kubernetes server
    
    MCPManager->>StdioTransport: call_tool("k8s_get_pods", args)
    
    StdioTransport->>K8sServer: {"jsonrpc": "2.0", "method": "tools/call",<br/>"params": {"name": "k8s_get_pods", "arguments": {namespace: "pos-order4u"}}}
    Note over K8sServer: Via stdin
    
    K8sServer->>Kubectl: subprocess: kubectl get pods -n pos-order4u -o json
    Kubectl-->>K8sServer: JSON output with pod list
    
    K8sServer->>K8sServer: Filter and format pods
    K8sServer-->>StdioTransport: {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "..."}]}}
    Note over StdioTransport: Via stdout
    
    StdioTransport-->>MCPManager: Tool result
    MCPManager-->>MessageHandler: Pod data
    
    MessageHandler->>MessageHandler: Apply status filter: "error"
    Note over MessageHandler: Filter for:<br/>- CrashLoopBackOff<br/>- Error<br/>- ImagePullBackOff
    
    MessageHandler->>MessageHandler: Format output with emojis
    Note over MessageHandler: ❌ for error pods<br/>Pod name, status, restarts
    
    MessageHandler->>DiscordAdapter: send_message()
    DiscordAdapter->>Discord: channel.send()
    Discord->>User: "📦 Pods with issues in namespace pos-order4u:\n\n❌ worker-def456\nStatus: CrashLoopBackOff | Restarts: 10"
```

## 10. Application Shutdown with MCP Cleanup

This diagram shows the graceful shutdown sequence including MCP server cleanup.

```mermaid
sequenceDiagram
    participant Docker
    participant Main
    participant FastAPI
    participant MCPManager
    participant StdioTransport
    participant SSETransport
    participant K8sServer
    participant Router

    Docker->>Main: SIGTERM signal
    Main->>FastAPI: lifespan shutdown
    
    FastAPI->>Main: Trigger shutdown handlers
    
    par Stop MCP Servers
        Main->>MCPManager: stop()
        
        MCPManager->>StdioTransport: stop()
        StdioTransport->>K8sServer: terminate() subprocess
        K8sServer-->>StdioTransport: Process terminated
        StdioTransport-->>MCPManager: Stopped
        
        MCPManager->>SSETransport: stop()
        SSETransport->>SSETransport: await client.aclose()
        SSETransport-->>MCPManager: Stopped
        
        MCPManager-->>Main: All servers stopped
        
    and Stop Channel Adapters
        Main->>Router: stop_all()
        Router->>Router: Stop Discord bot
        Router->>Router: Stop Telegram polling
        Router-->>Main: Adapters stopped
    end
    
    Main->>Main: Close database connections
    Main->>Main: Close Redis connections
    
    Main-->>FastAPI: Shutdown complete
    FastAPI-->>Docker: Exit code 0
```

## Key Improvements in Multi-Transport MCP Architecture

### Protocol Support

1. **stdio Transport**: 
   - Subprocess-based communication
   - Standard input/output JSON-RPC
   - Local server processes
   - Used by: Kubernetes MCP server

2. **SSE Transport**: 
   - HTTP-based communication
   - Server-Sent Events protocol
   - Remote cloud servers
   - Used by: SimplePortChecker MCP server

### Server-Sent Events (SSE) Handling

**Format**: SSE responses contain multiple messages:
```
event: message
data: {"method":"notifications/message",...}

event: message
data: {"jsonrpc":"2.0","id":3,"result":{...}}
```

**Parsing Strategy**:
1. Split response by newlines
2. Find all lines starting with `data: `
3. Parse each as JSON
4. Match response by request ID
5. Ignore notifications, return final result

### Tool Registry Architecture

**Purpose**: Route tool calls to correct MCP server

**Structure**:
```python
tool_registry = {
    "scan_ports": "simplePortChecker",
    "analyze_certificate": "simplePortChecker",
    "k8s_get_pods": "kubernetes",
    "k8s_scale_deployment": "kubernetes",
    # ... 21 total tools
}
```

**Benefits**:
- Single unified interface for all tools
- Automatic routing to appropriate server
- Support for unlimited MCP servers
- Type-based server instantiation

### Security Scanning Integration

**8 Security Tools Available**:
1. **scan_ports** - Port scanning and service detection
2. **analyze_certificate** - SSL/TLS certificate analysis
3. **detect_l7_protection** - WAF/CDN detection (Cloudflare, AWS, Azure)
4. **check_mtls** - Mutual TLS verification
5. **check_security_headers** - HSTS, CSP, CORS analysis
6. **scan_owasp_vulnerabilities** - OWASP Top 10 scanning
7. **full_security_scan** - Comprehensive security assessment
8. **check_hybrid_identity** - Azure AD Hybrid Identity detection

**Natural Language Support**:
- "is port 443 open on lobehub.com"
- "check certificate for example.com"
- "detect waf on site.com"
- "full security scan on api.example.com"

### Configuration Format

**`.mcp-config.json`**:
```json
{
  "mcpServers": {
    "kubernetes": {
      "type": "stdio",
      "command": "python3",
      "args": ["scripts/mcp_server.py"],
      "description": "Kubernetes management tools"
    },
    "simplePortChecker": {
      "type": "sse",
      "url": "https://mcp.simpleportchecker.com/mcp",
      "description": "Port checking and security tools"
    }
  }
}
```

**Environment Variables** (optional):
```json
{
  "env": {
    "KUBECONFIG": "~/.kube/config"
  }
}
```

