"""Prompt templates and management."""

from typing import Optional


class PromptManager:
    """Manages system prompts and templates."""

    DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant. You provide clear, accurate, and concise responses to user questions. You are friendly, professional, and always aim to be helpful."""

    CHANNEL_PROMPTS = {
        "discord": """You are a helpful AI assistant in a Discord server. Keep responses conversational and friendly. Use Discord markdown when appropriate.""",
        "telegram": """You are a helpful AI assistant in a Telegram chat. Keep responses clear and concise. You can use Telegram formatting like *bold* and _italic_.""",
        "whatsapp": """You are a helpful AI assistant in a WhatsApp conversation. Keep responses brief and conversational.""",
    }

    @classmethod
    def get_system_prompt(
        cls, channel_type: Optional[str] = None, custom_prompt: Optional[str] = None
    ) -> str:
        """
        Get system prompt for AI model.

        Args:
            channel_type: Channel type (discord, telegram, whatsapp)
            custom_prompt: Custom system prompt to use instead

        Returns:
            System prompt string
        """
        if custom_prompt:
            return custom_prompt

        if channel_type and channel_type in cls.CHANNEL_PROMPTS:
            return cls.CHANNEL_PROMPTS[channel_type]

        return cls.DEFAULT_SYSTEM_PROMPT

    @classmethod
    def format_user_message(cls, content: str, username: Optional[str] = None) -> str:
        """Format user message with optional username."""
        if username:
            return f"{username}: {content}"
        return content

    @classmethod
    def get_command_help(cls) -> str:
        """Get help text for available commands."""
        return """Available commands:

**General Commands:**
/help - Show this help message
/model <name> - Set AI model (gpt-4, claude-3-opus, llama-3-70b)
/reset - Start a new conversation
/status - Show current model and conversation stats

**Kubernetes Commands:**
/k8s help - Show full Kubernetes command list
/k8s pods [namespace] - List pods
/k8s nodes - List nodes
/k8s deployments [namespace] - List deployments
/k8s logs <pod> [namespace] - Get pod logs
/k8s scale <deployment> <replicas> [namespace] - Scale deployment

**AIOps Commands:**
/incident list - Show open incidents
/incident show <id> - Show incident details
/incident close <id> - Resolve an incident
/alert list - Show recent alert events
/approval list - Show pending approvals
/approval approve <id> - Approve a pending action
/approval reject <id> - Reject a pending action

**Self-Healing (Natural Language):**
• "restart pod <name>" or "restart deployment <name>"
• "rollback deployment <name>"
• "cordon / uncordon / drain node <name>"
• "show crashlooping pods"
