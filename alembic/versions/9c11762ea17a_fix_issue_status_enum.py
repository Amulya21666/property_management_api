"""fix issue status enum

Revision ID: 9c11762ea17a
Revises: 543a535007b5
Create Date: 2025-09-18 15:14:51.927072

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9c11762ea17a'
down_revision: Union[str, Sequence[str], None] = '543a535007b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Create the ENUM type first
    issue_status_enum = sa.Enum('pending', 'assigned', 'repaired', 'paid', name='issuestatus')
    issue_status_enum.create(op.get_bind(), checkfirst=True)

    # Convert the column using explicit cast
    op.execute("ALTER TABLE issues ALTER COLUMN status TYPE issuestatus USING status::text::issuestatus")

def downgrade():
    # Revert back to VARCHAR
    op.execute("ALTER TABLE issues ALTER COLUMN status TYPE VARCHAR USING status::text")
    sa.Enum(name='issuestatus').drop(op.get_bind(), checkfirst=True)
