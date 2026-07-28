# Environment Configuration for vLLM and Ollama

Add these environment variables to your `.env` file to enable vLLM and/or Ollama support.

## vLLM Configuration (Optional)

```bash
# vLLM server URL (default: http://localhost:8000/v1)
VLLM_BASE_URL=http://localhost:8000/v1

# vLLM API key (optional, depends on your server configuration)
# Leave empty if your vLLM server doesn't require authentication
VLLM_API_KEY=
```

## Ollama Configuration (Optional)

```bash
# Ollama server URL (default: http://localhost:11434/v1)
OLLAMA_BASE_URL=http://localhost:11434/v1
```

## Example Configurations

### Local Development (Ollama only)

```bash
# Existing
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx

# Add Ollama for local development
OLLAMA_BASE_URL=http://localhost:11434/v1
```

### Production with vLLM

```bash
# Existing
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIza...

# Add vLLM for self-hosted inference
VLLM_BASE_URL=http://vllm-server:8000/v1
VLLM_API_KEY=your-vllm-api-key
```

### Full Stack (All Backends)

```bash
# GitHub Models (default)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx

# Gemini (optional)
GEMINI_API_KEY=AIza...

# vLLM (optional)
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_API_KEY=

# Ollama (optional)
OLLAMA_BASE_URL=http://localhost:11434/v1
```

## Backend Selection

The AIRouter automatically selects the backend based on the model name:

- `gpt-4`, `claude-3-opus` → **GitHub Models** (requires `GITHUB_TOKEN`)
- `gemini-2.0-flash` → **Gemini** (requires `GEMINI_API_KEY`)
- `meta-llama/Llama-2-7b-chat-hf`, `vllm:mistral` → **vLLM** (requires `VLLM_BASE_URL`)
- `llama2`, `ollama:codellama` → **Ollama** (requires `OLLAMA_BASE_URL`)

## Verification

After configuring, verify the backends are enabled:

```bash
# Check logs during startup
python src/main.py

# Look for these log messages:
# ai_router_gemini_enabled
# ai_router_vllm_enabled base_url=http://localhost:8000/v1
# ai_router_ollama_enabled base_url=http://localhost:11434/v1
# ai_router_initialized backends=['github_models', 'gemini', 'vllm', 'ollama']
```

## Notes

- All backends are **optional** — only configure what you need
- vLLM and Ollama require their respective servers to be running
- Missing backends will cause runtime errors only when trying to use models routed to them
- See [vllm-ollama-integration.md](vllm-ollama-integration.md) for setup instructions
