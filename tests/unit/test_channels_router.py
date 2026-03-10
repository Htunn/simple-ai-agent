"""Unit tests for MessageRouter and channel base types."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.channels.base import ChannelAdapter, ChannelMessage
from src.channels.router import MessageRouter


# ── ChannelMessage ────────────────────────────────────────────────────────────

class TestChannelMessage:
    def test_basic_attributes(self):
        msg = ChannelMessage(content="hello", user_id="U123", channel_type="slack")
        assert msg.content == "hello"
        assert msg.user_id == "U123"
        assert msg.channel_type == "slack"

    def test_defaults(self):
        msg = ChannelMessage(content="hi", user_id="U1")
        assert msg.username is None
        assert msg.channel_type == ""
        assert msg.raw_event is None

    def test_repr_contains_channel_and_user(self):
        msg = ChannelMessage(content="x", user_id="U999", channel_type="telegram")
        r = repr(msg)
        assert "telegram" in r
        assert "U999" in r


# ── Concrete stub adapter ─────────────────────────────────────────────────────

class StubAdapter(ChannelAdapter):
    def __init__(self, channel_type: str, send_result: bool = True):
        super().__init__(channel_type)
        self._send_result = send_result
        self.sent: list[tuple[str, str]] = []

    async def send_message(self, user_id: str, content: str) -> bool:
        self.sent.append((user_id, content))
        return self._send_result

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def parse_message(self, event):
        return ChannelMessage(content=str(event), user_id="U1", channel_type=self.channel_type)


# ── MessageRouter ─────────────────────────────────────────────────────────────

class TestMessageRouter:
    def test_register_adapter_stores_by_channel_type(self):
        router = MessageRouter()
        adapter = StubAdapter("slack")
        router.register_adapter(adapter)
        assert router.get_adapter("slack") is adapter

    def test_register_multiple_adapters(self):
        router = MessageRouter()
        slack = StubAdapter("slack")
        telegram = StubAdapter("telegram")
        router.register_adapter(slack)
        router.register_adapter(telegram)
        assert router.get_adapter("slack") is slack
        assert router.get_adapter("telegram") is telegram

    def test_get_adapter_unknown_returns_none(self):
        router = MessageRouter()
        assert router.get_adapter("discord") is None

    def test_set_message_handler(self):
        router = MessageRouter()
        handler = AsyncMock()
        router.set_message_handler(handler)
        assert router.message_handler is handler

    async def test_send_message_routes_to_correct_adapter(self):
        router = MessageRouter()
        adapter = StubAdapter("slack")
        router.register_adapter(adapter)
        result = await router.send_message("slack", "U123", "hello")
        assert result is True
        assert adapter.sent == [("U123", "hello")]

    async def test_send_message_unknown_channel_returns_false(self):
        router = MessageRouter()
        result = await router.send_message("discord", "U1", "msg")
        assert result is False

    async def test_send_message_adapter_failure_propagates(self):
        router = MessageRouter()
        adapter = StubAdapter("slack", send_result=False)
        router.register_adapter(adapter)
        result = await router.send_message("slack", "U1", "msg")
        assert result is False

    async def test_route_message_calls_handler(self):
        router = MessageRouter()
        received = []

        async def handler(msg: ChannelMessage):
            received.append(msg)

        router.set_message_handler(handler)
        msg = ChannelMessage(content="test", user_id="U1", channel_type="slack")
        await router._route_message(msg)
        assert len(received) == 1
        assert received[0].content == "test"

    async def test_route_message_no_handler_does_not_raise(self):
        router = MessageRouter()
        msg = ChannelMessage(content="test", user_id="U1")
        # Should not raise, should log warning silently
        await router._route_message(msg)

    async def test_adapter_message_handler_set_on_register(self):
        router = MessageRouter()
        adapter = StubAdapter("slack")
        router.register_adapter(adapter)
        # The adapter's handler should route messages through the router
        received = []
        router.set_message_handler(lambda msg: received.append(msg) or asyncio.sleep(0))
        assert adapter.message_handler is not None
        assert callable(adapter.message_handler)

    async def test_stop_all_calls_stop_on_all_adapters(self):
        router = MessageRouter()
        a1 = StubAdapter("slack")
        a2 = StubAdapter("telegram")
        a1.stop = AsyncMock()
        a2.stop = AsyncMock()
        router.register_adapter(a1)
        router.register_adapter(a2)
        await router.stop_all()
        a1.stop.assert_awaited_once()
        a2.stop.assert_awaited_once()


# ── ChannelAdapter.handle_incoming_message() ─────────────────────────────────

class TestChannelAdapterHandleIncoming:
    async def test_handle_parses_and_calls_handler(self):
        adapter = StubAdapter("slack")
        received = []

        async def handler(msg: ChannelMessage):
            received.append(msg)

        adapter.set_message_handler(handler)
        await adapter.handle_incoming_message("raw event data")
        assert len(received) == 1
        assert received[0].content == "raw event data"

    async def test_handle_no_handler_does_not_raise(self):
        adapter = StubAdapter("telegram")
        # No handler set — should not raise
        await adapter.handle_incoming_message("some event")
