"""Prompt templates and management."""


class PromptManager:
    """Manages system prompts and templates."""

    DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant. You provide clear, accurate, and concise responses to user questions. You are friendly, professional, and always aim to be helpful."""

    CHANNEL_PROMPTS = {
        "telegram": """You are a helpful AI assistant in a Telegram chat. Keep responses clear and concise. You can use Telegram formatting like *bold* and _italic_.""",
        "slack": """You are a helpful AI assistant in a Slack workspace. Keep responses clear and professional. Use Slack mrkdwn formatting when appropriate.""",
    }

    @classmethod
    def get_system_prompt(
        cls, channel_type: str | None = None, custom_prompt: str | None = None
    ) -> str:
        """
        Get system prompt for AI model.

        Args:
            channel_type: Channel type (telegram, slack)
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
    def format_user_message(cls, content: str, username: str | None = None) -> str:
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
"""
