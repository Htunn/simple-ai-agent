# vLLM and Ollama Integration

This document explains how to use **vLLM** and **Ollama** as LLM providers in the AIOps Orchestrator, alongside the existing **GitHub Models** and **Gemini** backends.

---

## Overview

The AIOps Orchestrator now supports **four LLM backends**:

| Backend | Use Case | API Type | Model Examples |
|---------|----------|----------|----------------|
| **GitHub Models** | Default provider for GPT, Claude, Llama via GitHub | OpenAI-compatible | `gpt-4`, `claude-3.5-sonnet`, `llama-3.1-70b` |
| **Gemini** | Google's Gemini models | Google AI SDK | `gemini-2.0-flash`, `gemini-1.5-pro` |
| **vLLM** | Self-hosted high-performance inference | OpenAI-compatible | `meta-llama/Llama-2-7b-chat-hf`, `mistralai/Mistral-7B-Instruct-v0.2` |
| **Ollama** | Local LLM runner for laptops/servers | OpenAI-compatible | `llama2`, `mistral`, `codellama` |

---

## Architecture

### AI Router

The `AIRouter` class automatically routes requests to the correct backend based on **model name patterns**:

```python
from src.ai.ai_router import AIRouter

router = AIRouter()

# Routes to GitHub Models (default)
await router.generate_response(messages, model="gpt-4")

# Routes to Gemini
await router.generate_response(messages, model="gemini-2.0-flash")

# Routes to vLLM (contains "/" or starts with "vllm:")
await router.generate_response(messages, model="meta-llama/Llama-2-7b-chat-hf")
await router.generate_response(messages, model="vllm:mistral")

# Routes to Ollama (simple names or starts with "ollama:")
await router.generate_response(messages, model="llama2")
await router.generate_response(messages, model="ollama:codellama")
```

### Routing Rules (Priority Order)

1. **Gemini**: Model name starts with `"gemini-"` → `GeminiClient`
2. **vLLM**: Model name contains `"/"` or starts with `"vllm:"` → `VLLMClient`
3. **Ollama**: Model name matches Ollama patterns or starts with `"ollama:"` → `OllamaClient`
4. **GitHub Models**: Everything else → `GitHubModelsClient`

---

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Existing
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIza... # optional

# vLLM Configuration (optional)
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_API_KEY=  # optional, depends on your vLLM server

# Ollama Configuration (optional)
OLLAMA_BASE_URL=http://localhost:11434/v1
```

### Settings in `src/config.py`

The settings are automatically loaded from environment variables:

```python
class Settings(BaseSettings):
    # ...existing fields...
    
    # vLLM Configuration
    vllm_base_url: str | None = Field(
        default="http://localhost:8000/v1",
        description="vLLM server URL (e.g., http://localhost:8000/v1)",
    )
    vllm_api_key: str | None = Field(
        default=None,
        description="vLLM API key (optional, depends on server config)",
    )

    # Ollama Configuration
    ollama_base_url: str | None = Field(
        default="http://localhost:11434/v1",
        description="Ollama server URL",
    )
```

---

## Setting Up Backends

### 1. GitHub Models (Default)

✅ **Already configured** if you have `GITHUB_TOKEN` set.

No additional setup needed — this is the fallback backend.

### 2. Gemini (Optional)

Set `GEMINI_API_KEY` in your `.env`:

```bash
GEMINI_API_KEY=AIzaSyD...
```

### 3. vLLM (Optional)

#### Install and Run vLLM Server

```bash
# Install vLLM
pip install vllm

# Start vLLM server with a model
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --host 0.0.0.0 \
    --port 8000

# Or with more models and GPU settings
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 2
```

#### Configure AIOps

Add to `.env`:

```bash
VLLM_BASE_URL=http://localhost:8000/v1
```

### 4. Ollama (Optional)

#### Install and Run Ollama

```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models
ollama pull llama2
ollama pull mistral
ollama pull codellama

# Start Ollama server (usually auto-starts)
ollama serve  # Runs on http://localhost:11434
```

#### Configure AIOps

Add to `.env`:

```bash
OLLAMA_BASE_URL=http://localhost:11434/v1
```

---

## Usage Examples

### Using vLLM Models

```python
from src.ai.ai_router import AIRouter

router = AIRouter()

# Method 1: Full HuggingFace model path (auto-detects "/" for vLLM)
messages = [{"role": "user", "content": "Explain Kubernetes pods"}]
response, tokens = await router.generate_response(
    messages=messages,
    model="meta-llama/Llama-2-7b-chat-hf",
    temperature=0.7,
)

# Method 2: Explicit vllm: prefix
response, tokens = await router.generate_response(
    messages=messages,
    model="vllm:mistral",
    temperature=0.7,
)

# Streaming
async for chunk in router.stream_response(messages, model="meta-llama/Llama-2-7b-chat-hf"):
    print(chunk, end="", flush=True)
```

### Using Ollama Models

```python
# Method 1: Simple model name (auto-detects Ollama patterns)
response, tokens = await router.generate_response(
    messages=[{"role": "user", "content": "Write a Python function"}],
    model="llama2",
)

# Method 2: Explicit ollama: prefix
response, tokens = await router.generate_response(
    messages=[{"role": "user", "content": "Debug this code"}],
    model="ollama:codellama",
)

# With model tags
response, tokens = await router.generate_response(
    messages=messages,
    model="llama2:13b",  # Use 13B variant
)
```

### Checking Available Models

```python
router = AIRouter()

# List all models from all backends
models = router.list_supported_models()
# Returns: ["gpt-4", "claude-3.5-sonnet", "gemini-2.0-flash", 
#           "vllm:meta-llama/Llama-2-7b-chat-hf", "ollama:llama2", ...]

# Check if a specific model is supported
if router.is_model_supported("llama2"):
    print("Ollama is configured!")
```

---

## Direct Client Usage

If you need to use a specific client directly (bypassing the router):

### VLLMClient

```python
from src.ai.vllm_client import VLLMClient

client = VLLMClient(
    base_url="http://localhost:8000/v1",
    api_key="optional-key",  # or None
)

response, tokens = await client.generate_response(
    messages=[{"role": "user", "content": "Hello"}],
    model="meta-llama/Llama-2-7b-chat-hf",
    temperature=0.7,
    max_tokens=2000,
)
```

### OllamaClient

```python
from src.ai.ollama_client import OllamaClient

client = OllamaClient(
    base_url="http://localhost:11434/v1",
)

response, tokens = await client.generate_response(
    messages=[{"role": "user", "content": "Hello"}],
    model="llama2",
    temperature=0.7,
    max_tokens=2000,
)
```

---

## Model Support

### vLLM Supported Models

The `VLLMClient` supports any model compatible with vLLM. Common examples:

- **Llama**: `meta-llama/Llama-2-7b-chat-hf`, `meta-llama/Meta-Llama-3-8B-Instruct`, `meta-llama/Meta-Llama-3-70B-Instruct`
- **Mistral**: `mistralai/Mistral-7B-Instruct-v0.2`, `mistralai/Mixtral-8x7B-Instruct-v0.1`
- **Qwen**: `Qwen/Qwen-7B-Chat`, `Qwen/Qwen-14B-Chat`
- **DeepSeek**: `deepseek-ai/deepseek-coder-6.7b-instruct`
- **Phi**: `microsoft/phi-2`

Detection: Model name contains `llama`, `mistral`, `qwen`, `phi`, `vicuna`, `yi`, `mixtral`, `deepseek`, or `codellama`.

### Ollama Supported Models

The `OllamaClient` supports models installed via `ollama pull`. Common examples:

- **Llama**: `llama2`, `llama2:7b`, `llama2:13b`, `llama2:70b`, `llama3:8b`, `llama3:70b`
- **Mistral**: `mistral`, `mistral:7b`, `mixtral:8x7b`
- **Code**: `codellama`, `codellama:7b`, `codellama:13b`, `deepseek-coder:6.7b`
- **Other**: `phi`, `phi:2.7b`, `neural-chat`, `vicuna`, `qwen:7b`, `solar:10.7b`, `yi:6b`

Detection: Model name matches `llama2`, `llama3`, `mistral`, `mixtral`, `codellama`, `phi`, `neural-chat`, `vicuna`, `qwen`, `deepseek-coder`, `orca-mini`, `solar`, or `yi`.

---

## Error Handling

### Backend Not Configured

If you try to use a backend that's not configured:

```python
# vLLM not configured (VLLM_BASE_URL not set)
await router.generate_response(messages, model="meta-llama/Llama-2-7b-chat-hf")
# Raises: RuntimeError: Model 'meta-llama/Llama-2-7b-chat-hf' requires vLLM but VLLM_BASE_URL is not set.

# Ollama not configured (OLLAMA_BASE_URL not set)
await router.generate_response(messages, model="llama2")
# Raises: RuntimeError: Model 'llama2' requires Ollama but OLLAMA_BASE_URL is not set.
```

### Connection Errors

If the backend server is not running:

```python
# vLLM server not running
await router.generate_response(messages, model="vllm:mistral")
# Raises: openai.APIConnectionError or similar
```

**Solution**: Start the backend server and ensure the URL is correct.

---

## Testing

### Run Unit Tests

```bash
# Test vLLM and Ollama clients
pytest tests/unit/test_vllm_ollama_clients.py -v

# Test all AI components
pytest tests/unit/test_*.py -k ai -v
```

### Manual Testing

```python
# Test script
import asyncio
from src.ai.ai_router import AIRouter

async def test_backends():
    router = AIRouter()
    
    test_models = [
        "gpt-4",                              # GitHub Models
        "gemini-2.0-flash",                   # Gemini (if configured)
        "meta-llama/Llama-2-7b-chat-hf",      # vLLM (if running)
        "llama2",                             # Ollama (if running)
    ]
    
    for model in test_models:
        try:
            if router.is_model_supported(model):
                response, tokens = await router.generate_response(
                    messages=[{"role": "user", "content": "Say hello"}],
                    model=model,
                    max_tokens=50,
                )
                print(f"✅ {model}: {response[:50]}... ({tokens} tokens)")
        except Exception as e:
            print(f"❌ {model}: {e}")

if __name__ == "__main__":
    asyncio.run(test_backends())
```

---

## Performance Comparison

| Backend | Latency | Throughput | Cost | Best For |
|---------|---------|------------|------|----------|
| **GitHub Models** | ~1-3s | Moderate | Pay-per-token | Production, variety of models |
| **Gemini** | ~1-2s | High | Pay-per-token | Google ecosystem, multimodal |
| **vLLM** | ~50-500ms | Very High | Self-hosted | High-throughput, low-latency |
| **Ollama** | ~100-1000ms | Low-Moderate | Free (local) | Development, offline, privacy |

---

## Production Deployment

### Docker Compose with vLLM

```yaml
version: "3.8"
services:
  vllm:
    image: vllm/vllm-openai:latest
    ports:
      - "8000:8000"
    environment:
      - MODEL=meta-llama/Llama-2-7b-chat-hf
    volumes:
      - vllm-cache:/root/.cache/huggingface
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  aiops-orchestrator:
    build: .
    environment:
      - VLLM_BASE_URL=http://vllm:8000/v1
    depends_on:
      - vllm
```

### Kubernetes with Ollama

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        volumeMounts:
        - name: ollama-data
          mountPath: /root/.ollama
---
apiVersion: v1
kind: Service
metadata:
  name: ollama
spec:
  ports:
  - port: 11434
```

---

## Troubleshooting

### vLLM Issues

**Problem**: `Connection refused` error  
**Solution**: Ensure vLLM server is running: `curl http://localhost:8000/v1/models`

**Problem**: Model not found  
**Solution**: Check the model is loaded: `curl http://localhost:8000/v1/models`

**Problem**: Out of memory  
**Solution**: Use smaller model or enable tensor parallelism: `--tensor-parallel-size 2`

### Ollama Issues

**Problem**: `Connection refused` error  
**Solution**: Start Ollama: `ollama serve`

**Problem**: Model not found  
**Solution**: Pull the model: `ollama pull llama2`

**Problem**: Slow responses  
**Solution**: Ollama caches models in memory after first use. Subsequent requests are faster.

---

## Migration Guide

### From GitHub Models to vLLM

```python
# Before
response, tokens = await router.generate_response(
    messages=messages,
    model="llama-3.1-70b",  # GitHub Models
)

# After (assuming you have Llama model in vLLM)
response, tokens = await router.generate_response(
    messages=messages,
    model="meta-llama/Meta-Llama-3-70B-Instruct",  # vLLM
)
```

### From Gemini to Ollama

```python
# Before
response, tokens = await router.generate_response(
    messages=messages,
    model="gemini-2.0-flash",
)

# After
response, tokens = await router.generate_response(
    messages=messages,
    model="llama3:8b",  # Ollama
)
```

---

## Summary

✅ **Four LLM backends** supported: GitHub Models, Gemini, vLLM, Ollama  
✅ **Automatic routing** based on model name patterns  
✅ **OpenAI-compatible** API for vLLM and Ollama  
✅ **Fully tested** with comprehensive unit tests  
✅ **Optional configuration** — only enable what you need  
✅ **Production-ready** with retry logic, error handling, and logging

For questions or issues, see the [main README](../README.md) or [architecture docs](architecture.md).
