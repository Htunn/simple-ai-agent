"""Unit tests for PromptManager."""

import pytest
from src.ai.prompt_manager import PromptManager


class TestGetSystemPrompt:
    def test_returns_default_when_no_args(self):
        prompt = PromptManager.get_system_prompt()
        assert prompt == PromptManager.DEFAULT_SYSTEM_PROMPT
        assert len(prompt) > 0

    def test_custom_prompt_overrides_everything(self):
        custom = "You are a pirate assistant."
        assert PromptManager.get_system_prompt(custom_prompt=custom) == custom

    def test_custom_prompt_overrides_channel_type(self):
        custom = "My custom prompt"
        result = PromptManager.get_system_prompt(channel_type="slack", custom_prompt=custom)
        assert result == custom

    def test_telegram_channel_returns_telegram_prompt(self):
        result = PromptManager.get_system_prompt(channel_type="telegram")
        assert result == PromptManager.CHANNEL_PROMPTS["telegram"]
        assert "Telegram" in result

    def test_slack_channel_returns_slack_prompt(self):
        result = PromptManager.get_system_prompt(channel_type="slack")
        assert result == PromptManager.CHANNEL_PROMPTS["slack"]
        assert "Slack" in result

    def test_unknown_channel_falls_back_to_default(self):
        result = PromptManager.get_system_prompt(channel_type="discord")
        assert result == PromptManager.DEFAULT_SYSTEM_PROMPT

    def test_none_channel_returns_default(self):
        result = PromptManager.get_system_prompt(channel_type=None)
        assert result == PromptManager.DEFAULT_SYSTEM_PROMPT

    def test_channel_prompts_differ_from_default(self):
        default = PromptManager.DEFAULT_SYSTEM_PROMPT
        assert PromptManager.CHANNEL_PROMPTS["telegram"] != default
        assert PromptManager.CHANNEL_PROMPTS["slack"] != default

    def test_channel_prompts_differ_from_each_other(self):
        assert PromptManager.CHANNEL_PROMPTS["telegram"] != PromptManager.CHANNEL_PROMPTS["slack"]


class TestFormatUserMessage:
    def test_no_username_returns_content_unchanged(self):
        result = PromptManager.format_user_message("hello world")
        assert result == "hello world"

    def test_with_username_prepends_username(self):
        result = PromptManager.format_user_message("hello", username="alice")
        assert result == "alice: hello"

    def test_empty_username_still_returns_content(self):
        result = PromptManager.format_user_message("hello", username=None)
        assert result == "hello"

    def test_username_colon_separator(self):
        result = PromptManager.format_user_message("msg", username="bob")
        assert result.startswith("bob:")


class TestGetCommandHelp:
    def test_returns_non_empty_string(self):
        help_text = PromptManager.get_command_help()
        assert isinstance(help_text, str)
        assert len(help_text) > 0

    def test_includes_k8s_commands(self):
        help_text = PromptManager.get_command_help()
        assert "/k8s" in help_text

    def test_includes_aiops_commands(self):
        help_text = PromptManager.get_command_help()
        assert "incident" in help_text.lower() or "approval" in help_text.lower()

    def test_includes_help_command(self):
        help_text = PromptManager.get_command_help()
        assert "/help" in help_text

    def test_includes_model_command(self):
        help_text = PromptManager.get_command_help()
        assert "/model" in help_text
