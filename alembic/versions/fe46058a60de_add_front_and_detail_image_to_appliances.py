"""add front and detail image to appliances

Revision ID: fe46058a60de
Revises: 4595ef3d6dfa
Create Date: 2025-08-22 12:24:16.782410

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe46058a60de'
down_revision: Union[str, Sequence[str], None] = '4595ef3d6dfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('appliances', sa.Column('front_image', sa.String(), nullable=True))
    op.add_column('appliances', sa.Column('detail_image', sa.String(), nullable=True))

def downgrade():
    op.drop_column('appliances', 'front_image')
    op.drop_column('appliances', 'detail_image')
