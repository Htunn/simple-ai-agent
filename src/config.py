"""Configuration settings for the application."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # GitHub Models API
    github_token: str = Field(..., description="GitHub fine-grained personal access token")

    # Discord Bot
    discord_token: str | None = Field(None, description="Discord bot token")

    # Telegram Bot
    telegram_token: str | None = Field(None, description="Telegram bot token")

    # Slack Bot
    slack_bot_token: str | None = Field(None, description="Slack bot token")
    slack_signing_secret: str | None = Field(None, description="Slack signing secret for webhook verification")

    # MCP Server Configuration
    mcp_server_url: str | None = Field(
        default=None,
        description="MCP (Model Context Protocol) server URL for custom business logic",
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://clawbot:clawbot_password@localhost:5432/clawbot",
        description="PostgreSQL database URL",
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # Application Settings
    log_level: str = Field(default="INFO", description="Logging level")
    environment: Literal["development", "production"] = Field(
        default="development", description="Environment"
    )

    # FastAPI Server
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")

    # Session Configuration
    session_ttl_seconds: int = Field(
        default=3600, description="Session TTL in seconds (1 hour)"
    )

    # Default AI Model
    default_model: str = Field(
        default="gpt-4",
        description="Default AI model (gpt-4, claude-3-opus, llama-3-70b)",
    )

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
