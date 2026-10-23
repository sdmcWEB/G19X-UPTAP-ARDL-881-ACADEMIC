"""dictamen de revision humana en hallazgos

El abogado confirma o descarta cada hallazgo. Es lo que convierte una lista
propuesta por el sistema en una revisión que alguien firma.

Revision ID: 1ab9c556f128
Revises: 6b06417cde1c
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1ab9c556f128"
down_revision: str | None = "6b06417cde1c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FK_REVISOR = "fk_findings_revisado_por_id_users"

review_status = sa.Enum("PENDIENTE", "CONFIRMADO", "DESCARTADO", name="reviewstatus")


def upgrade() -> None:
    review_status.create(op.get_bind(), checkfirst=True)

    # server_default: sin él, añadir una columna NOT NULL a una tabla que ya
    # tiene hallazgos falla. Los existentes nacen como pendientes, que es la
    # verdad: nadie los ha revisado.
    op.add_column(
        "findings",
        sa.Column("revision", review_status, nullable=False, server_default="PENDIENTE"),
    )
    op.add_column("findings", sa.Column("comentario_revision", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column("revisado_por_id", sa.UUID(), nullable=True))
    op.add_column("findings", sa.Column("revisado_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index(op.f("ix_findings_revision"), "findings", ["revision"], unique=False)
    # Con nombre explícito: una restricción anónima no se puede eliminar.
    op.create_foreign_key(FK_REVISOR, "findings", "users", ["revisado_por_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint(FK_REVISOR, "findings", type_="foreignkey")
    op.drop_index(op.f("ix_findings_revision"), table_name="findings")
    op.drop_column("findings", "revisado_at")
    op.drop_column("findings", "revisado_por_id")
    op.drop_column("findings", "comentario_revision")
    op.drop_column("findings", "revision")
    # El tipo sobrevive a sus columnas: sin esto, volver a aplicar la
    # migración falla con "type already exists".
    review_status.drop(op.get_bind(), checkfirst=True)
