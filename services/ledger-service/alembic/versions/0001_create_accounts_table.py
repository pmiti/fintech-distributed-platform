"""create accounts table

Revision ID: 0001
Revises:
Create Date: 2026-11-27 14:56:05.657298

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("balance", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("balance >= 0", name=op.f("ck_accounts_balance_non_negative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
    )


def downgrade() -> None:
    op.drop_table("accounts")
