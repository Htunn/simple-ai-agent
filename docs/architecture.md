# Architecture Design

## Overview

Simple AI Agent is a production-ready multi-channel conversational AI system built with a modular, layered architecture. The system follows Domain-Driven Design (DDD) principles with clear separation of concerns across presentation, application, domain, and infrastructure layers.

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
- `DiscordAdapter`
- `TelegramAdapter`
- `MessageRouter`

**Responsibilities:**
- Protocol translation (Discord/Telegram → ChannelMessage)
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
- `GitHubModelsClient` - AI model interaction
- `ModelSelector` - Model preference resolution
- `ContextBuilder` - Conversation context construction
- `PromptManager` - System prompt templates

**Responsibilities:**
- AI model selection logic
- Conversation context building
- Prompt engineering
- Response generation

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

1. **Ingestion**: Message arrives via Discord/Telegram
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
1. Conversation.model_override (per-conversation setting)
   ↓ (if not set)
2. User.preferred_model (user preference)
   ↓ (if not set)
3. ChannelConfig.default_model (channel default)
   ↓ (if not set)
4. Settings.default_model (system default)
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
- **Discord**: Bot token + intents validation
- **Telegram**: Webhook signature verification
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
- [Discord.py Guide](https://discordpy.readthedocs.io/)
- [Python Telegram Bot](https://python-telegram-bot.readthedocs.io/)
- [GitHub Models](https://github.com/marketplace/models)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
