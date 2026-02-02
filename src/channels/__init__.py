"""Channels package."""

from src.channels.base import ChannelAdapter, ChannelMessage
from src.channels.discord_adapter import DiscordAdapter
from src.channels.router import MessageRouter, create_router
from src.channels.telegram_adapter import TelegramAdapter

__all__ = [
    "ChannelAdapter",
    "ChannelMessage",
    "DiscordAdapter",
    "TelegramAdapter",
    "MessageRouter",
    "create_router",
]
