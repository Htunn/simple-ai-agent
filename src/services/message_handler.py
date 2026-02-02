"""Core message handling service."""

import uuid
from typing import Optional

import structlog

from src.ai import ContextBuilder, GitHubModelsClient, ModelSelector, PromptManager
from src.channels.base import ChannelMessage
from src.channels.router import MessageRouter
from src.database import get_db_session
from src.database.redis import RedisCache, get_redis
from src.services.session_manager import SessionManager

logger = structlog.get_logger()


class MessageHandler:
    """Handles incoming messages and orchestrates responses."""

    def __init__(
        self,
        router: MessageRouter,
        ai_client: GitHubModelsClient,
    ):
        self.router = router
        self.ai_client = ai_client
        logger.info("message_handler_initialized")

    async def handle_message(self, message: ChannelMessage) -> None:
        """
        Handle incoming message from any channel.

        Args:
            message: Incoming channel message
        """
        logger.info(
            "message_received",
            channel_type=message.channel_type,
            user_id=message.user_id,
            content_length=len(message.content),
        )

        # Check for commands
        if message.content.startswith("/"):
            await self._handle_command(message)
            return

        # Process regular message
        await self._process_message(message)

    async def _handle_command(self, message: ChannelMessage) -> None:
        """Handle command messages."""
        command_parts = message.content.split()
        command = command_parts[0].lower()

        async with get_db_session() as db_session:
            session_mgr = SessionManager(RedisCache(get_redis()), db_session)
            session_data = await session_mgr.get_or_create_session(
                message.channel_type, message.user_id, message.username
            )

            if command == "/help":
                response = PromptManager.get_command_help()

            elif command == "/reset":
                await session_mgr.clear_session(message.channel_type, message.user_id)
                response = "Conversation reset! Starting fresh."

            elif command == "/status":
                context_builder = ContextBuilder(db_session)
                stats = await context_builder.get_message_stats(
                    uuid.UUID(session_data.conversation_id)
                )
                model_selector = ModelSelector(db_session)
                current_model = await model_selector.select_model(
                    uuid.UUID(session_data.user_id),
                    uuid.UUID(session_data.conversation_id),
                    message.channel_type,
                )
                response = f"""📊 Status:
Model: {current_model}
Messages: {stats['message_count']}
Tokens: {stats['total_tokens']}"""

            elif command == "/model":
                if len(command_parts) < 2:
                    response = "Usage: /model <gpt-4|claude-3-opus|llama-3-70b>"
                else:
                    new_model = command_parts[1]
                    if self.ai_client.is_model_supported(new_model):
                        model_selector = ModelSelector(db_session)
                        await model_selector.set_user_model(
                            uuid.UUID(session_data.user_id), new_model
                        )
                        response = f"Model set to: {new_model}"
                    else:
                        supported = ", ".join(self.ai_client.list_supported_models())
                        response = f"Unsupported model. Available: {supported}"

            else:
                response = "Unknown command. Try /help"

            # Send response
            await self.router.send_message(
                message.channel_type, message.user_id, response
            )

    async def _process_message(self, message: ChannelMessage) -> None:
        """Process regular message and generate AI response."""
        try:
            async with get_db_session() as db_session:
                # Initialize managers
                redis_cache = RedisCache(get_redis())
                session_mgr = SessionManager(redis_cache, db_session)
                context_builder = ContextBuilder(db_session)
                model_selector = ModelSelector(db_session)

                # Get or create session
                session_data = await session_mgr.get_or_create_session(
                    message.channel_type, message.user_id, message.username
                )

                conversation_id = uuid.UUID(session_data.conversation_id)
                user_id = uuid.UUID(session_data.user_id)

                # Add user message to database
                await context_builder.add_user_message(
                    conversation_id, message.content
                )

                # Build conversation context
                system_prompt = PromptManager.get_system_prompt(message.channel_type)
                context = await context_builder.build_context(
                    conversation_id, system_prompt=system_prompt
                )

                # Select model
                model = await model_selector.select_model(
                    user_id, conversation_id, message.channel_type
                )

                # Generate AI response
                logger.info(
                    "generating_ai_response",
                    model=model,
                    conversation_id=str(conversation_id),
                )

                response_content, token_count = await self.ai_client.generate_response(
                    messages=context, model=model
                )

                # Save assistant message
                await context_builder.add_assistant_message(
                    conversation_id,
                    response_content,
                    model_used=model,
                    token_count=token_count,
                )

                # Update session activity
                await session_mgr.update_session_activity(
                    message.channel_type, message.user_id
                )
                await session_mgr.increment_message_count(
                    message.channel_type, message.user_id
                )

                # Send response through channel
                await self.router.send_message(
                    message.channel_type, message.user_id, response_content
                )

                logger.info(
                    "message_processed_successfully",
                    conversation_id=str(conversation_id),
                    model=model,
                    tokens=token_count,
                )

        except Exception as e:
            logger.error(
                "message_processing_failed",
                error=str(e),
                error_type=type(e).__name__,
                channel_type=message.channel_type,
                user_id=message.user_id,
            )

            # Send error message to user
            error_message = "Sorry, I encountered an error processing your message. Please try again."
            await self.router.send_message(
                message.channel_type, message.user_id, error_message
            )
