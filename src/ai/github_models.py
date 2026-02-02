"""GitHub Models API client."""

from typing import Any, Optional

import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class GitHubModelsClient:
    """Client for GitHub Models API using OpenAI SDK."""

    # Supported models on GitHub Models
    SUPPORTED_MODELS = {
        "gpt-4": "gpt-4",
        "gpt-4-turbo": "gpt-4-turbo",
        "claude-3-opus": "claude-3-opus-20240229",
        "claude-3-sonnet": "claude-3-sonnet-20240229",
        "llama-3-70b": "llama-3-70b-instruct",
        "llama-3-8b": "llama-3-8b-instruct",
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize GitHub Models client."""
        self.api_key = api_key or settings.github_token
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://models.github.com/v1",
        )
        logger.info("github_models_client_initialized")

    def get_model_name(self, model_alias: str) -> str:
        """Get full model name from alias."""
        return self.SUPPORTED_MODELS.get(model_alias, model_alias)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def generate_response(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> tuple[str, int]:
        """
        Generate AI response from messages.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model alias (gpt-4, claude-3-opus, llama-3-70b)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the API

        Returns:
            Tuple of (response_content, token_count)
        """
        model_name = self.get_model_name(model)

        logger.debug(
            "generating_response",
            model=model_name,
            message_count=len(messages),
            temperature=temperature,
        )

        try:
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0

            logger.info(
                "response_generated",
                model=model_name,
                tokens=tokens,
                content_length=len(content),
            )

            return content, tokens

        except Exception as e:
            logger.error(
                "generation_failed",
                model=model_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def stream_response(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ):
        """
        Stream AI response from messages.

        Args:
            messages: List of message dictionaries
            model: Model alias
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Yields:
            Response chunks
        """
        model_name = self.get_model_name(model)

        logger.debug("streaming_response", model=model_name, message_count=len(messages))

        try:
            stream = await self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(
                "streaming_failed",
                model=model_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def is_model_supported(self, model: str) -> bool:
        """Check if model is supported."""
        return model in self.SUPPORTED_MODELS

    def list_supported_models(self) -> list[str]:
        """List all supported model aliases."""
        return list(self.SUPPORTED_MODELS.keys())
