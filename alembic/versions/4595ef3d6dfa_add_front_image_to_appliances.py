"""Add front_image to appliances

Revision ID: 4595ef3d6dfa
Revises: 5c099865c2f6
Create Date: 2025-08-22 10:28:07.217901

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4595ef3d6dfa'
down_revision: Union[str, Sequence[str], None] = '5c099865c2f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Since front_image already exists, skip adding it
    # Also, SQLite cannot alter column types easily, so skip altering 'image'
    pass


def downgrade() -> None:
    # Optional: you can drop 'front_image' if needed
    # But do not try to alter 'image' back
    pass

