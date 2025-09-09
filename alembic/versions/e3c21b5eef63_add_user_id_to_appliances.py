"""add user_id to appliances

Revision ID: e3c21b5eef63
Revises: fe46058a60de
Create Date: 2025-08-22 13:01:59.267298

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3c21b5eef63'
down_revision: Union[str, Sequence[str], None] = 'fe46058a60de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("appliances", schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key(
            'fk_appliances_user',   # give the constraint a name
            'users',                # refer to users table
            ['user_id'],            # local column
            ['id']                  # remote column
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("appliances", schema=None) as batch_op:
        batch_op.drop_constraint('fk_appliances_user', type_='foreignkey')
        batch_op.drop_column('user_id')
