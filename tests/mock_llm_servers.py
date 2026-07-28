#!/usr/bin/env python3
"""
Mock vLLM and Ollama servers for end-to-end testing.

This script starts mock servers that simulate vLLM and Ollama OpenAI-compatible APIs,
allowing you to test the AIOps vLLM and Ollama clients without installing the actual servers.

Usage:
    # Start both mock servers
    python3 tests/mock_llm_servers.py

    # In another terminal, run the E2E tests
    pytest tests/test_vllm_ollama_e2e_real.py -v
"""

import asyncio
import json
import sys
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn


# Mock vLLM Server
vllm_app = FastAPI(title="Mock vLLM Server")


@vllm_app.post("/v1/chat/completions")
async def vllm_chat_completions(request: dict[str, Any]):
    """Mock vLLM chat completions endpoint."""
    messages = request.get("messages", [])
    model = request.get("model", "unknown")
    stream = request.get("stream", False)
    
    print(f"[vLLM] Received request for model: {model}, stream: {stream}")
    
    if not stream:
        # Non-streaming response
        response = {
            "id": "vllm-mock-response",
            "object": "chat.completion",
            "created": 1234567890,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"This is a mock response from vLLM for model {model}. User said: {messages[-1].get('content', '')}",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }
        return response
    else:
        # Streaming response
        async def generate():
            chunks = [
                "This ",
                "is ",
                "a ",
                "streaming ",
                "response ",
                "from ",
                f"vLLM ({model}). ",
            ]
            for chunk_text in chunks:
                chunk = {
                    "id": "vllm-stream-chunk",
                    "object": "chat.completion.chunk",
                    "created": 1234567890,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": chunk_text},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                await asyncio.sleep(0.1)
            
            # Final chunk
            final_chunk = {
                "id": "vllm-stream-chunk",
                "object": "chat.completion.chunk",
                "created": 1234567890,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")


@vllm_app.get("/v1/models")
async def vllm_list_models():
    """Mock vLLM models endpoint."""
    return {
        "object": "list",
        "data": [
            {"id": "meta-llama/Llama-2-7b-chat-hf", "object": "model"},
            {"id": "mistralai/Mistral-7B-Instruct-v0.2", "object": "model"},
            {"id": "Qwen/Qwen-7B-Chat", "object": "model"},
        ],
    }


@vllm_app.get("/health")
async def vllm_health():
    """Health check endpoint."""
    return {"status": "ok", "backend": "mock-vllm"}


# Mock Ollama Server
ollama_app = FastAPI(title="Mock Ollama Server")


@ollama_app.post("/v1/chat/completions")
async def ollama_chat_completions(request: dict[str, Any]):
    """Mock Ollama chat completions endpoint."""
    messages = request.get("messages", [])
    model = request.get("model", "unknown")
    stream = request.get("stream", False)
    
    print(f"[Ollama] Received request for model: {model}, stream: {stream}")
    
    if not stream:
        # Non-streaming response
        response = {
            "id": "ollama-mock-response",
            "object": "chat.completion",
            "created": 1234567890,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"This is a mock response from Ollama for model {model}. User said: {messages[-1].get('content', '')}",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 8,
                "completion_tokens": 15,
                "total_tokens": 23,
            },
        }
        return response
    else:
        # Streaming response
        async def generate():
            chunks = [
                "Hello ",
                "from ",
                "Ollama ",
                f"({model})! ",
            ]
            for chunk_text in chunks:
                chunk = {
                    "id": "ollama-stream-chunk",
                    "object": "chat.completion.chunk",
                    "created": 1234567890,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": chunk_text},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                await asyncio.sleep(0.1)
            
            # Final chunk
            final_chunk = {
                "id": "ollama-stream-chunk",
                "object": "chat.completion.chunk",
                "created": 1234567890,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")


@ollama_app.get("/v1/models")
async def ollama_list_models():
    """Mock Ollama models endpoint."""
    return {
        "object": "list",
        "data": [
            {"id": "llama2", "object": "model"},
            {"id": "llama2:7b", "object": "model"},
            {"id": "mistral", "object": "model"},
            {"id": "codellama", "object": "model"},
        ],
    }


@ollama_app.get("/health")
async def ollama_health():
    """Health check endpoint."""
    return {"status": "ok", "backend": "mock-ollama"}


async def run_servers():
    """Run both mock servers concurrently."""
    print("🚀 Starting Mock LLM Servers...")
    print("=" * 60)
    print("vLLM Mock Server:   http://localhost:8000")
    print("Ollama Mock Server: http://localhost:11434")
    print("=" * 60)
    print("\nEndpoints:")
    print("  vLLM:   POST http://localhost:8000/v1/chat/completions")
    print("  vLLM:   GET  http://localhost:8000/v1/models")
    print("  Ollama: POST http://localhost:11434/v1/chat/completions")
    print("  Ollama: GET  http://localhost:11434/v1/models")
    print("\n✅ Servers are ready! Press Ctrl+C to stop.")
    print("\nEnvironment variables to set:")
    print("  export VLLM_BASE_URL=http://localhost:8000/v1")
    print("  export OLLAMA_BASE_URL=http://localhost:11434/v1")
    print()
    
    # Run both servers
    config_vllm = uvicorn.Config(vllm_app, host="0.0.0.0", port=8000, log_level="info")
    config_ollama = uvicorn.Config(ollama_app, host="0.0.0.0", port=11434, log_level="info")
    
    server_vllm = uvicorn.Server(config_vllm)
    server_ollama = uvicorn.Server(config_ollama)
    
    await asyncio.gather(
        server_vllm.serve(),
        server_ollama.serve(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(run_servers())
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down mock servers...")
        sys.exit(0)
