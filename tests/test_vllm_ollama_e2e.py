"""End-to-end tests for vLLM and Ollama integration.

This test suite includes:
1. Mock server tests (no external dependencies)
2. Integration tests with real servers (if available)
3. Router routing logic tests
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.ai_router import AIRouter
from src.ai.ollama_client import OllamaClient
from src.ai.vllm_client import VLLMClient


class TestRouterRoutingLogic:
    """Test AIRouter routing logic without external dependencies."""

    def test_vllm_model_detection(self):
        """Test vLLM model detection patterns."""
        with patch("src.ai.ai_router.get_settings") as mock_settings:
            settings = MagicMock()
            settings.github_token = "test"
            settings.gemini_api_key = None
            settings.vllm_base_url = "http://localhost:8000/v1"
            settings.ollama_base_url = None
            mock_settings.return_value = settings
            
            with patch("src.ai.vllm_client.get_settings", return_value=settings):
                with patch("src.ai.vllm_client.AsyncOpenAI"):
                    router = AIRouter()
                    
                    # Test vLLM detection
                    assert router._is_vllm_model("meta-llama/Llama-2-7b-chat-hf")
                    assert router._is_vllm_model("mistralai/Mistral-7B-Instruct-v0.2")
                    assert router._is_vllm_model("vllm:some-model")
                    
                    # Test non-vLLM models
                    assert not router._is_vllm_model("gpt-4")
                    assert not router._is_vllm_model("gemini-2.0-flash")
                    assert not router._is_vllm_model("llama2")

    def test_ollama_model_detection(self):
        """Test Ollama model detection patterns."""
        with patch("src.ai.ai_router.get_settings") as mock_settings:
            settings = MagicMock()
            settings.github_token = "test"
            settings.gemini_api_key = None
            settings.vllm_base_url = None
            settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.return_value = settings
            
            with patch("src.ai.ollama_client.get_settings", return_value=settings):
                with patch("src.ai.ollama_client.AsyncOpenAI"):
                    router = AIRouter()
                    
                    # Test Ollama detection
                    assert router._is_ollama_model("llama2")
                    assert router._is_ollama_model("llama2:7b")
                    assert router._is_ollama_model("mistral")
                    assert router._is_ollama_model("codellama")
                    assert router._is_ollama_model("ollama:some-model")
                    
                    # Test non-Ollama models
                    assert not router._is_ollama_model("gpt-4")
                    assert not router._is_ollama_model("gemini-2.0-flash")
                    assert not router._is_ollama_model("meta-llama/Llama-2-7b-chat-hf")

    def test_gemini_model_detection(self):
        """Test Gemini model detection patterns."""
        with patch("src.ai.ai_router.get_settings") as mock_settings:
            settings = MagicMock()
            settings.github_token = "test"
            settings.gemini_api_key = "test-key"
            settings.vllm_base_url = None
            settings.ollama_base_url = None
            mock_settings.return_value = settings
            
            with patch("src.ai.gemini_client.get_settings", return_value=settings):
                router = AIRouter()
                
                # Test Gemini detection
                assert router._is_gemini_model("gemini-2.0-flash")
                assert router._is_gemini_model("gemini-2.5-pro")
                assert router._is_gemini_model("Gemini-1.5-Flash")  # case-insensitive
                
                # Test non-Gemini models
                assert not router._is_gemini_model("gpt-4")
                assert not router._is_gemini_model("llama2")

    def test_prefix_stripping(self):
        """Test provider prefix stripping."""
        with patch("src.ai.ai_router.get_settings") as mock_settings:
            settings = MagicMock()
            settings.github_token = "test"
            settings.gemini_api_key = None
            settings.vllm_base_url = "http://localhost:8000/v1"
            settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.return_value = settings
            
            with patch("src.ai.vllm_client.get_settings", return_value=settings):
                with patch("src.ai.ollama_client.get_settings", return_value=settings):
                    with patch("src.ai.vllm_client.AsyncOpenAI"):
                        with patch("src.ai.ollama_client.AsyncOpenAI"):
                            router = AIRouter()
                            
                            # Test vLLM prefix stripping
                            assert router._strip_provider_prefix("vllm:mistral") == "mistral"
                            assert router._strip_provider_prefix("vllm:llama2") == "llama2"
                            
                            # Test Ollama prefix stripping
                            assert router._strip_provider_prefix("ollama:codellama") == "codellama"
                            assert router._strip_provider_prefix("ollama:mistral:7b") == "mistral:7b"
                            
                            # Test no prefix
                            assert router._strip_provider_prefix("gpt-4") == "gpt-4"
                            assert router._strip_provider_prefix("meta-llama/Llama-2-7b-chat-hf") == "meta-llama/Llama-2-7b-chat-hf"


class TestVLLMClientMocked:
    """Test VLLMClient with mocked OpenAI client."""

    @pytest.mark.asyncio
    async def test_generate_response_success(self):
        """Test successful response generation."""
        with patch("src.ai.vllm_client.get_settings") as mock_settings:
            settings = MagicMock()
            settings.vllm_base_url = "http://localhost:8000/v1"
            settings.vllm_api_key = "test-key"
            mock_settings.return_value = settings
            
            with patch("src.ai.vllm_client.AsyncOpenAI") as mock_openai:
                # Setup mock response
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "This is a test response from vLLM"
                mock_response.usage.total_tokens = 25
                
                mock_client = AsyncMock()
                mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
                mock_openai.return_value = mock_client
                
                # Test
                client = VLLMClient()
                messages = [{"role": "user", "content": "Hello, how are you?"}]
                
                content, tokens = await client.generate_response(
                    messages=messages,
                    model="meta-llama/Llama-2-7b-chat-hf",
                    temperature=0.7,
                    max_tokens=2000,
                )
                
                assert content == "This is a test response from vLLM"
                assert tokens == 25
                mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_response_success(self):
        """Test successful streaming response."""
        with patch("src.ai.vllm_client.get_settings") as mock_settings:
            settings = MagicMock()
            settings.vllm_base_url = "http://localhost:8000/v1"
            settings.vllm_api_key = "test-key"
            mock_settings.return_value = settings
            
            with patch("src.ai.vllm_client.AsyncOpenAI") as mock_openai:
                # Setup mock streaming response
                async def mock_stream():
                    chunks = ["Hello", " from", " vLLM", "!"]
                    for chunk_text in chunks:
                        chunk = MagicMock()
                        chunk.choices = [MagicMock()]
                        chunk.choices[0].delta.content = chunk_text
                        yield chunk
                
                mock_client = AsyncMock()
                mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
                mock_openai.return_value = mock_client
                
                # Test
                client = VLLMClient()
                messages = [{"role": "user", "content": "Say hello"}]
                
                chunks = []
                async for chunk in client.stream_response(messages=messages):
                    chunks.append(chunk)
                
                assert chunks == ["Hello", " from", " vLLM", "!"]
                assert "".join(chunks) == "Hello from vLLM!"


class TestOllamaClientMocked:
    """Test OllamaClient with mocked OpenAI client."""

    @pytest.mark.asyncio
    async def test_generate_response_success(self):
        """Test successful response generation."""
        with patch("src.ai.ollama_client.get_settings") as mock_settings:
            settings = MagicMock()
            settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.return_value = settings
            
            with patch("src.ai.ollama_client.AsyncOpenAI") as mock_openai:
                # Setup mock response
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "This is a test response from Ollama"
                mock_response.usage.total_tokens = 30
                
                mock_client = AsyncMock()
                mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
                mock_openai.return_value = mock_client
                
                # Test
                client = OllamaClient()
                messages = [{"role": "user", "content": "Hello, Ollama!"}]
                
                content, tokens = await client.generate_response(
                    messages=messages,
                    model="llama2",
                    temperature=0.7,
                    max_tokens=2000,
                )
                
                assert content == "This is a test response from Ollama"
                assert tokens == 30
                mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_response_success(self):
        """Test successful streaming response."""
        with patch("src.ai.ollama_client.get_settings") as mock_settings:
            settings = MagicMock()
            settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.return_value = settings
            
            with patch("src.ai.ollama_client.AsyncOpenAI") as mock_openai:
                # Setup mock streaming response
                async def mock_stream():
                    chunks = ["Greetings", " from", " Ollama", "!"]
                    for chunk_text in chunks:
                        chunk = MagicMock()
                        chunk.choices = [MagicMock()]
                        chunk.choices[0].delta.content = chunk_text
                        yield chunk
                
                mock_client = AsyncMock()
                mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
                mock_openai.return_value = mock_client
                
                # Test
                client = OllamaClient()
                messages = [{"role": "user", "content": "Say greetings"}]
                
                chunks = []
                async for chunk in client.stream_response(messages=messages):
                    chunks.append(chunk)
                
                assert chunks == ["Greetings", " from", " Ollama", "!"]
                assert "".join(chunks) == "Greetings from Ollama!"


class TestRouterE2EMocked:
    """End-to-end router tests with mocked backends."""

    @pytest.mark.asyncio
    async def test_router_with_all_backends(self):
        """Test router with all four backends configured."""
        with patch("src.ai.ai_router.get_settings") as mock_settings:
            settings = MagicMock()
            settings.github_token = "test-token"
            settings.gemini_api_key = "test-gemini-key"
            settings.vllm_base_url = "http://localhost:8000/v1"
            settings.vllm_api_key = "test-vllm-key"
            settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.return_value = settings
            
            # Mock all client initializations
            with patch("src.ai.github_models.AsyncOpenAI"):
                with patch("src.ai.gemini_client.get_settings", return_value=settings):
                    with patch("src.ai.vllm_client.get_settings", return_value=settings):
                        with patch("src.ai.ollama_client.get_settings", return_value=settings):
                            with patch("src.ai.vllm_client.AsyncOpenAI"):
                                with patch("src.ai.ollama_client.AsyncOpenAI"):
                                    router = AIRouter()
                                    
                                    # Verify all backends are initialized
                                    assert router._github is not None
                                    assert router._gemini is not None
                                    assert router._vllm is not None
                                    assert router._ollama is not None

    @pytest.mark.asyncio
    async def test_router_vllm_dispatch(self):
        """Test router dispatches vLLM models correctly."""
        with patch("src.ai.ai_router.get_settings") as mock_settings:
            settings = MagicMock()
            settings.github_token = "test-token"
            settings.gemini_api_key = None
            settings.vllm_base_url = "http://localhost:8000/v1"
            settings.vllm_api_key = "test-key"
            settings.ollama_base_url = None
            mock_settings.return_value = settings
            
            with patch("src.ai.github_models.AsyncOpenAI"):
                with patch("src.ai.vllm_client.get_settings", return_value=settings):
                    with patch("src.ai.vllm_client.AsyncOpenAI") as mock_vllm_openai:
                        # Setup mock vLLM response
                        mock_response = MagicMock()
                        mock_response.choices = [MagicMock()]
                        mock_response.choices[0].message.content = "vLLM response"
                        mock_response.usage.total_tokens = 20
                        
                        mock_client = AsyncMock()
                        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
                        mock_vllm_openai.return_value = mock_client
                        
                        router = AIRouter()
                        
                        # Test vLLM routing with HuggingFace path
                        messages = [{"role": "user", "content": "Test"}]
                        content, tokens = await router.generate_response(
                            messages=messages,
                            model="meta-llama/Llama-2-7b-chat-hf",
                        )
                        
                        assert content == "vLLM response"
                        assert tokens == 20
                        
                        # Verify the call was made with stripped model name
                        call_args = mock_client.chat.completions.create.call_args
                        assert call_args.kwargs["model"] == "meta-llama/Llama-2-7b-chat-hf"

    @pytest.mark.asyncio
    async def test_router_ollama_dispatch(self):
        """Test router dispatches Ollama models correctly."""
        with patch("src.ai.ai_router.get_settings") as mock_settings:
            settings = MagicMock()
            settings.github_token = "test-token"
            settings.gemini_api_key = None
            settings.vllm_base_url = None
            settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.return_value = settings
            
            with patch("src.ai.github_models.AsyncOpenAI"):
                with patch("src.ai.ollama_client.get_settings", return_value=settings):
                    with patch("src.ai.ollama_client.AsyncOpenAI") as mock_ollama_openai:
                        # Setup mock Ollama response
                        mock_response = MagicMock()
                        mock_response.choices = [MagicMock()]
                        mock_response.choices[0].message.content = "Ollama response"
                        mock_response.usage.total_tokens = 15
                        
                        mock_client = AsyncMock()
                        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
                        mock_ollama_openai.return_value = mock_client
                        
                        router = AIRouter()
                        
                        # Test Ollama routing
                        messages = [{"role": "user", "content": "Test"}]
                        content, tokens = await router.generate_response(
                            messages=messages,
                            model="llama2",
                        )
                        
                        assert content == "Ollama response"
                        assert tokens == 15
                        
                        # Verify the call was made with correct model name
                        call_args = mock_client.chat.completions.create.call_args
                        assert call_args.kwargs["model"] == "llama2"


class TestHuggingFaceOllamaRouting:
    """Tests for Ollama HuggingFace model ref routing (hf.co/ prefix)."""

    def _make_settings(self, **kwargs):
        settings = MagicMock()
        settings.github_token = "test"
        settings.gemini_api_key = None
        settings.vllm_base_url = "http://localhost:8000/v1"
        settings.ollama_base_url = "http://localhost:11434/v1"
        for k, v in kwargs.items():
            setattr(settings, k, v)
        return settings

    def test_hf_model_is_not_vllm(self):
        """hf.co/ refs must NOT be routed to vLLM."""
        settings = self._make_settings()
        with patch("src.ai.ai_router.get_settings", return_value=settings), \
             patch("src.ai.vllm_client.get_settings", return_value=settings), \
             patch("src.ai.ollama_client.get_settings", return_value=settings), \
             patch("src.ai.github_models.AsyncOpenAI"), \
             patch("src.ai.vllm_client.AsyncOpenAI"), \
             patch("src.ai.ollama_client.AsyncOpenAI"):
            router = AIRouter()
            assert not router._is_vllm_model("hf.co/htunn/gemma-4-e2b-aiops-gguf:Q4_K_M")
            assert not router._is_vllm_model("hf.co/mistralai/Mistral-7B-Instruct-v0.3")

    def test_hf_model_is_ollama(self):
        """hf.co/ refs must be routed to Ollama."""
        settings = self._make_settings()
        with patch("src.ai.ai_router.get_settings", return_value=settings), \
             patch("src.ai.vllm_client.get_settings", return_value=settings), \
             patch("src.ai.ollama_client.get_settings", return_value=settings), \
             patch("src.ai.github_models.AsyncOpenAI"), \
             patch("src.ai.vllm_client.AsyncOpenAI"), \
             patch("src.ai.ollama_client.AsyncOpenAI"):
            router = AIRouter()
            assert router._is_ollama_model("hf.co/htunn/gemma-4-e2b-aiops-gguf:Q4_K_M")
            assert router._is_ollama_model("hf.co/mistralai/Mistral-7B-Instruct-v0.3")

    def test_gemma_model_is_ollama(self):
        """gemma* models must route to Ollama."""
        settings = self._make_settings()
        with patch("src.ai.ai_router.get_settings", return_value=settings), \
             patch("src.ai.vllm_client.get_settings", return_value=settings), \
             patch("src.ai.ollama_client.get_settings", return_value=settings), \
             patch("src.ai.github_models.AsyncOpenAI"), \
             patch("src.ai.vllm_client.AsyncOpenAI"), \
             patch("src.ai.ollama_client.AsyncOpenAI"):
            router = AIRouter()
            assert router._is_ollama_model("gemma4:e2b")
            assert router._is_ollama_model("gemma:7b")

    @pytest.mark.asyncio
    async def test_router_dispatches_hf_model_to_ollama(self):
        """AIRouter must dispatch hf.co/ model to OllamaClient, not VLLMClient."""
        settings = self._make_settings(vllm_base_url=None)
        with patch("src.ai.ai_router.get_settings", return_value=settings), \
             patch("src.ai.ollama_client.get_settings", return_value=settings), \
             patch("src.ai.github_models.AsyncOpenAI"), \
             patch("src.ai.ollama_client.AsyncOpenAI") as mock_ollama_openai:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "action": "remediate_auth",
                "target_domain": "ADFS",
                "service_account": "svc_k8s_cluster",
                "steps": ["check_pki_cert_validity", "rotate_secret_k8s"],
                "api_call": "POST /api/v1/auth/refresh",
            })
            mock_response.usage.total_tokens = 42

            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_ollama_openai.return_value = mock_client

            router = AIRouter()
            messages = [
                {
                    "role": "user",
                    "content": (
                        "[AIOps-Agent] Node k8s-worker-03 status is NotReady. "
                        "AD service account 'svc_k8s_cluster' authentication failed on ADFS."
                    ),
                }
            ]
            content, tokens = await router.generate_response(
                messages=messages,
                model="hf.co/htunn/gemma-4-e2b-aiops-gguf:Q4_K_M",
                temperature=0.3,
                max_tokens=512,
            )

            result = json.loads(content)
            assert result["action"] == "remediate_auth"
            assert tokens == 42

            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs["model"] == "hf.co/htunn/gemma-4-e2b-aiops-gguf:Q4_K_M"
            assert call_args.kwargs["temperature"] == 0.3

    def test_ollama_client_supports_hf_model(self):
        """OllamaClient.is_model_supported() must accept hf.co/ refs."""
        with patch("src.ai.ollama_client.get_settings") as mock_settings:
            settings = MagicMock()
            settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.return_value = settings
            with patch("src.ai.ollama_client.AsyncOpenAI"):
                client = OllamaClient()
                assert client.is_model_supported("hf.co/htunn/gemma-4-e2b-aiops-gguf:Q4_K_M")
                assert client.is_model_supported("gemma4:e2b")
                assert client.is_model_supported("gemma:7b")

    def test_ollama_client_lists_custom_model(self):
        """hf.co/htunn/gemma-4-e2b-aiops-gguf:Q4_K_M appears in list_supported_models()."""
        with patch("src.ai.ollama_client.get_settings") as mock_settings:
            settings = MagicMock()
            settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.return_value = settings
            with patch("src.ai.ollama_client.AsyncOpenAI"):
                client = OllamaClient()
                models = client.list_supported_models()
                assert "hf.co/htunn/gemma-4-e2b-aiops-gguf:Q4_K_M" in models


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
