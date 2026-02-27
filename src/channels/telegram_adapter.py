"""Telegram channel adapter."""

from typing import Any, Optional

import structlog
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from src.channels.base import ChannelAdapter, ChannelMessage
from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class TelegramAdapter(ChannelAdapter):
    """Telegram bot adapter."""

    def __init__(self, token: Optional[str] = None):
        super().__init__("telegram")
        self.token = token or settings.telegram_token
        self.application: Optional[Application] = None

    async def _initialize_application(self) -> None:
        """Initialize Telegram application."""
        if not self.token:
            logger.warning("telegram_token_not_set")
            return

        self.application = Application.builder().token(self.token).build()

        # Add handlers - handle ALL text messages in groups and private chats
        # In groups, bot needs privacy mode disabled OR will only see mentions/replies
        # filters.TEXT catches both commands (/k8s) and regular text messages
        self.application.add_handler(
            MessageHandler(filters.TEXT, self._handle_message)
        )

        logger.info("telegram_application_initialized")

    async def _handle_message(self, update: Update, context: Any) -> None:
        """Handle incoming Telegram message."""
        await self.handle_incoming_message(update)

    async def _handle_start(self, update: Update, context: Any) -> None:
        """Handle /start command."""
        if update.message:
            await update.message.reply_text(
                "Hello! I'm your AI assistant. Send me a message and I'll respond!"
            )

    async def _handle_help(self, update: Update, context: Any) -> None:
        """Handle /help command."""
        from src.ai.prompt_manager import PromptManager

        if update.message:
            await update.message.reply_text(PromptManager.get_command_help())

    def parse_message(self, event: Any) -> Optional[ChannelMessage]:
        """Parse Telegram update."""
        if not isinstance(event, Update) or not event.message:
            return None

        message = event.message
        content = message.text or ""
        
        # In groups, remove bot mentions from the message (e.g., @botname)
        # This allows natural language queries and commands to work properly
        if message.chat.type in ['group', 'supergroup']:
            # Get bot username from the application
            if self.application and self.application.bot:
                bot_username = self.application.bot.username
                if bot_username:
                    # Remove @botname mentions (handles @botname at start or in middle)
                    content = content.replace(f'@{bot_username}', '').strip()
                    # Also remove bot's first name if mentioned
                    bot_first_name = self.application.bot.first_name
                    if bot_first_name:
                        content = content.replace(f'@{bot_first_name}', '').strip()
            
            logger.debug(
                "telegram_group_message",
                chat_id=message.chat_id,
                chat_type=message.chat.type,
                original_content=message.text,
                cleaned_content=content,
            )

        return ChannelMessage(
            content=content,
            user_id=str(message.chat_id),
            username=message.from_user.username if message.from_user else None,
            channel_type=self.channel_type,
            raw_event=event,
        )

    async def send_message(self, user_id: str, content: str) -> bool:
        """Send message to Telegram chat."""
        if not self.application:
            logger.error("telegram_application_not_initialized")
            return False

        try:
            chat_id = int(user_id)

            # Split long messages (Telegram limit is 4096)
            if len(content) > 4096:
                chunks = [content[i : i + 4096] for i in range(0, len(content), 4096)]
                for chunk in chunks:
                    await self.application.bot.send_message(
                        chat_id=chat_id, text=chunk
                    )
            else:
                await self.application.bot.send_message(chat_id=chat_id, text=content)

            logger.debug("telegram_message_sent", chat_id=user_id)
            return True

        except Exception as e:
            logger.error(
                "telegram_send_failed",
                chat_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )

        return False

    async def start(self) -> None:
        """Start Telegram bot."""
        if not self.token:
            logger.warning("telegram_token_not_set")
            return

        logger.info("starting_telegram_bot")
        try:
            await self._initialize_application()
            if self.application:
                await self.application.initialize()
                await self.application.start()
                await self.application.updater.start_polling()
                logger.info("telegram_bot_started")
        except Exception as e:
            logger.error("telegram_start_failed", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop Telegram bot."""
        logger.info("stopping_telegram_bot")
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
