"""
Human-in-the-loop Approval Manager.

Stores pending remediation approvals in Redis with TTL.
Risk classification determines whether an action needs approval:
  LOW    → execute immediately, notify after
  MEDIUM → post approval request, user must confirm in chat
  HIGH   → post approval request with explicit risk warning

Approval is granted/rejected via chat response matching approval ID.
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine

import structlog

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"


@dataclass
class PendingApproval:
    """A pending action waiting for user approval."""
    approval_id: str
    tool_name: str
    tool_params: dict[str, Any]
    risk_level: RiskLevel
    description: str
    requested_by: str          # user_id or "auto"
    channel_type: str
    channel_target: str        # chat_id or channel_id to reply to
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    playbook_run_id: str | None = None
    incident_id: str | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["requested_at"] = self.requested_at.isoformat()
        d["risk_level"] = self.risk_level.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PendingApproval":
        d = dict(d)
        d["requested_at"] = datetime.fromisoformat(d["requested_at"])
        d["risk_level"] = RiskLevel(d["risk_level"])
        d["status"] = ApprovalStatus(d["status"])
        return cls(**d)

    def approval_message(self) -> str:
        risk_emoji = {"low": "🟡", "medium": "🟠", "high": "🔴"}[self.risk_level.value]
        lines = [
            f"{risk_emoji} **Approval Required** [{self.risk_level.value.upper()}]",
            f"",
            f"**Action:** {self.description}",
            f"**Tool:** `{self.tool_name}`",
            f"**Parameters:** `{json.dumps(self.tool_params, indent=2)}`",
            f"",
            f"Reply with **`approve {self.approval_id[:8]}`** to proceed or **`reject {self.approval_id[:8]}`** to cancel.",
            f"This request expires in {settings.approval_timeout_seconds // 60} minutes.",
        ]
        if self.risk_level == RiskLevel.HIGH:
            lines.insert(0, "⚠️ **HIGH RISK ACTION — Review carefully before approving**\n")
        return "\n".join(lines)


class ApprovalManager:
    """
    Manages the lifecycle of pending approvals via Redis.

    Usage:
        mgr = ApprovalManager(redis_client, mcp_manager)
        approval_id = await mgr.request_approval(
            tool_name="k8s_drain_node",
            tool_params={"node_name": "node-1"},
            risk_level=RiskLevel.HIGH,
            description="Drain node-1 for maintenance",
            ...,
            send_message_callback=channel_send_fn,
        )
    """

    REDIS_KEY_PREFIX = "approval:"

    def __init__(self, redis_client=None, mcp_manager=None) -> None:
        self._redis = redis_client
        self._mcp = mcp_manager

    async def request_approval(
        self,
        tool_name: str,
        tool_params: dict[str, Any],
        risk_level: RiskLevel,
        description: str,
        requested_by: str,
        channel_type: str,
        channel_target: str,
        send_message_callback: Callable[[str, str], Coroutine] | None = None,
        playbook_run_id: str | None = None,
        incident_id: str | None = None,
    ) -> str:
        """
        Create a pending approval and notify the user.
        Returns the approval_id.
        """
        approval = PendingApproval(
            approval_id=str(uuid.uuid4()),
            tool_name=tool_name,
            tool_params=tool_params,
            risk_level=risk_level,
            description=description,
            requested_by=requested_by,
            channel_type=channel_type,
            channel_target=channel_target,
            playbook_run_id=playbook_run_id,
            incident_id=incident_id,
        )

        # Store in Redis with TTL
        if self._redis:
            key = f"{self.REDIS_KEY_PREFIX}{approval.approval_id}"
            await self._redis.setex(
                key,
                settings.approval_timeout_seconds,
                json.dumps(approval.to_dict()),
            )

        logger.info("approval_requested",
                   approval_id=approval.approval_id,
                   tool=tool_name,
                   risk=risk_level.value,
                   user=requested_by)

        # Notify user
        if send_message_callback:
            await send_message_callback(channel_target, approval.approval_message())

        return approval.approval_id

    async def process_response(self, text: str, user_id: str, channel_target: str) -> str | None:
        """
        Check if a message contains an approval/rejection command.
        Returns a response message or None if the text is unrelated.

        Supports:
          "approve abc12345" | "yes abc12345" | "confirm abc12345"
          "reject abc12345"  | "no abc12345"  | "cancel abc12345"
        """
        import re
        approve_match = re.search(r'\b(?:approve|yes|confirm)\s+([a-f0-9]{8})', text, re.IGNORECASE)
        reject_match = re.search(r'\b(?:reject|no|cancel)\s+([a-f0-9]{8})', text, re.IGNORECASE)

        if not approve_match and not reject_match:
            return None

        active_match = approve_match or reject_match
        if active_match is None:
            return None  # should be unreachable; satisfies type-checker
        short_id = active_match.group(1)
        approval = await self._find_by_short_id(short_id)
        if not approval:
            return f"⚠️ No pending approval found for ID `{short_id}`. It may have expired."

        if approve_match:
            return await self._execute_approval(approval, user_id)
        else:
            return await self._reject_approval(approval, user_id)

    async def _execute_approval(self, approval: PendingApproval, approved_by: str) -> str:
        """Execute an approved action via MCP."""
        logger.info("approval_executing",
                   approval_id=approval.approval_id,
                   tool=approval.tool_name,
                   approved_by=approved_by)

        if not self._mcp:
            await self._update_status(approval.approval_id, ApprovalStatus.APPROVED)
            return f"✅ Approved by {approved_by}, but MCP manager not available to execute."

        try:
            result = await self._mcp.call_tool(approval.tool_name, approval.tool_params)
            await self._update_status(approval.approval_id, ApprovalStatus.EXECUTED)
            logger.info("approval_executed", approval_id=approval.approval_id, tool=approval.tool_name)
            return (
                f"✅ **{approval.description}** executed successfully.\n\n"
                f"```\n{str(result)[:800]}\n```"
            )
        except Exception as e:
            logger.error("approval_execution_failed", approval_id=approval.approval_id, error=str(e))
            return f"❌ Execution failed: {e}"

    async def _reject_approval(self, approval: PendingApproval, rejected_by: str) -> str:
        await self._update_status(approval.approval_id, ApprovalStatus.REJECTED)
        logger.info("approval_rejected", approval_id=approval.approval_id, rejected_by=rejected_by)
        return f"❌ Action **{approval.description}** rejected by {rejected_by}."

    async def _find_by_short_id(self, short_id: str) -> PendingApproval | None:
        """Find a pending approval by the first 8 chars of its ID."""
        if not self._redis:
            return None
        # Scan for matching keys (low volume expected)
        cursor = 0
        pattern = f"{self.REDIS_KEY_PREFIX}*"
        while True:
            cursor, keys = await self._redis.scan(cursor, match=pattern, count=50)
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                approval_id = key_str.replace(self.REDIS_KEY_PREFIX, "")
                if approval_id.startswith(short_id):
                    data = await self._redis.get(key_str)
                    if data:
                        raw = json.loads(data.decode() if isinstance(data, bytes) else data)
                        return PendingApproval.from_dict(raw)
            if cursor == 0:
                break
        return None

    async def _update_status(self, approval_id: str, status: ApprovalStatus) -> None:
        if not self._redis:
            return
        key = f"{self.REDIS_KEY_PREFIX}{approval_id}"
        data = await self._redis.get(key)
        if data:
            raw = json.loads(data.decode() if isinstance(data, bytes) else data)
            raw["status"] = status.value
            await self._redis.setex(key, settings.approval_timeout_seconds, json.dumps(raw))

    async def list_pending(self) -> list[PendingApproval]:
        """List all currently pending approvals."""
        if not self._redis:
            return []
        results = []
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match=f"{self.REDIS_KEY_PREFIX}*", count=100)
            for key in keys:
                data = await self._redis.get(key)
                if data:
                    raw = json.loads(data.decode() if isinstance(data, bytes) else data)
                    if raw.get("status") == ApprovalStatus.PENDING.value:
                        results.append(PendingApproval.from_dict(raw))
            if cursor == 0:
                break
        return results
