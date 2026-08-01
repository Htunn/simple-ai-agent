"""Unit tests for vLLM and Ollama AI clients."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.ai.ollama_client import OllamaClient
from src.ai.vllm_client import VLLMClient


class TestVLLMClient:
    """Tests for VLLMClient."""

    @pytest.fixture
    def mock_openai(self):
        with patch("src.ai.vllm_client.AsyncOpenAI") as mock:
            yield mock

    @pytest.fixture
    def mock_settings(self):
        with patch("src.ai.vllm_client.get_settings") as mock:
            settings = MagicMock()
            settings.vllm_base_url = "http://localhost:8000/v1"
            settings.vllm_api_key = "test-key"
            mock.return_value = settings
            yield settings

    def test_init_with_base_url(self, mock_openai, mock_settings):
        """Test VLLMClient initialization with base URL."""
        client = VLLMClient(base_url="http://custom:8000/v1", api_key="custom-key")
        assert client.base_url == "http://custom:8000/v1"
        assert client.api_key == "custom-key"
        mock_openai.assert_called_once()

    def test_init_from_settings(self, mock_openai, mock_settings):
        """Test VLLMClient initialization from settings."""
        client = VLLMClient()
        assert client.base_url == "http://localhost:8000/v1"
        assert client.api_key == "test-key"

    def test_init_without_base_url_raises(self, mock_openai):
        """Test VLLMClient raises error without base URL."""
        with patch("src.ai.vllm_client.get_settings") as mock:
            settings = MagicMock()
            settings.vllm_base_url = None
            settings.vllm_api_key = None
            mock.return_value = settings
            
            with pytest.raises(ValueError, match="vLLM base URL not configured"):
                VLLMClient()

    @pytest.mark.asyncio
    async def test_generate_response(self, mock_openai, mock_settings):
        """Test generate_response method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.total_tokens = 100

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        client = VLLMClient()
        messages = [{"role": "user", "content": "Test"}]
        
        content, tokens = await client.generate_response(
            messages=messages,
            model="meta-llama/Llama-2-7b-chat-hf",
        )

        assert content == "Test response"
        assert tokens == 100
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_response(self, mock_openai, mock_settings):
        """Test stream_response method."""
        # Setup mock streaming response
        mock_chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content=" world"))]),
        ]

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        mock_openai.return_value = mock_client

        client = VLLMClient()
        messages = [{"role": "user", "content": "Test"}]

        chunks = []
        async for chunk in client.stream_response(messages=messages):
            chunks.append(chunk)

        assert chunks == ["Hello", " world"]

    def test_is_model_supported(self, mock_openai, mock_settings):
        """Test model support detection."""
        client = VLLMClient()
        
        assert client.is_model_supported("meta-llama/Llama-2-7b-chat-hf")
        assert client.is_model_supported("mistralai/Mistral-7B-Instruct-v0.2")
        assert client.is_model_supported("Qwen/Qwen-7B-Chat")
        assert not client.is_model_supported("gpt-4")

    def test_list_supported_models(self, mock_openai, mock_settings):
        """Test listing supported models."""
        client = VLLMClient()
        models = client.list_supported_models()
        
        assert len(models) > 0
        assert "meta-llama/Llama-2-7b-chat-hf" in models
        assert "mistralai/Mistral-7B-Instruct-v0.2" in models


class TestOllamaClient:
    """Tests for OllamaClient."""

    @pytest.fixture
    def mock_openai(self):
        with patch("src.ai.ollama_client.AsyncOpenAI") as mock:
            yield mock

    @pytest.fixture
    def mock_settings(self):
        with patch("src.ai.ollama_client.get_settings") as mock:
            settings = MagicMock()
            settings.ollama_base_url = "http://localhost:11434/v1"
            mock.return_value = settings
            yield settings

    def test_init_with_base_url(self, mock_openai, mock_settings):
        """Test OllamaClient initialization with base URL."""
        client = OllamaClient(base_url="http://custom:11434/v1")
        assert client.base_url == "http://custom:11434/v1"
        mock_openai.assert_called_once()

    def test_init_from_settings(self, mock_openai, mock_settings):
        """Test OllamaClient initialization from settings."""
        client = OllamaClient()
        assert client.base_url == "http://localhost:11434/v1"

    @pytest.mark.asyncio
    async def test_generate_response(self, mock_openai, mock_settings):
        """Test generate_response method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Ollama response"
        mock_response.usage.total_tokens = 50

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Test"}]
        
        content, tokens = await client.generate_response(
            messages=messages,
            model="llama2",
        )

        assert content == "Ollama response"
        assert tokens == 50

    @pytest.mark.asyncio
    async def test_generate_response_without_usage(self, mock_openai, mock_settings):
        """Test generate_response fallback token counting."""
        # Setup mock response without usage
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response with words"
        mock_response.usage = None

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Test"}]
        
        content, tokens = await client.generate_response(messages=messages)

        assert content == "Test response with words"
        assert tokens == 4  # Fallback word count

    def test_is_model_supported(self, mock_openai, mock_settings):
        """Test model support detection."""
        client = OllamaClient()
        
        assert client.is_model_supported("llama2")
        assert client.is_model_supported("llama2:7b")
        assert client.is_model_supported("mistral")
        assert client.is_model_supported("codellama")
        assert not client.is_model_supported("gpt-4")

    def test_list_supported_models(self, mock_openai, mock_settings):
        """Test listing supported models."""
        client = OllamaClient()
        models = client.list_supported_models()
        
        assert len(models) > 0
        assert "llama2" in models
        assert "mistral" in models
        assert "codellama" in models
