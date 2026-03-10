"""Unit tests for ApprovalManager and PendingApproval."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.approval_manager import (
    ApprovalManager,
    ApprovalStatus,
    PendingApproval,
    RiskLevel,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_approval(**kwargs) -> PendingApproval:
    defaults = dict(
        approval_id=str(uuid.uuid4()),
        tool_name="k8s_restart_pod",
        tool_params={"pod_name": "web-pod", "namespace": "default"},
        risk_level=RiskLevel.MEDIUM,
        description="Restart pod web-pod",
        requested_by="aiops-watchloop",
        channel_type="slack",
        channel_target="D0AHV7N42NS",
    )
    defaults.update(kwargs)
    return PendingApproval(**defaults)


def _make_redis(approval: PendingApproval | None = None):
    """Mock redis with optional stored approval."""
    redis = AsyncMock()
    data = json.dumps(approval.to_dict()).encode() if approval else None
    redis.get = AsyncMock(return_value=data)
    redis.setex = AsyncMock()
    redis.scan = AsyncMock(return_value=(0, []))
    return redis


# ── PendingApproval ───────────────────────────────────────────────────────────

class TestPendingApproval:
    def test_to_dict_roundtrip(self):
        original = _make_approval()
        restored = PendingApproval.from_dict(original.to_dict())
        assert restored.approval_id == original.approval_id
        assert restored.tool_name == original.tool_name
        assert restored.risk_level == original.risk_level
        assert restored.status == original.status

    def test_to_dict_serializes_enums_as_strings(self):
        approval = _make_approval(risk_level=RiskLevel.HIGH)
        d = approval.to_dict()
        assert d["risk_level"] == "high"
        assert d["status"] == "pending"

    def test_to_dict_serializes_datetime(self):
        approval = _make_approval()
        d = approval.to_dict()
        assert isinstance(d["requested_at"], str)
        # Should be ISO format parseable
        datetime.fromisoformat(d["requested_at"])

    def test_approval_message_contains_short_id(self):
        approval = _make_approval()
        msg = approval.approval_message()
        assert approval.approval_id[:8] in msg

    def test_approval_message_medium_risk_emoji(self):
        approval = _make_approval(risk_level=RiskLevel.MEDIUM)
        assert "🟠" in approval.approval_message()

    def test_approval_message_high_risk_emoji(self):
        approval = _make_approval(risk_level=RiskLevel.HIGH)
        assert "🔴" in approval.approval_message()

    def test_approval_message_low_risk_emoji(self):
        approval = _make_approval(risk_level=RiskLevel.LOW)
        assert "🟡" in approval.approval_message()

    def test_approval_message_high_risk_includes_warning_prefix(self):
        approval = _make_approval(risk_level=RiskLevel.HIGH)
        msg = approval.approval_message()
        assert "HIGH RISK" in msg

    def test_approval_message_medium_risk_no_warning_prefix(self):
        approval = _make_approval(risk_level=RiskLevel.MEDIUM)
        msg = approval.approval_message()
        assert "HIGH RISK" not in msg

    def test_approval_message_contains_tool_name(self):
        approval = _make_approval(tool_name="k8s_drain_node")
        assert "k8s_drain_node" in approval.approval_message()

    def test_approval_message_contains_description(self):
        approval = _make_approval(description="Drain node for maintenance")
        assert "Drain node for maintenance" in approval.approval_message()

    def test_approval_message_approve_reject_instructions(self):
        approval = _make_approval()
        msg = approval.approval_message()
        assert "approve" in msg
        assert "reject" in msg

    def test_default_status_is_pending(self):
        approval = _make_approval()
        assert approval.status == ApprovalStatus.PENDING

    def test_playbook_run_id_defaults_none(self):
        approval = _make_approval()
        assert approval.playbook_run_id is None


# ── ApprovalManager.process_response() ───────────────────────────────────────

class TestApprovalManagerProcessResponse:
    def _make_manager_with_approval(self, approval: PendingApproval):
        redis = _make_redis(approval)
        # Index lookup: returns full approval_id
        full_id_bytes = approval.approval_id.encode()
        approval_data = json.dumps(approval.to_dict()).encode()

        async def fake_get(key):
            if "approval_idx:" in key:
                return full_id_bytes
            return approval_data

        redis.get = AsyncMock(side_effect=fake_get)
        mgr = ApprovalManager(redis_client=redis)
        return mgr

    async def test_unrelated_message_returns_none(self):
        mgr = ApprovalManager()
        result = await mgr.process_response("hello world", "user1", "chan1")
        assert result is None

    async def test_only_keyword_without_id_returns_none(self):
        mgr = ApprovalManager()
        result = await mgr.process_response("approve", "user1", "chan1")
        assert result is None

    async def test_unknown_short_id_returns_not_found_message(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.scan = AsyncMock(return_value=(0, []))
        mgr = ApprovalManager(redis_client=redis)
        result = await mgr.process_response("approve abcd1234", "user1", "chan1")
        assert result is not None
        assert "abcd1234" in result

    @pytest.mark.parametrize("keyword", ["approve", "yes", "confirm"])
    async def test_approve_keywords_recognized(self, keyword):
        approval = _make_approval()
        short_id = approval.approval_id[:8]
        mgr = self._make_manager_with_approval(approval)
        # MCP not set → returns "approved but MCP not available"
        result = await mgr.process_response(f"{keyword} {short_id}", "user1", "chan1")
        assert result is not None
        assert "Approved" in result or "approved" in result or "MCP" in result

    @pytest.mark.parametrize("keyword", ["reject", "no", "cancel"])
    async def test_reject_keywords_recognized(self, keyword):
        approval = _make_approval()
        short_id = approval.approval_id[:8]
        mgr = self._make_manager_with_approval(approval)
        result = await mgr.process_response(f"{keyword} {short_id}", "user1", "chan1")
        assert result is not None
        assert "rejected" in result.lower() or "❌" in result

    async def test_approve_is_case_insensitive(self):
        approval = _make_approval()
        short_id = approval.approval_id[:8]
        mgr = self._make_manager_with_approval(approval)
        result = await mgr.process_response(f"APPROVE {short_id}", "user1", "chan1")
        assert result is not None

    async def test_reject_updates_status_in_redis(self):
        approval = _make_approval()
        short_id = approval.approval_id[:8]
        redis = AsyncMock()
        full_id_bytes = approval.approval_id.encode()
        approval_data = json.dumps(approval.to_dict()).encode()

        async def fake_get(key):
            if "approval_idx:" in key:
                return full_id_bytes
            return approval_data

        redis.get = AsyncMock(side_effect=fake_get)
        redis.setex = AsyncMock()

        mgr = ApprovalManager(redis_client=redis)
        await mgr.process_response(f"reject {short_id}", "user1", "chan1")
        # setex should have been called to update status
        redis.setex.assert_called()


# ── ApprovalManager.request_approval() ───────────────────────────────────────

class TestApprovalManagerRequestApproval:
    async def test_returns_approval_id_string(self):
        redis = AsyncMock()
        redis.setex = AsyncMock()
        mgr = ApprovalManager(redis_client=redis)
        # Patch audit log write to avoid DB
        mgr._write_audit_log = AsyncMock()

        approval_id = await mgr.request_approval(
            tool_name="k8s_restart_pod",
            tool_params={"pod_name": "p1"},
            risk_level=RiskLevel.MEDIUM,
            description="Restart p1",
            requested_by="test-user",
            channel_type="slack",
            channel_target="D123",
        )
        assert isinstance(approval_id, str)
        # Should be a valid UUID
        uuid.UUID(approval_id)

    async def test_stores_in_redis_with_two_keys(self):
        redis = AsyncMock()
        redis.setex = AsyncMock()
        mgr = ApprovalManager(redis_client=redis)
        mgr._write_audit_log = AsyncMock()

        await mgr.request_approval(
            tool_name="k8s_drain_node",
            tool_params={"node": "node-1"},
            risk_level=RiskLevel.HIGH,
            description="Drain node",
            requested_by="admin",
            channel_type="slack",
            channel_target="C123",
        )
        # Two setex calls: main key + index key
        assert redis.setex.call_count == 2

    async def test_send_message_callback_is_called(self):
        redis = AsyncMock()
        redis.setex = AsyncMock()
        mgr = ApprovalManager(redis_client=redis)
        mgr._write_audit_log = AsyncMock()

        sent_messages = []

        async def fake_send(channel, message):
            sent_messages.append((channel, message))

        await mgr.request_approval(
            tool_name="k8s_restart_pod",
            tool_params={"pod_name": "p1"},
            risk_level=RiskLevel.MEDIUM,
            description="Restart p1",
            requested_by="test",
            channel_type="slack",
            channel_target="D999",
            send_message_callback=fake_send,
        )
        assert len(sent_messages) == 1
        assert sent_messages[0][0] == "D999"
        assert "Approval Required" in sent_messages[0][1]

    async def test_no_send_message_callback_does_not_raise(self):
        redis = AsyncMock()
        redis.setex = AsyncMock()
        mgr = ApprovalManager(redis_client=redis)
        mgr._write_audit_log = AsyncMock()

        # Should not raise even without callback
        await mgr.request_approval(
            tool_name="k8s_restart_pod",
            tool_params={},
            risk_level=RiskLevel.LOW,
            description="test",
            requested_by="test",
            channel_type="slack",
            channel_target="D1",
        )

    async def test_no_redis_still_returns_approval_id(self):
        mgr = ApprovalManager(redis_client=None)
        mgr._write_audit_log = AsyncMock()

        approval_id = await mgr.request_approval(
            tool_name="k8s_restart_pod",
            tool_params={},
            risk_level=RiskLevel.LOW,
            description="test",
            requested_by="test",
            channel_type="slack",
            channel_target="D1",
        )
        assert isinstance(approval_id, str)


# ── ApprovalManager.list_pending() ───────────────────────────────────────────

class TestListPending:
    async def test_returns_empty_when_no_redis(self):
        mgr = ApprovalManager(redis_client=None)
        result = await mgr.list_pending()
        assert result == []

    async def test_returns_only_pending_status(self):
        redis = AsyncMock()
        approved = _make_approval(status=ApprovalStatus.APPROVED)
        pending = _make_approval(status=ApprovalStatus.PENDING)

        async def fake_scan(cursor, match, count):
            return (0, [b"approval:key1", b"approval:key2"])

        async def fake_get(key):
            key_str = key.decode() if isinstance(key, bytes) else key
            if "key1" in key_str:
                return json.dumps(approved.to_dict()).encode()
            return json.dumps(pending.to_dict()).encode()

        redis.scan = AsyncMock(side_effect=fake_scan)
        redis.get = AsyncMock(side_effect=fake_get)
        mgr = ApprovalManager(redis_client=redis)

        results = await mgr.list_pending()
        assert len(results) == 1
        assert results[0].status == ApprovalStatus.PENDING
