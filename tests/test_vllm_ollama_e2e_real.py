"""Real end-to-end tests with mock vLLM and Ollama servers.

Prerequisites:
    1. Start mock servers: python3 tests/mock_llm_servers.py
    2. Set environment variables:
       export VLLM_BASE_URL=http://localhost:8000/v1
       export OLLAMA_BASE_URL=http://localhost:11434/v1
    3. Run tests: pytest tests/test_vllm_ollama_e2e_real.py -v -s

This test suite verifies the actual HTTP communication with mock servers.
"""

import asyncio
import os

import httpx
import pytest

from src.ai.ai_router import AIRouter
from src.ai.ollama_client import OllamaClient
from src.ai.vllm_client import VLLMClient


# Mark all tests as integration tests (skip if servers not running)
pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
async def check_servers():
    """Check if mock servers are running."""
    vllm_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    
    async with httpx.AsyncClient() as client:
        try:
            vllm_response = await client.get(f"{vllm_url.rstrip('/v1')}/health")
            ollama_response = await client.get(f"{ollama_url.rstrip('/v1')}/health")
            
            if vllm_response.status_code != 200 or ollama_response.status_code != 200:
                pytest.skip("Mock servers not running. Start with: python3 tests/mock_llm_servers.py")
        except Exception as e:
            pytest.skip(f"Mock servers not reachable: {e}")


class TestVLLMClientReal:
    """Real integration tests for VLLMClient."""

    @pytest.mark.asyncio
    async def test_generate_response_real(self, check_servers):
        """Test real HTTP call to mock vLLM server."""
        client = VLLMClient(
            base_url="http://localhost:8000/v1",
            api_key="test-key",
        )
        
        messages = [
            {"role": "user", "content": "Hello, vLLM!"}
        ]
        
        content, tokens = await client.generate_response(
            messages=messages,
            model="meta-llama/Llama-2-7b-chat-hf",
            temperature=0.7,
            max_tokens=100,
        )
        
        print(f"\n[vLLM Response] {content}")
        print(f"[vLLM Tokens] {tokens}")
        
        assert "mock response from vLLM" in content
        assert "meta-llama/Llama-2-7b-chat-hf" in content
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_stream_response_real(self, check_servers):
        """Test real streaming HTTP call to mock vLLM server."""
        client = VLLMClient(
            base_url="http://localhost:8000/v1",
            api_key="test-key",
        )
        
        messages = [
            {"role": "user", "content": "Stream this response"}
        ]
        
        chunks = []
        async for chunk in client.stream_response(
            messages=messages,
            model="mistralai/Mistral-7B-Instruct-v0.2",
            temperature=0.7,
            max_tokens=100,
        ):
            print(f"[vLLM Chunk] {repr(chunk)}")
            chunks.append(chunk)
        
        full_response = "".join(chunks)
        print(f"\n[vLLM Full Stream] {full_response}")
        
        assert len(chunks) > 0
        assert "streaming" in full_response or "vLLM" in full_response


class TestOllamaClientReal:
    """Real integration tests for OllamaClient."""

    @pytest.mark.asyncio
    async def test_generate_response_real(self, check_servers):
        """Test real HTTP call to mock Ollama server."""
        client = OllamaClient(
            base_url="http://localhost:11434/v1",
        )
        
        messages = [
            {"role": "user", "content": "Hello, Ollama!"}
        ]
        
        content, tokens = await client.generate_response(
            messages=messages,
            model="llama2",
            temperature=0.7,
            max_tokens=100,
        )
        
        print(f"\n[Ollama Response] {content}")
        print(f"[Ollama Tokens] {tokens}")
        
        assert "mock response from Ollama" in content
        assert "llama2" in content
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_stream_response_real(self, check_servers):
        """Test real streaming HTTP call to mock Ollama server."""
        client = OllamaClient(
            base_url="http://localhost:11434/v1",
        )
        
        messages = [
            {"role": "user", "content": "Stream this response"}
        ]
        
        chunks = []
        async for chunk in client.stream_response(
            messages=messages,
            model="mistral",
            temperature=0.7,
            max_tokens=100,
        ):
            print(f"[Ollama Chunk] {repr(chunk)}")
            chunks.append(chunk)
        
        full_response = "".join(chunks)
        print(f"\n[Ollama Full Stream] {full_response}")
        
        assert len(chunks) > 0
        assert "Ollama" in full_response


class TestAIRouterReal:
    """Real integration tests for AIRouter."""

    @pytest.mark.asyncio
    async def test_router_vllm_real(self, check_servers):
        """Test router with real vLLM mock server."""
        # Set environment for testing
        os.environ["VLLM_BASE_URL"] = "http://localhost:8000/v1"
        os.environ["VLLM_API_KEY"] = "test-key"
        
        # Import after setting env vars
        from src.config import get_settings
        get_settings.cache_clear()  # Clear cache to reload settings
        
        router = AIRouter()
        
        messages = [
            {"role": "user", "content": "Test vLLM routing"}
        ]
        
        # Test with HuggingFace model path
        content, tokens = await router.generate_response(
            messages=messages,
            model="meta-llama/Llama-2-7b-chat-hf",
            temperature=0.7,
        )
        
        print(f"\n[Router→vLLM] {content}")
        
        assert "mock response from vLLM" in content
        assert tokens > 0
        
        # Test with vllm: prefix
        content2, tokens2 = await router.generate_response(
            messages=messages,
            model="vllm:mistral",
            temperature=0.7,
        )
        
        print(f"[Router→vLLM (prefix)] {content2}")
        assert "mock response from vLLM" in content2

    @pytest.mark.asyncio
    async def test_router_ollama_real(self, check_servers):
        """Test router with real Ollama mock server."""
        # Set environment for testing
        os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434/v1"
        
        # Import after setting env vars
        from src.config import get_settings
        get_settings.cache_clear()  # Clear cache to reload settings
        
        router = AIRouter()
        
        messages = [
            {"role": "user", "content": "Test Ollama routing"}
        ]
        
        # Test with simple model name
        content, tokens = await router.generate_response(
            messages=messages,
            model="llama2",
            temperature=0.7,
        )
        
        print(f"\n[Router→Ollama] {content}")
        
        assert "mock response from Ollama" in content
        assert tokens > 0
        
        # Test with ollama: prefix
        content2, tokens2 = await router.generate_response(
            messages=messages,
            model="ollama:codellama",
            temperature=0.7,
        )
        
        print(f"[Router→Ollama (prefix)] {content2}")
        assert "mock response from Ollama" in content2

    @pytest.mark.asyncio
    async def test_router_streaming_real(self, check_servers):
        """Test router streaming with real mock servers."""
        os.environ["VLLM_BASE_URL"] = "http://localhost:8000/v1"
        os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434/v1"
        
        from src.config import get_settings
        get_settings.cache_clear()
        
        router = AIRouter()
        
        messages = [{"role": "user", "content": "Stream test"}]
        
        # Test vLLM streaming
        print("\n[Router→vLLM Stream]")
        chunks_vllm = []
        async for chunk in router.stream_response(
            messages=messages,
            model="meta-llama/Llama-2-7b-chat-hf",
        ):
            print(f"  {repr(chunk)}", end="")
            chunks_vllm.append(chunk)
        print()
        
        assert len(chunks_vllm) > 0
        
        # Test Ollama streaming
        print("\n[Router→Ollama Stream]")
        chunks_ollama = []
        async for chunk in router.stream_response(
            messages=messages,
            model="llama2",
        ):
            print(f"  {repr(chunk)}", end="")
            chunks_ollama.append(chunk)
        print()
        
        assert len(chunks_ollama) > 0


if __name__ == "__main__":
    # Run with: python3 -m pytest tests/test_vllm_ollama_e2e_real.py -v -s
    pytest.main([__file__, "-v", "-s"])
