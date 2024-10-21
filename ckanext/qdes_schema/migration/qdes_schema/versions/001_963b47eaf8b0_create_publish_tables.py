"""empty message

Revision ID: 963b47eaf8b0
Revises: 
Create Date: 2024-08-23 15:30:06.847105

"""
from alembic import op
import sqlalchemy as sa
import datetime

# revision identifiers, used by Alembic.
revision = '963b47eaf8b0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    engine = op.get_bind()
    inspector = sa.inspect(engine)
    tables = inspector.get_table_names()
    if 'publish_log' not in tables:
        op.create_table(
            'publish_log',
            sa.Column('id', sa.String, primary_key=True),
            sa.Column('dataset_id', sa.String, nullable=False),
            sa.Column('resource_id', sa.String),
            sa.Column('trigger', sa.String, nullable=False),
            sa.Column('destination', sa.String),
            sa.Column('destination_identifier', sa.String),
            sa.Column('action', sa.String),
            sa.Column('date_created', sa.DateTime, default=datetime.datetime.utcnow()),
            sa.Column('date_processed', sa.DateTime),
            sa.Column('status', sa.String, nullable=False),
            sa.Column('details', sa.String),
        )


def downgrade():
    op.drop_table('publish_log')
