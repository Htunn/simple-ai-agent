"""Channels package."""

from src.channels.base import ChannelAdapter, ChannelMessage
from src.channels.router import MessageRouter, create_router
from src.channels.slack_adapter import SlackAdapter
from src.channels.telegram_adapter import TelegramAdapter

__all__ = [
    "ChannelAdapter",
    "ChannelMessage",
    "SlackAdapter",
    "TelegramAdapter",
    "MessageRouter",
    "create_router",
]
