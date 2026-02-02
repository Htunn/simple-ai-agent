"""Base channel adapter interface."""

from abc import ABC, abstractmethod
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class ChannelMessage:
    """Standardized message format across channels."""

    def __init__(
        self,
        content: str,
        user_id: str,
        username: Optional[str] = None,
        channel_type: str = "",
        raw_event: Optional[Any] = None,
    ):
        self.content = content
        self.user_id = user_id
        self.username = username
        self.channel_type = channel_type
        self.raw_event = raw_event

    def __repr__(self) -> str:
        return f"<ChannelMessage {self.channel_type}:{self.user_id}>"


class ChannelAdapter(ABC):
    """Abstract base class for channel adapters."""

    def __init__(self, channel_type: str):
        self.channel_type = channel_type
        self.message_handler = None
        logger.info("channel_adapter_initialized", channel_type=channel_type)

    def set_message_handler(self, handler: Any) -> None:
        """Set the message handler callback."""
        self.message_handler = handler

    @abstractmethod
    async def send_message(self, user_id: str, content: str) -> bool:
        """
        Send message to user.

        Args:
            user_id: User/chat identifier
            content: Message content

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the channel adapter."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel adapter."""
        pass

    @abstractmethod
    def parse_message(self, event: Any) -> Optional[ChannelMessage]:
        """
        Parse incoming message event.

        Args:
            event: Raw channel event

        Returns:
            ChannelMessage or None if invalid
        """
        pass

    async def handle_incoming_message(self, event: Any) -> None:
        """Handle incoming message event."""
        message = self.parse_message(event)
        if message and self.message_handler:
            await self.message_handler(message)
        elif not self.message_handler:
            logger.warning("no_message_handler", channel_type=self.channel_type)
