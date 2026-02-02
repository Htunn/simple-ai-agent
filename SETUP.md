# Quick Setup Guide

## Step 1: Install Dependencies

```bash
# Activate virtual environment (already exists)
source .venv/bin/activate

# Install production dependencies
pip install -r requirements.txt

# Optional: Install development dependencies
pip install -r requirements-dev.txt
```

## Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

**Required Configuration:**

1. **GitHub Token** (Required):
   - Go to: https://github.com/settings/tokens
   - Create fine-grained token with Models API access
   - Add to `.env`: `GITHUB_TOKEN=ghp_your_token_here`

2. **Discord Token** (Optional):
   - Go to: https://discord.com/developers/applications
   - Create application → Add Bot
   - Enable "Message Content Intent"
   - Add to `.env`: `DISCORD_TOKEN=your_token_here`

3. **Telegram Token** (Optional):
   - Message @BotFather on Telegram
   - Create bot with `/newbot`
   - Add to `.env`: `TELEGRAM_TOKEN=your_token_here`

## Step 3: Choose Deployment Method

### Option A: Docker Compose (Recommended)

```bash
# Start all services (PostgreSQL, Redis, App)
docker-compose up -d

# View logs
docker-compose logs -f app

# Check status
curl http://localhost:8000/health
```

### Option B: Local Development

```bash
# Start only database services
docker-compose up -d postgres redis

# Update .env for local URLs
# DATABASE_URL=postgresql+asyncpg://aiagent:aiagent_password@localhost:5432/aiagent
# REDIS_URL=redis://localhost:6379/0

# Run database migrations
python scripts/init_db.py

# Start application
python -m uvicorn src.main:app --reload
```

## Step 4: Test the Bot

### Discord:
1. Invite bot to your server
2. Send a message: "Hello!"
3. Try commands: `/help`, `/model gpt-4`, `/status`

### Telegram:
1. Find your bot on Telegram
2. Send `/start`
3. Chat with the bot

## Supported Models

- `gpt-4` - GPT-4 (default)
- `gpt-4-turbo` - GPT-4 Turbo
- `claude-3-opus` - Claude 3 Opus
- `claude-3-sonnet` - Claude 3 Sonnet
- `llama-3-70b` - Llama 3 70B
- `llama-3-8b` - Llama 3 8B

Change model: `/model claude-3-opus`

## Troubleshooting

### "Module not found" errors:
```bash
pip install -r requirements.txt
```

### Database connection failed:
```bash
docker-compose up -d postgres
python scripts/init_db.py
```

### Bot not responding:
1. Check tokens in `.env`
2. View logs: `docker-compose logs app`
3. Verify intents enabled (Discord)

## Next Steps

- Read [README.md](README.md) for full documentation
- Set up monitoring and logging
- Configure rate limits
- Add custom prompts
- Extend with more channels (WhatsApp support can be added)
