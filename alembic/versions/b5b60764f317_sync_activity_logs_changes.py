"""Sync activity_logs changes"""

revision = 'b5b60764f317'
down_revision =  '456b6e9acbf8' # the ID of the previous migration
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 1. Create a new table with the updated schema
    op.create_table(
        'activity_logs_new',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user', sa.String, nullable=True),  # now nullable
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id')),
        # add other columns here exactly as they exist in the original table
    )

    # 2. Copy the data
    op.execute("""
        INSERT INTO activity_logs_new (id, user, user_id)
        SELECT id, user, user_id FROM activity_logs
    """)

    # 3. Drop the old table
    op.drop_table('activity_logs')

    # 4. Rename new table
    op.rename_table('activity_logs_new', 'activity_logs')

    # Remove the logs.timestamp column change here if it has same issue with SQLite


def downgrade():
    # Implement reverse steps if needed
    pass
