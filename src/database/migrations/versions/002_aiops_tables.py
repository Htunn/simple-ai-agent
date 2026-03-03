"""AIOps tables: incidents, alert_events, remediation_actions, k8s_state_snapshots, audit_log

Revision ID: 002_aiops_tables
Revises: 001
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = "002_aiops_tables"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # incidents
    op.create_table(
        "incidents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False, server_default="P3"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("namespace", sa.String(255), nullable=True),
        sa.Column("resource_kind", sa.String(50), nullable=True),
        sa.Column("resource_name", sa.String(255), nullable=True),
        sa.Column("root_cause", sa.Text, nullable=True),
        sa.Column("rca_confidence", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", JSONB, server_default="{}", nullable=False),
    )
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_namespace", "incidents", ["namespace"])
    op.create_index("ix_incidents_status_created", "incidents", ["status", "created_at"])

    # alert_events
    op.create_table(
        "alert_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", UUID(as_uuid=True), nullable=True),
        sa.Column("rule_name", sa.String(255), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("status", sa.String(20), nullable=False, server_default="firing"),
        sa.Column("source", sa.String(50), nullable=False, server_default="watchloop"),
        sa.Column("labels", JSONB, server_default="{}", nullable=False),
        sa.Column("annotations", JSONB, server_default="{}", nullable=False),
        sa.Column("fired_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_alert_events_rule_name", "alert_events", ["rule_name"])
    op.create_index("ix_alert_events_severity", "alert_events", ["severity"])
    op.create_index("ix_alert_events_fired_at", "alert_events", ["fired_at"])
    op.create_index("ix_alert_events_incident_id", "alert_events", ["incident_id"])

    # remediation_actions
    op.create_table(
        "remediation_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", UUID(as_uuid=True), nullable=True),
        sa.Column("playbook_id", sa.String(100), nullable=True),
        sa.Column("playbook_run_id", sa.String(100), nullable=True),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("resource_kind", sa.String(50), nullable=True),
        sa.Column("resource_name", sa.String(255), nullable=True),
        sa.Column("namespace", sa.String(255), nullable=True),
        sa.Column("initiator", sa.String(50), nullable=False, server_default="human"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("output", sa.Text, nullable=True),
        sa.Column("error_msg", sa.Text, nullable=True),
        sa.Column("extra_data", JSONB, server_default="{}", nullable=False),
    )
    op.create_index("ix_remediation_incident_id", "remediation_actions", ["incident_id"])
    op.create_index("ix_remediation_playbook_run_id", "remediation_actions", ["playbook_run_id"])
    op.create_index("ix_remediation_action_type", "remediation_actions", ["action_type"])
    op.create_index("ix_remediation_status", "remediation_actions", ["status"])

    # k8s_state_snapshots
    op.create_table(
        "k8s_state_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("namespace", sa.String(255), nullable=False),
        sa.Column("resource_kind", sa.String(50), nullable=False),
        sa.Column("resource_name", sa.String(255), nullable=False),
        sa.Column("spec_hash", sa.String(64), nullable=True),
        sa.Column("snapshot_data", JSONB, server_default="{}", nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_k8s_snapshot_namespace", "k8s_state_snapshots", ["namespace"])
    op.create_index("ix_k8s_snapshot_resource_kind", "k8s_state_snapshots", ["resource_kind"])
    op.create_index("ix_k8s_snapshot_captured_at", "k8s_state_snapshots", ["captured_at"])
    op.create_index("ix_k8s_snapshot_resource", "k8s_state_snapshots", ["namespace", "resource_kind", "resource_name"])

    # audit_log
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("initiator", sa.String(100), nullable=False, server_default="unknown"),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("resource_kind", sa.String(50), nullable=True),
        sa.Column("resource_name", sa.String(255), nullable=True),
        sa.Column("namespace", sa.String(255), nullable=True),
        sa.Column("result", sa.String(20), nullable=False, server_default="success"),
        sa.Column("error_msg", sa.Text, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("extra_data", JSONB, server_default="{}", nullable=False),
    )
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("k8s_state_snapshots")
    op.drop_table("remediation_actions")
    op.drop_table("alert_events")
    op.drop_table("incidents")
