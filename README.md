# � Simple AI Agent

A production-ready multi-channel AI agent with Discord, Telegram, and Slack support, featuring GitHub Models API integration (GPT-4, Claude Opus, Llama 3) and extensible MCP (Model Context Protocol) for custom business logic.

## Features

### Channel & AI Capabilities
- 🤖 **Multi-Channel Support**: Discord, Telegram, and Slack bots
- 🧠 **Multiple AI Models**: GPT-4, Claude 3 Opus, Llama 3 via GitHub Models
- 🎯 **Model Preferences**: Per-user and per-channel model selection

### Kubernetes Management
- ☸️ **Kubernetes Integration**: Full cluster management with natural language queries and status filtering
- 🗣️ **Natural Language K8s**: "show me error pods in production" - intelligent query parsing
- 🔍 **Smart Filtering**: Automatic status filtering (error, running, pending, all)

### Security & Infrastructure
- 🔐 **Security Scanning**: Port scanning, certificate analysis, WAF detection, mTLS checks
- 🛡️ **Natural Language Security**: "check certificate for example.com", "detect waf on mysite.com"
- 🌐 **8 Security Tools**: Full integration with SimplePortChecker MCP server

### MCP (Model Context Protocol)
- 🔌 **Multi-Transport MCP**: stdio (Kubernetes) + SSE (cloud services)
- 🔧 **MCP Registry**: Extensible tool registry for custom integrations
- 🚀 **Cloud MCP Servers**: HTTP/SSE transport for remote MCP servers

### Data & Performance
- 💾 **Hybrid Database Architecture**: PostgreSQL for persistence, Redis for caching
- ⚡ **Sub-millisecond Session Access**: Redis-backed session management with TTL
- 📊 **Complete Message History**: Full conversation tracking with token usage
- 🗄️ **ACID Guarantees**: PostgreSQL for reliable data storage

### Production Ready
- 🐳 **Docker Ready**: Multi-stage builds with kubectl support
- ⚙️ **Resource Management**: CPU/memory limits, health checks, logging rotation
- 🔒 **Security Hardening**: Non-root containers, no-new-privileges, OCI labels
- 📈 **Monitoring**: Health endpoints, PostgreSQL/Redis metrics, debug tools (pgAdmin, redis-commander)
- 🛠️ **Extensible Architecture**: Easy to add new channels and integrations

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
- `SLACK_BOT_TOKEN`: Slack bot token (optional)
- `SLACK_SIGNING_SECRET`: Slack signing secret (optional)
- `MCP_SERVER_URL`: MCP server URL for custom business logic (optional)

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

**For Group Usage:**
- **Option 1 (Recommended)**: Disable Privacy Mode:
  - Send `/mybots` to @BotFather
  - Select your bot → Bot Settings → Group Privacy → Turn OFF
  - This allows the bot to see all messages and commands in groups
  - Use commands directly: `/k8s pods pos-order4u`
  - Use natural language: "check pos-order4u namespace pods"
  
- **Option 2**: Mention the bot (Privacy Mode ON):
  - Keep privacy mode ON (default)
  - Bot only responds when mentioned or replied to
  - For commands: `@your_bot_name /k8s pods pos-order4u`
  - For natural language: `@your_bot_name check pos-order4u namespace pods`
  - The bot automatically strips mentions for processing

**Note**: In private chats, the bot always receives all messages regardless of privacy mode.

### 6. Slack Bot Setup (Optional)

1. Go to https://api.slack.com/apps
2. Create "New App" → "From scratch"
3. Add OAuth scopes: `app_mentions:read`, `chat:write`, `im:history`, `users:read`
4. Install app to workspace
5. Copy "Bot User OAuth Token" to `.env` as `SLACK_BOT_TOKEN`
6. Copy "Signing Secret" to `.env` as `SLACK_SIGNING_SECRET`
7. Enable Event Subscriptions with webhook URL: `https://your-domain.com/api/webhook/slack`
8. Subscribe to events: `app_mention`, `message.im`

**See [docs/slack-setup.md](docs/slack-setup.md) for detailed instructions.**

### 7. MCP Integration (Enabled by Default)

**NEW**: Multi-transport MCP (Model Context Protocol) integration with support for both stdio (local) and SSE (cloud) servers!

**What's Included:**
- ✅ **Kubernetes MCP** - stdio transport with 13 kubectl tools
- ✅ **SimplePortChecker MCP** - SSE transport with 8 security scanning tools
- ✅ Automatic process management (starts/stops with app)
- ✅ JSON-RPC 2.0 protocol support
- ✅ Compatible with Claude Desktop, LobeHub, and other MCP clients

**Configuration:** `.mcp-config.json` (already included)

```json
{
  "mcpServers": {
    "kubernetes": {
      "type": "stdio",
      "command": "python3",
      "args": ["scripts/mcp_server.py"],
      "description": "Kubernetes management tools via kubectl"
    },
    "simplePortChecker": {
      "type": "sse",
      "url": "https://mcp.simpleportchecker.com/mcp",
      "description": "Security scanning and port checking tools"
    }
  }
}
```

**Available MCP Tools:**

*Kubernetes (stdio):*
- `k8s_get_pods`, `k8s_get_nodes`, `k8s_get_deployments`
- `k8s_get_services`, `k8s_get_namespaces`, `k8s_get_logs`
- `k8s_scale_deployment`, `k8s_describe_resource`, `k8s_get_events`
- `k8s_top_pods`, `k8s_top_nodes`, `k8s_get_contexts`, `k8s_current_context`

*Security Scanning (SSE):*
- `scan_ports`, `analyze_certificate`, `detect_l7_protection`
- `check_mtls`, `check_security_headers`, `scan_owasp_vulnerabilities`
- `full_security_scan`, `check_hybrid_identity`

**Benefits:**
- 🔒 **Secure**: Credentials isolated, non-root containers
- 🚀 **Fast**: stdio for local, SSE for cloud services
- 🔌 **Standard**: Follows official MCP specification
- 🌐 **Cloud-Ready**: HTTP/SSE transport for remote servers
- 🛠️ **Extensible**: Easy to add custom servers

**Architecture:**
- **stdio**: Direct subprocess communication for local tools (Kubernetes)
- **SSE**: Server-Sent Events for cloud services (SimplePortChecker)
- **Tool Registry**: Automatic routing to the correct transport
- **Multi-Message Support**: SSE response parsing with request ID matching

For detailed architecture and protocol flow, see **[Sequence Diagrams](docs/sequence-diagrams.md)** (Diagram 7-10).

### 8. Run with Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Check health
curl http://localhost:8000/health
```

### 9. Run Locally (Development)

**Option A: Using Helper Scripts (Recommended)**

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Update .env to use local database URLs
# DATABASE_URL=postgresql+asyncpg://aiagent:aiagent_password@localhost:5432/aiagent
# REDIS_URL=redis://localhost:6379/0

# Start server (database is initialized automatically on startup)
./scripts/start_server.sh

# Optional: Custom host/port
./scripts/start_server.sh 0.0.0.0 8000 --reload

# Stop server
./scripts/stop_server.sh
```

**Option B: Manual Start**

```bash
# Activate virtual environment
source .venv/bin/activate

# Optional: Run migrations manually (not required, auto-runs on startup)
# python scripts/init_db.py

# Start application (database initializes automatically)
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Usage

### Available Commands

Users can interact with the bot using these commands:

- `/help` - Show available commands
- `/model <name>` - Set AI model (gpt-4, claude-3-opus, llama-3-70b)
- `/reset` - Start a new conversation
- `/status` - Show current model and conversation statistics
- `/k8s <command>` - Kubernetes cluster management (see below)

### Kubernetes Commands

Manage your Kubernetes clusters directly from chat with both commands and natural language:

**Command Syntax:**
- `/k8s help` - Show all Kubernetes commands
- `/k8s pods [namespace]` - List pods
- `/k8s logs <pod> [namespace]` - Get pod logs
- `/k8s deployments [namespace]` - List deployments
- `/k8s scale <deployment> <replicas> [namespace]` - Scale deployment
- `/k8s nodes` - List cluster nodes
- `/k8s services [namespace]` - List services
- `/k8s namespaces` - List all namespaces
- `/k8s events [namespace]` - Show recent events
- `/k8s contexts` - List available contexts
- `/k8s describe <type> <name> [namespace]` - Describe resource
- `/k8s top pods|nodes` - Show resource usage

**Natural Language Queries:**
The bot understands natural language with intelligent intent detection:
```
"show me pods in production namespace"
"show me error pods in pos-order4u"
"list failed pods"
"show unhealthy pods in staging"
"get logs from pod nginx-abc123"
"scale api-server deployment to 3 replicas"
"what are my nodes"
"show pending pods"
```

**Status Filters:**
- **error/failed/crash** - Show pods with issues (CrashLoopBackOff, Error, ImagePullBackOff)
- **unhealthy/not ready** - Show pods where containers aren't ready
- **pending** - Show pods in Pending or ContainerCreating state
- **running/healthy** - Show only healthy running pods

**Example Usage:**
```
User: /k8s pods production
Bot: 📦 Pods in namespace production:

     ✅ **api-server-abc123**
        Status: Running | Ready: 2/2 | Restarts: 0 | Age: 5d
     
     ✅ **nginx-xyz789**
        Status: Running | Ready: 1/1 | Restarts: 1 | Age: 12d

User: show me error pods in production
Bot: 📦 Pods with issues in namespace production:

     ❌ **worker-def456**
        Status: CrashLoopBackOff | Ready: 0/1 | Restarts: 10 | Age: 2h

User: /k8s scale api-server 5 production
Bot: ⚖️ Scaling deployment api-server to 5 replicas in namespace production:
     deployment.apps/api-server scaled

User: /k8s logs nginx-abc123 production
Bot: 📜 Logs from pod nginx-abc123 in namespace production:
     [Shows last 50 lines of logs]
```

**Output Formatting:**
- ✅ Running pods with healthy status
- ⚠️ Running pods with warnings
- ❌ Failed/crashing pods
- ⏳ Pending/creating pods
- ✔️ Completed jobs
- Compact format optimized for chat (no horizontal scrolling)
- Status information at a glance

**Requirements:**
- `kubectl` installed and configured on the server
- Valid kubeconfig with cluster access
- Appropriate RBAC permissions for cluster operations

For full Kubernetes integration documentation, see **[Kubernetes Integration Guide](docs/kubernetes-integration.md)**.

### Security Scanning

Perform comprehensive security scans on any domain or IP using natural language:

**Available Security Tools:**
- **Port Scanning** - Scan open ports on a target
- **Certificate Analysis** - Check SSL/TLS certificates
- **WAF Detection** - Detect Web Application Firewalls (Cloudflare, AWS WAF, etc.)
- **mTLS Verification** - Check mutual TLS support
- **Full Security Scan** - Comprehensive security assessment

**Natural Language Queries:**
```
"is port 443 open on example.com"
"check certificate for example.com"
"detect waf on mysite.com"
"scan ports on example.com"
"check mtls on api.example.com"
"full security scan on example.com"
```

**Example Usage:**
```
User: check certificate for github.com
Bot: 🔐 Certificate Analysis for github.com:
     
     ✅ Valid Certificate
     - Issuer: DigiCert Inc
     - Valid Until: 2024-12-15
     - SANs: github.com, www.github.com
     - Protocol: TLSv1.3

User: detect waf on example.com
Bot: 🛡️ L7 Protection Detection for example.com:
     
     Detected: Cloudflare
     - Type: CDN/WAF
     - Headers: cf-ray, cf-cache-status
     - Protection Level: Medium

User: is port 443 open on example.com
Bot: 🔍 Port Scan Results for example.com:
     
     ✅ Port 443: OPEN (https)
     - Service: HTTPS
     - Response Time: 45ms
```

**Features:**
- 🚀 Real-time scanning via cloud MCP server
- 🔐 SSL/TLS certificate validation and expiration checking
- 🛡️ WAF/CDN detection (Cloudflare, AWS, Azure, etc.)
- 📊 Comprehensive security reports
- ⚡ Sub-second response times

**Note:** Security scanning uses the SimplePortChecker MCP server via SSE transport. Some advanced tools (OWASP scanning, security headers check) may have limited availability.

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
┌──────────────────────────────────────────────────────────────┐
│           Discord / Telegram / Slack                          │
└───────────────────────────┬──────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Channel       │
                    │  Adapters      │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │  Message       │◄─────────┐
                    │  Handler       │          │
                    └───────┬────────┘          │
                            │                   │
                 ┌──────────┴──────────┐   ┌────▼────────────┐
                 │                     │   │  Kubernetes     │
          ┌──────▼──────┐      ┌──────▼───▼───┐ Handler    │
          │  Session    │      │   GitHub      │            │
          │  Manager    │      │   Models      ├────────────┤
          │  (Redis)    │      │   Client      │    MCP     │
          └──────┬──────┘      └──────┬────────│   Client   │
                 │                     │        └─────┬──────┘
                 │             ┌───────▼────────┐     │
                 │             │  Context       │     │
                 │             │  Builder       │     │
                 │             └───────┬────────┘     │
                 │                     │              │
          ┌──────▼─────────────────────▼──────┐      │
          │         PostgreSQL                 │      │
          │  (Users, Conversations, Messages)  │      │
          └────────────────────────────────────┘      │
                                                       │
          ┌────────────────────────────────────────┐  │
          │    MCP Server / Kubernetes API        │◄─┘
          │  - Custom Tools                        │
          │  - Kubernetes Resources                │
          │  - Helm Releases                       │
          │  - Business APIs                       │
          └────────────────────────────────────────┘
```

### Detailed Documentation

For comprehensive architecture documentation, see:
- **[Architecture Design](docs/architecture.md)** - Layered architecture, design decisions, scalability
- **[Component Diagram](docs/component-diagram.md)** - System components and interactions
- **[Sequence Diagrams](docs/sequence-diagrams.md)** - Message flow, commands, startup sequences, MCP multi-transport
- **[Database Architecture](docs/database-architecture.md)** - PostgreSQL & Redis use cases, schema design, performance optimization

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
│   │   ├── slack_adapter.py     # Slack integration
│   │   └── router.py            # Message routing
│   ├── database/                # Database layer
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── postgres.py          # PostgreSQL connection
│   │   ├── redis.py             # Redis connection
│   │   ├── repositories/        # Data access layer
│   │   └── migrations/          # Alembic migrations
│   ├── services/                # Business logic
│   │   ├── message_handler.py   # Message processing with K8s integration
│   │   ├── session_manager.py   # Session management
│   │   ├── mcp_client.py        # MCP server integration
│   │   ├── mcp_registry.py      # MCP tools registry
│   │   └── kubernetes_handler.py # Kubernetes operations handler
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

### Production Setup

The project includes production-ready configurations with resource management, security hardening, and monitoring.

**Key Features:**
- 🐳 Multi-stage Docker builds with kubectl support
- ⚙️ Resource limits (CPU, memory) for all services
- 🔒 Security hardening (non-root, no-new-privileges)
- 📊 Health checks with proper timing for MCP initialization
- 📝 Structured logging with rotation
- 🔧 Debug tools (pgAdmin, redis-commander) on separate profile

**Configuration Files:**
1. **Dockerfile** - Optimized multi-stage build with OCI labels
2. **docker-compose.yml** - Orchestration with PostgreSQL tuning
3. **.env.production.example** - Comprehensive environment template

### Quick Production Deploy

```bash
# 1. Copy production environment template
cp .env.production.example .env.production

# 2. Edit with your credentials and settings
nano .env.production

# 3. Build with version metadata
export VERSION=$(git describe --tags --always)
export VCS_REF=$(git rev-parse --short HEAD)
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

docker-compose build --build-arg VERSION=$VERSION \
                      --build-arg VCS_REF=$VCS_REF \
                      --build-arg BUILD_DATE=$BUILD_DATE

# 4. Start production stack
docker-compose --env-file .env.production up -d

# 5. Verify health
curl http://localhost:8000/health
```

### Docker Production

```bash
# Build production image
docker build -t simple-ai-agent:latest .

# Run with docker-compose
docker-compose up -d

# Scale (if needed)
docker-compose up -d --scale app=3

# Start with debug tools (pgAdmin, redis-commander)
docker-compose --profile debug up -d
```

### Production Checklist

**Before Deployment:**
- [ ] Set all bot tokens (Discord, Telegram, Slack)
- [ ] Configure database credentials
- [ ] Set secure PostgreSQL password
- [ ] Set Redis password
- [ ] Configure kubeconfig mount (if using Kubernetes MCP)
- [ ] Review resource limits in docker-compose.yml
- [ ] Enable SSL/TLS for database connections
- [ ] Set up backup strategy for PostgreSQL
- [ ] Configure log aggregation

**After Deployment:**
- [ ] Verify `/health` endpoint returns healthy
- [ ] Test bot responses in each channel
- [ ] Test Kubernetes commands (if enabled)
- [ ] Test security scanning commands
- [ ] Monitor resource usage
- [ ] Set up alerts for errors
- [ ] Review logs for warnings

### Environment Variables (Production)

The `.env.production.example` file provides a comprehensive template with 11 sections:

1. **Bot Tokens** - Discord, Telegram, Slack credentials
2. **Database** - PostgreSQL connection and performance tuning
3. **Redis** - Cache configuration and persistence
4. **Application** - Log level, workers, timeouts
5. **AI Models** - GitHub Models API configuration
6. **Performance** - Rate limiting, connection pooling
7. **Resource Limits** - CPU, memory for containers
8. **Debug Tools** - pgAdmin, redis-commander (optional)
9. **Build Metadata** - Version, VCS ref, build date
10. **Network** - Subnet configuration
11. **Data Persistence** - Volume driver options

**Security Best Practices:**
- Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- Never commit `.env` or `.env.production` to git
- Rotate tokens regularly
- Use different tokens per environment
- Enable SSL/TLS for all external connections
- Use read-only kubeconfig for Kubernetes MCP

### Resource Requirements

**Minimum (Development):**
- CPU: 1 core
- Memory: 2GB (app: 1GB, postgres: 512MB, redis: 256MB)
- Disk: 10GB

**Recommended (Production):**
- CPU: 4 cores (app: 2, postgres: 1, redis: 0.5)
- Memory: 4GB (app: 2GB, postgres: 1GB, redis: 512MB)
- Disk: 50GB with SSD for database

**Scaling Considerations:**
- Add more app replicas for higher concurrency
- Use PostgreSQL read replicas for analytics
- Use Redis Cluster for distributed caching
- Consider message queue (RabbitMQ) for very high loads

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
docker-compose exec postgres psql -U aiagent -c "SELECT 1"
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

### Integration Guides
- **[Slack Setup](docs/slack-setup.md)** - Complete Slack bot setup and configuration guide
- **[MCP Integration](docs/mcp-integration.md)** - Model Context Protocol integration for custom business logic
- **[MCP Registry](docs/mcp-registry.md)** - MCP tools registry for Kubernetes and custom integrations
- **[Kubernetes Integration](docs/kubernetes-integration.md)** - Complete guide with natural language queries and status filtering

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
