"""batch queue: leases, attempts and stored uploads

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("batch_jobs", sa.Column("worker_id", sa.String(length=128), nullable=True))
    op.add_column(
        "batch_jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "batch_jobs",
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "batch_uploads",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["batch_jobs.id"],
            name=op.f("fk_batch_uploads_job_id_batch_jobs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("job_id", name=op.f("pk_batch_uploads")),
    )


def downgrade() -> None:
    op.drop_table("batch_uploads")
    op.drop_column("batch_jobs", "attempts")
    op.drop_column("batch_jobs", "lease_expires_at")
    op.drop_column("batch_jobs", "worker_id")
