"""Slack channel adapter."""

from typing import Any, Optional

import structlog
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from src.channels.base import ChannelAdapter, ChannelMessage
from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class SlackAdapter(ChannelAdapter):
    """Slack bot adapter using Events API."""

    def __init__(self, token: Optional[str] = None):
        super().__init__("slack")
        self.token = token or settings.slack_bot_token
        self.client: Optional[AsyncWebClient] = None
        self._bot_user_id: Optional[str] = None

    async def _initialize_client(self) -> None:
        """Initialize Slack client and get bot user ID."""
        if not self.token:
            logger.warning("slack_token_not_set")
            return

        self.client = AsyncWebClient(token=self.token)

        try:
            # Get bot user ID to ignore own messages
            response = await self.client.auth_test()
            self._bot_user_id = response["user_id"]
            logger.info("slack_client_initialized", bot_user_id=self._bot_user_id)
        except SlackApiError as e:
            logger.error("slack_auth_failed", error=str(e))
            raise

    def parse_message(self, event: Any) -> Optional[ChannelMessage]:
        """
        Parse Slack event.
        
        Handles both message events and direct mentions.
        """
        if not isinstance(event, dict):
            return None

        # Handle message events
        if event.get("type") == "message":
            # Ignore bot messages and message changes
            if event.get("subtype") in ["bot_message", "message_changed", "message_deleted"]:
                return None

            # Ignore own messages
            if event.get("user") == self._bot_user_id:
                return None

            # Extract message content
            text = event.get("text", "")
            
            # Remove bot mention if present
            if self._bot_user_id and f"<@{self._bot_user_id}>" in text:
                text = text.replace(f"<@{self._bot_user_id}>", "").strip()

            return ChannelMessage(
                content=text,
                user_id=event.get("channel", ""),
                username=event.get("user", ""),
                channel_type=self.channel_type,
                raw_event=event,
            )

        # Handle app mention events
        elif event.get("type") == "app_mention":
            text = event.get("text", "")
            
            # Remove bot mention
            if self._bot_user_id and f"<@{self._bot_user_id}>" in text:
                text = text.replace(f"<@{self._bot_user_id}>", "").strip()

            return ChannelMessage(
                content=text,
                user_id=event.get("channel", ""),
                username=event.get("user", ""),
                channel_type=self.channel_type,
                raw_event=event,
            )

        return None

    async def send_message(self, user_id: str, content: str) -> bool:
        """
        Send message to Slack channel.

        Args:
            user_id: Channel ID (can be a channel or DM)
            content: Message content

        Returns:
            True if successful
        """
        if not self.client:
            logger.error("slack_client_not_initialized")
            return False

        try:
            # Slack has 40,000 char limit, but we'll chunk at 3000 for readability
            if len(content) > 3000:
                chunks = [content[i : i + 3000] for i in range(0, len(content), 3000)]
                for chunk in chunks:
                    await self.client.chat_postMessage(
                        channel=user_id,
                        text=chunk,
                        unfurl_links=False,
                        unfurl_media=False,
                    )
            else:
                await self.client.chat_postMessage(
                    channel=user_id,
                    text=content,
                    unfurl_links=False,
                    unfurl_media=False,
                )

            logger.debug("slack_message_sent", channel=user_id)
            return True

        except SlackApiError as e:
            logger.error(
                "slack_send_failed",
                channel=user_id,
                error=str(e),
                error_code=e.response.get("error"),
            )
            return False
        except Exception as e:
            logger.error(
                "slack_send_failed",
                channel=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def start(self) -> None:
        """Start Slack adapter (initialize client)."""
        if not self.token:
            logger.warning("slack_token_not_set")
            return

        logger.info("starting_slack_adapter")
        await self._initialize_client()
        logger.info("slack_adapter_started")

    async def stop(self) -> None:
        """Stop Slack adapter (cleanup)."""
        logger.info("stopping_slack_adapter")
        if self.client:
            # Close client connection
            await self.client.close()
        logger.info("slack_adapter_stopped")
