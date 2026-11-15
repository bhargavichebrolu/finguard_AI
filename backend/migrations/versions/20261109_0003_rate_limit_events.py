"""rate limit events

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("key", sa.String(length=320), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rate_limit_events")),
    )
    op.create_index(
        "ix_rate_limit_events_key_occurred_at",
        "rate_limit_events",
        ["key", "occurred_at"],
        unique=False,
    )
    op.create_table(
        "rate_limit_windows",
        sa.Column("key", sa.String(length=320), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key", "window_start", name=op.f("pk_rate_limit_windows")),
    )


def downgrade() -> None:
    op.drop_table("rate_limit_windows")
    op.drop_index("ix_rate_limit_events_key_occurred_at", table_name="rate_limit_events")
    op.drop_table("rate_limit_events")
