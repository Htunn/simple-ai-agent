"""AI package — multi-backend LLM support."""

from src.ai.ai_router import AIRouter
from src.ai.base_client import BaseAIClient
from src.ai.context_builder import ContextBuilder
from src.ai.gemini_client import GeminiClient
from src.ai.github_models import GitHubModelsClient
from src.ai.model_selector import ModelSelector
from src.ai.prompt_manager import PromptManager

__all__ = [
    "AIRouter",
    "BaseAIClient",
    "GeminiClient",
    "GitHubModelsClient",
    "ModelSelector",
    "ContextBuilder",
    "PromptManager",
]
