"""add tenant query model and enums

Revision ID: aa2d3df460bd
Revises: bec6e2119756
Create Date: 2025-09-16 10:35:03.620034

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa2d3df460bd'
down_revision: Union[str, Sequence[str], None] = 'bec6e2119756'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Upgrade schema."""
    # First, create the ENUM type explicitly (sa.Enum alone doesn’t always work cleanly with alter_column)
    query_status_enum = sa.Enum('pending', 'resolved', name='querystatus')
    query_status_enum.create(op.get_bind(), checkfirst=True)

    # Then alter the column with USING clause
    op.execute(
        "ALTER TABLE tenant_queries ALTER COLUMN status TYPE querystatus USING status::text::querystatus"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Convert back to VARCHAR first
    op.execute(
        "ALTER TABLE tenant_queries ALTER COLUMN status TYPE VARCHAR USING status::text"
    )

    # Then drop the ENUM type
    op.execute("DROP TYPE querystatus")
