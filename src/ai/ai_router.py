"""AI client router — dispatches to the right backend by model prefix.

Routing rules (checked in order):
  1. Model name starts with "gemini-"  → GeminiClient
  2. Everything else                   → GitHubModelsClient (GitHub Models / Azure AI Inference)

This lets callers use any model alias (e.g. "gpt-4", "gemini-2.0-flash")
without caring which backend handles it.
"""

from collections.abc import AsyncGenerator
from typing import Any

import structlog

from src.ai.base_client import BaseAIClient
from src.ai.gemini_client import GeminiClient
from src.ai.github_models import GitHubModelsClient
from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class AIRouter(BaseAIClient):
    """Routes AI calls to the appropriate backend based on model prefix."""

    def __init__(self) -> None:
        self._github = GitHubModelsClient()

        # GeminiClient is optional — only instantiate if the key is configured
        self._gemini: GeminiClient | None = None
        if settings.gemini_api_key:
            try:
                self._gemini = GeminiClient()
                logger.info("ai_router_gemini_enabled")
            except Exception as e:
                logger.warning("ai_router_gemini_init_failed", error=str(e))
        else:
            logger.info("ai_router_gemini_disabled", reason="GEMINI_API_KEY not set")

        logger.info(
            "ai_router_initialized",
            backends=["github_models"] + (["gemini"] if self._gemini else []),
        )

    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------

    def _is_gemini_model(self, model: str) -> bool:
        return model.lower().startswith("gemini")

    def _backend_for(self, model: str) -> BaseAIClient:
        """Return the correct backend client for *model*."""
        if self._is_gemini_model(model):
            if self._gemini is None:
                raise RuntimeError(
                    f"Model '{model}' requires Gemini but GEMINI_API_KEY is not set."
                )
            return self._gemini
        return self._github

    # ------------------------------------------------------------------
    # BaseAIClient interface
    # ------------------------------------------------------------------

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> tuple[str, int]:
        backend = self._backend_for(model)
        logger.debug("ai_router_dispatch", model=model, backend=type(backend).__name__)
        return await backend.generate_response(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def stream_response(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        backend = self._backend_for(model)
        return backend.stream_response(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def is_model_supported(self, model: str) -> bool:
        if self._is_gemini_model(model):
            return self._gemini is not None and self._gemini.is_model_supported(model)
        return self._github.is_model_supported(model)

    def list_supported_models(self) -> list[str]:
        models = self._github.list_supported_models()
        if self._gemini:
            models = models + self._gemini.list_supported_models()
        return models
