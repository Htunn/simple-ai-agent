"""Message router for channel adapters."""

import asyncio
from typing import Optional

import structlog

from src.channels.base import ChannelAdapter, ChannelMessage
from src.channels.discord_adapter import DiscordAdapter
from src.channels.telegram_adapter import TelegramAdapter

logger = structlog.get_logger()


class MessageRouter:
    """Routes messages between channels and message handler."""

    def __init__(self):
        self.adapters: dict[str, ChannelAdapter] = {}
        self.message_handler = None
        self.tasks: list[asyncio.Task] = []

    def register_adapter(self, adapter: ChannelAdapter) -> None:
        """Register a channel adapter."""
        self.adapters[adapter.channel_type] = adapter
        adapter.set_message_handler(self._route_message)
        logger.info("adapter_registered", channel_type=adapter.channel_type)

    def set_message_handler(self, handler: any) -> None:
        """Set the global message handler."""
        self.message_handler = handler
        logger.info("message_handler_set")

    async def _route_message(self, message: ChannelMessage) -> None:
        """Route message to handler."""
        if self.message_handler:
            await self.message_handler(message)
        else:
            logger.warning("no_message_handler_configured")

    async def send_message(
        self, channel_type: str, user_id: str, content: str
    ) -> bool:
        """Send message through appropriate channel adapter."""
        adapter = self.adapters.get(channel_type)
        if not adapter:
            logger.error("adapter_not_found", channel_type=channel_type)
            return False

        return await adapter.send_message(user_id, content)

    async def start_all(self) -> None:
        """Start all registered adapters."""
        for channel_type, adapter in self.adapters.items():
            logger.info("starting_adapter", channel_type=channel_type)
            task = asyncio.create_task(adapter.start())
            self.tasks.append(task)

    async def stop_all(self) -> None:
        """Stop all adapters."""
        for channel_type, adapter in self.adapters.items():
            logger.info("stopping_adapter", channel_type=channel_type)
            await adapter.stop()

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        self.tasks.clear()

    def get_adapter(self, channel_type: str) -> Optional[ChannelAdapter]:
        """Get adapter by channel type."""
        return self.adapters.get(channel_type)


# Factory function to create and configure router
def create_router() -> MessageRouter:
    """Create message router with available adapters."""
    router = MessageRouter()

    # Register Discord adapter if token available
    try:
        discord_adapter = DiscordAdapter()
        router.register_adapter(discord_adapter)
    except Exception as e:
        logger.warning("discord_adapter_not_registered", error=str(e))

    # Register Telegram adapter if token available
    try:
        telegram_adapter = TelegramAdapter()
        router.register_adapter(telegram_adapter)
    except Exception as e:
        logger.warning("telegram_adapter_not_registered", error=str(e))

    return router
