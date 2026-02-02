"""Initial migration - create tables

Revision ID: 001
Revises: 
Create Date: 2026-02-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel_type", sa.String(20), nullable=False, index=True),
        sa.Column("channel_user_id", sa.String(255), nullable=False, index=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("preferred_model", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("channel_type", "channel_user_id", name="uq_channel_user"),
    )

    # Create conversations table
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("channel_type", sa.String(20), nullable=False, index=True),
        sa.Column("model_override", sa.String(50), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_activity",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("metadata", postgresql.JSON, server_default="{}", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # Create messages table
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id", postgresql.UUID(as_uuid=True), nullable=False, index=True
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("model_used", sa.String(50), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("metadata", postgresql.JSON, server_default="{}", nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
    )

    # Create channel_configs table
    op.create_table(
        "channel_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel_type", sa.String(20), nullable=False, unique=True, index=True),
        sa.Column("default_model", sa.String(50), nullable=False),
        sa.Column("settings", postgresql.JSON, server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create additional indexes for performance
    op.create_index(
        "idx_messages_conversation_timestamp",
        "messages",
        ["conversation_id", "timestamp"],
    )
    op.create_index(
        "idx_conversations_user_activity",
        "conversations",
        ["user_id", "last_activity"],
    )


def downgrade() -> None:
    op.drop_index("idx_conversations_user_activity", table_name="conversations")
    op.drop_index("idx_messages_conversation_timestamp", table_name="messages")
    op.drop_table("channel_configs")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("users")
