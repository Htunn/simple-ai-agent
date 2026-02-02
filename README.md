# 🦞 Clawbot AI Agent

A production-ready multi-channel AI agent inspired by OpenClaw, supporting Discord and Telegram with GitHub Models API integration (GPT-4, Claude Opus, Llama 3).

## Features

- 🤖 **Multi-Channel Support**: Discord and Telegram bots
- 🧠 **Multiple AI Models**: GPT-4, Claude 3 Opus, Llama 3 via GitHub Models
- 💾 **Full Message Persistence**: PostgreSQL with complete conversation history
- ⚡ **Session Management**: Redis-backed session caching
- 🎯 **Model Preferences**: Per-user and per-channel model selection
- 🐳 **Docker Ready**: Complete containerization with docker-compose
- 🔒 **Security Best Practices**: Environment-based configuration, input validation
- 📊 **Health Checks**: Built-in monitoring endpoints

## Prerequisites

- Python 3.12+
- Docker & Docker Compose (for containerized deployment)
- PostgreSQL 16 (if running locally)
- Redis 7 (if running locally)

## Quick Start

### 1. Clone and Setup

```bash
cd /Users/htunn/code/AI/simple-ai-agent

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required environment variables:
- `GITHUB_TOKEN`: GitHub fine-grained personal access token with Models API access
- `DISCORD_TOKEN`: Discord bot token (optional)
- `TELEGRAM_TOKEN`: Telegram bot token (optional)

### 3. GitHub Token Setup

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Fine-grained personal access token"
3. Configure:
   - **Repository access**: Choose repositories you need
   - **Permissions**: Enable Models API access
4. Copy token to `.env` as `GITHUB_TOKEN`

### 4. Discord Bot Setup (Optional)

1. Go to https://discord.com/developers/applications
2. Create "New Application"
3. Go to "Bot" → Click "Add Bot"
4. Enable "Message Content Intent" under "Privileged Gateway Intents"
5. Copy token to `.env` as `DISCORD_TOKEN`
6. Invite bot: `https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=2048&scope=bot`

### 5. Telegram Bot Setup (Optional)

1. Message @BotFather on Telegram
2. Send `/newbot` and follow instructions
3. Copy token to `.env` as `TELEGRAM_TOKEN`

### 6. Run with Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Check health
curl http://localhost:8000/health
```

### 7. Run Locally (Development)

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Update .env to use local database URLs
# DATABASE_URL=postgresql+asyncpg://clawbot:clawbot_password@localhost:5432/clawbot
# REDIS_URL=redis://localhost:6379/0

# Run migrations
python scripts/init_db.py

# Start application
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Usage

### Available Commands

Users can interact with the bot using these commands:

- `/help` - Show available commands
- `/model <name>` - Set AI model (gpt-4, claude-3-opus, llama-3-70b)
- `/reset` - Start a new conversation
- `/status` - Show current model and conversation statistics

### Model Selection Priority

The bot selects models based on this priority:

1. **Conversation Override** - Set with `/model` command
2. **User Preference** - Stored per user
3. **Channel Default** - Configured per channel (Discord/Telegram)
4. **System Default** - Fallback from `.env` (`DEFAULT_MODEL`)

### Example Conversation

```
User: Hello!
Bot: Hello! How can I help you today?

User: /model claude-3-opus
Bot: Model set to: claude-3-opus

User: Explain quantum computing in simple terms
Bot: [AI response using Claude 3 Opus]

User: /status
Bot: 📊 Status:
     Model: claude-3-opus
     Messages: 4
     Tokens: 532
```

## Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────┐
│              Discord / Telegram                      │
└────────────────┬────────────────────────────────────┘
                 │
         ┌───────▼────────┐
         │  Channel       │
         │  Adapters      │
         └───────┬────────┘
                 │
         ┌───────▼────────┐
         │  Message       │
         │  Handler       │
         └───────┬────────┘
                 │
      ┌──────────┴──────────┐
      │                     │
┌─────▼──────┐      ┌──────▼──────┐
│  Session   │      │   GitHub    │
│  Manager   │      │   Models    │
│  (Redis)   │      │   Client    │
└─────┬──────┘      └──────┬──────┘
      │                     │
      │             ┌───────▼────────┐
      │             │  Context       │
      │             │  Builder       │
      │             └───────┬────────┘
      │                     │
┌─────▼─────────────────────▼──────┐
│         PostgreSQL                │
│  (Users, Conversations, Messages) │
└───────────────────────────────────┘
```

### Detailed Documentation

For comprehensive architecture documentation, see:
- **[Architecture Design](docs/architecture.md)** - Layered architecture, design decisions, scalability
- **[Component Diagram](docs/component-diagram.md)** - System components and interactions
- **[Sequence Diagrams](docs/sequence-diagrams.md)** - Message flow, commands, startup sequences

## Project Structure

```
simple-ai-agent/
├── src/
│   ├── ai/                      # AI integration layer
│   │   ├── github_models.py     # GitHub Models client
│   │   ├── model_selector.py    # Model selection logic
│   │   ├── context_builder.py   # Conversation context
│   │   └── prompt_manager.py    # Prompt templates
│   ├── channels/                # Channel adapters
│   │   ├── base.py              # Base adapter interface
│   │   ├── discord_adapter.py   # Discord integration
│   │   ├── telegram_adapter.py  # Telegram integration
│   │   └── router.py            # Message routing
│   ├── database/                # Database layer
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── postgres.py          # PostgreSQL connection
│   │   ├── redis.py             # Redis connection
│   │   ├── repositories/        # Data access layer
│   │   └── migrations/          # Alembic migrations
│   ├── services/                # Business logic
│   │   ├── message_handler.py   # Message processing
│   │   └── session_manager.py   # Session management
│   ├── api/                     # FastAPI endpoints
│   │   ├── health.py            # Health checks
│   │   ├── webhooks.py          # Webhook endpoints
│   │   └── middleware.py        # Rate limiting
│   ├── utils/                   # Utilities
│   │   └── logger.py            # Logging configuration
│   ├── config.py                # Configuration management
│   └── main.py                  # Application entry point
├── scripts/
│   ├── init_db.py               # Database initialization
│   └── start.sh                 # Startup script
├── tests/                       # Test suite
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Container image
├── requirements.txt             # Python dependencies
├── alembic.ini                  # Migration configuration
└── README.md                    # This file
```

## Database Schema

### Users
- `id`: UUID (primary key)
- `channel_type`: Discord, Telegram, WhatsApp
- `channel_user_id`: User ID from channel
- `username`: Display name
- `preferred_model`: User's preferred AI model
- `created_at`: Timestamp

### Conversations
- `id`: UUID (primary key)
- `user_id`: Foreign key to users
- `channel_type`: Channel type
- `model_override`: Override model for this conversation
- `started_at`: Timestamp
- `last_activity`: Timestamp
- `is_active`: Boolean
- `metadata`: JSONB

### Messages
- `id`: UUID (primary key)
- `conversation_id`: Foreign key to conversations
- `role`: user, assistant, system
- `content`: Message text
- `model_used`: AI model used
- `timestamp`: Timestamp
- `token_count`: Token usage
- `metadata`: JSONB

### Channel Configs
- `id`: UUID (primary key)
- `channel_type`: Channel type
- `default_model`: Default model for channel
- `settings`: JSONB

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check (database + Redis)
- `GET /ready` - Readiness check
- `POST /api/webhook/telegram` - Telegram webhook
- `GET /api/webhook/test` - Test webhook server

## Development

### Run Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# With coverage
pytest --cov=src
```

### Code Quality

```bash
# Format code
black src/

# Lint
ruff check src/

# Type checking
mypy src/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Deployment

### Docker Production

```bash
# Build production image
docker build -t clawbot-agent:latest .

# Run with docker-compose
docker-compose up -d

# Scale (if needed)
docker-compose up -d --scale app=3
```

### Environment Variables (Production)

Ensure these are set securely:
- Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- Never commit `.env` to git
- Rotate tokens regularly
- Use different tokens per environment

## Monitoring

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "database": "healthy",
  "redis": "healthy"
}
```

### Logs

```bash
# Docker logs
docker-compose logs -f app

# Application logs (structured JSON)
# Logs include: conversation_id, user_id, model, tokens, errors
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection
docker-compose exec postgres psql -U clawbot -c "SELECT 1"
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping
```

### Bot Not Responding

1. Check bot tokens are correct in `.env`
2. Verify network connectivity
3. Check logs: `docker-compose logs app`
4. Ensure intents are enabled (Discord)

### GitHub Models API Errors

1. Verify token has correct permissions
2. Check rate limits
3. Ensure model names are correct: `gpt-4`, `claude-3-opus`, `llama-3-70b`

## Security Considerations

- ✅ All secrets in environment variables
- ✅ `.gitignore` excludes `.env` and sensitive files
- ✅ Pydantic validation on all inputs
- ✅ Rate limiting enabled
- ✅ Non-root Docker user
- ✅ PostgreSQL password authentication
- ✅ Redis protected with network isolation
- ✅ Health checks without exposing sensitive data

## Documentation

### Quick Start Guides
- **[SETUP.md](SETUP.md)** - Quick setup guide with step-by-step instructions
- **[README.md](README.md)** - This file - comprehensive project documentation

### Architecture & Design
- **[Architecture Design](docs/architecture.md)** - System architecture, layers, design decisions
- **[Component Diagram](docs/component-diagram.md)** - Visual component interactions with Mermaid
- **[Sequence Diagrams](docs/sequence-diagrams.md)** - Message flows and process sequences

### Configuration & Deployment
- **[Environment Setup](.env.example)** - Environment variable template
- **[Docker Compose](docker-compose.yml)** - Container orchestration configuration
- **[Database Migrations](src/database/migrations/)** - Alembic database migrations

### API Reference
- **[Health Endpoints](src/api/health.py)** - `/health` and `/ready` endpoints
- **[Webhook Endpoints](src/api/webhooks.py)** - Channel webhook handlers
- **[Database Models](src/database/models.py)** - SQLAlchemy ORM models

## License

MIT License - see LICENSE file

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## Support

- Documentation: This README + [docs/](docs/)
- Issues: GitHub Issues
- Security: Report via private disclosure

---

Built with ❤️ using Python 3.12, FastAPI, Discord.py, python-telegram-bot, and GitHub Models API
