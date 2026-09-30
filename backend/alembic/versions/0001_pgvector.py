"""Habilita la extensión pgvector

La extensión tiene que existir antes de que cualquier tabla declare una
columna Vector, así que esta migración va primero y sola.

Revision ID: 0001_pgvector
Revises:
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_pgvector"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
