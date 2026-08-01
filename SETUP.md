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

1. **GitHub Token** (Required for GitHub Models):
   - Go to: https://github.com/settings/tokens
   - Create fine-grained token with Models API access
   - Add to `.env`: `GITHUB_TOKEN=ghp_your_token_here`

2. **Gemini API Key** (Optional, for Google Gemini):
   - Go to: https://aistudio.google.com/app/apikey
   - Create API key
   - Add to `.env`: `GEMINI_API_KEY=AIza...`

3. **vLLM Server** (Optional, for self-hosted inference):
   - Set up vLLM server (see [vLLM docs](https://docs.vllm.ai))
   - Add to `.env`: `VLLM_BASE_URL=http://localhost:8000/v1`
   - Optionally: `VLLM_API_KEY=your-key`

4. **Ollama Server** (Optional, for local development):
   - Install Ollama from https://ollama.ai
   - Pull a model: `ollama pull llama2`
   - Add to `.env`: `OLLAMA_BASE_URL=http://localhost:11434/v1`

5. **Telegram Token** (Optional):
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

### Telegram:
1. Find your bot on Telegram
2. Send `/start`
3. Chat with the bot

## Supported Models

### GitHub Models (Default)
- `gpt-4o` - GPT-4o (default)
- `gpt-4` - GPT-4
- `claude-3-opus` - Claude 3 Opus
- `claude-3-sonnet` - Claude 3 Sonnet
- `llama-3-70b` - Llama 3 70B
- `llama-3-8b` - Llama 3 8B

### Google Gemini
- `gemini-2.5-pro` - Gemini 2.5 Pro
- `gemini-2.5-flash` - Gemini 2.5 Flash
- `gemini-2.0-flash` - Gemini 2.0 Flash
- `gemini-1.5-pro` - Gemini 1.5 Pro
- `gemini-1.5-flash` - Gemini 1.5 Flash

### vLLM (Self-Hosted)
- `meta-llama/Llama-2-7b-chat-hf` - Llama 2 7B
- `meta-llama/Meta-Llama-3-8B-Instruct` - Llama 3 8B
- `mistralai/Mistral-7B-Instruct-v0.2` - Mistral 7B
- `Qwen/Qwen-7B-Chat` - Qwen 7B
- Or use prefix: `vllm:mistral`

### Ollama (Local)
- `llama2`, `llama2:7b`, `llama2:13b` - Llama 2
- `llama3:8b`, `llama3:70b` - Llama 3
- `mistral`, `mistral:7b` - Mistral
- `codellama`, `codellama:13b` - Code Llama
- Or use prefix: `ollama:codellama`

Change model: `/model gemini-2.5-flash` or `/model llama2` or `/model gpt-4o`

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

## Next Steps

- Read [README.md](README.md) for full documentation
- Set up monitoring and logging
- Configure rate limits
- Add custom prompts
- Extend with more channels (WhatsApp support can be added)
