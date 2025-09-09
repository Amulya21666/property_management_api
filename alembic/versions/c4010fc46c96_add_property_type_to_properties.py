"""Add property_type to properties

Revision ID: c4010fc46c96
Revises: 114f47ddfec9
Create Date: 2025-09-01 12:33:10.299105

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4010fc46c96'
down_revision: Union[str, Sequence[str], None] = '114f47ddfec9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Step 1: Add column as nullable
    op.add_column('properties', sa.Column('property_type', sa.String(), nullable=True))

    # Step 2: Set default for existing rows
    op.execute("UPDATE properties SET property_type = 'Apartment' WHERE property_type IS NULL")



def downgrade():
    op.drop_column('properties', 'property_type')
