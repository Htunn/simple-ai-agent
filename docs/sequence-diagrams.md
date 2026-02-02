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
