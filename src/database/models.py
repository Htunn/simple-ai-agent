"""Database models for the application."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class User(Base):
    """User model representing users across different channels."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    channel_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    channel_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_model: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="User's preferred AI model"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<User {self.channel_type}:{self.channel_user_id}>"


class Conversation(Base):
    """Conversation/session model."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    channel_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    model_override: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Override model for this conversation"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False, server_default="{}"
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id} user={self.user_id}>"


class Message(Base):
    """Message model storing conversation history."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="user, assistant, system"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="AI model used for this message"
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False, server_default="{}"
    )

    def __repr__(self) -> str:
        return f"<Message {self.role} in {self.conversation_id}>"


class ChannelConfig(Base):
    """Channel-specific configuration."""

    __tablename__ = "channel_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    channel_type: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )
    default_model: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Default model for this channel"
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ChannelConfig {self.channel_type}>"


# ── AIOps Tables ──────────────────────────────────────────────────────────────


class Incident(Base):
    """An operational incident detected by the watchloop or Alertmanager."""

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="P3", index=True)
    # open | investigating | remediating | resolved
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    namespace: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    resource_kind: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    rca_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, server_default="{}")

    __table_args__ = (
        Index("ix_incidents_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Incident {self.severity} {self.event_type}/{self.resource_name} [{self.status}]>"


class AlertEvent(Base):
    """An alert event from Alertmanager or the internal watchloop."""

    __tablename__ = "alert_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning", index=True)
    # firing | resolved
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="firing")
    # prometheus | alertmanager | watchloop | manual
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="watchloop")
    labels: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, server_default="{}")
    annotations: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, server_default="{}")
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<AlertEvent {self.rule_name} [{self.status}]>"


class RemediationAction(Base):
    """Audit record of every remediation action (approved or auto-executed)."""

    __tablename__ = "remediation_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    playbook_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    playbook_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_kind: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    namespace: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # human | auto
    initiator: Mapped[str] = mapped_column(String(50), nullable=False, default="human")
    # pending | approved | rejected | executing | completed | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, server_default="{}")

    def __repr__(self) -> str:
        return f"<RemediationAction {self.action_type} [{self.status}]>"


class K8sStateSnapshot(Base):
    """Periodic snapshot of cluster resource state for drift detection."""

    __tablename__ = "k8s_state_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    namespace: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resource_kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    spec_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    snapshot_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, server_default="{}")
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_k8s_snapshot_resource", "namespace", "resource_kind", "resource_name"),
    )


class AuditLog(Base):
    """Audit trail for all destructive AIOps operations."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    # auto for automated actions
    initiator: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
    action: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resource_kind: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    namespace: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # success | failed | rejected
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, server_default="{}")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by {self.initiator} [{self.result}]>"
