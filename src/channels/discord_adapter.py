"""Discord channel adapter."""

from typing import Any, Optional

import discord
import structlog
from discord.ext import commands

from src.channels.base import ChannelAdapter, ChannelMessage
from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class DiscordAdapter(ChannelAdapter):
    """Discord bot adapter."""

    def __init__(self, token: Optional[str] = None):
        super().__init__("discord")
        self.token = token or settings.discord_token

        # Set up Discord intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        # Create bot instance
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up Discord event handlers."""

        @self.bot.event
        async def on_ready() -> None:
            logger.info("discord_bot_ready", user=str(self.bot.user))

        @self.bot.event
        async def on_message(message: discord.Message) -> None:
            # Ignore bot's own messages
            if message.author == self.bot.user:
                return

            # Ignore other bots
            if message.author.bot:
                return

            # Handle the message
            await self.handle_incoming_message(message)

    def parse_message(self, event: Any) -> Optional[ChannelMessage]:
        """Parse Discord message."""
        if not isinstance(event, discord.Message):
            return None

        return ChannelMessage(
            content=event.content,
            user_id=str(event.channel.id),  # Use channel ID for DMs
            username=event.author.name,
            channel_type=self.channel_type,
            raw_event=event,
        )

    async def send_message(self, user_id: str, content: str) -> bool:
        """Send message to Discord channel."""
        try:
            channel = self.bot.get_channel(int(user_id))
            if not channel:
                channel = await self.bot.fetch_channel(int(user_id))

            if channel:
                # Split long messages
                if len(content) > 2000:
                    chunks = [content[i : i + 2000] for i in range(0, len(content), 2000)]
                    for chunk in chunks:
                        await channel.send(chunk)
                else:
                    await channel.send(content)

                logger.debug("discord_message_sent", channel_id=user_id)
                return True

        except Exception as e:
            logger.error(
                "discord_send_failed",
                channel_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )

        return False

    async def start(self) -> None:
        """Start Discord bot."""
        if not self.token:
            logger.warning("discord_token_not_set")
            return

        logger.info("starting_discord_bot")
        try:
            await self.bot.start(self.token)
        except Exception as e:
            logger.error("discord_start_failed", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop Discord bot."""
        logger.info("stopping_discord_bot")
        await self.bot.close()
