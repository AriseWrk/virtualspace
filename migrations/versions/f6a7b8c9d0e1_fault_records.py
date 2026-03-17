"""fault records knowledge base

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'fault_records',
        sa.Column('id',         sa.Integer(),   primary_key=True),
        sa.Column('title',      sa.String(256), nullable=False),
        sa.Column('category',   sa.String(32),  nullable=False, server_default='other'),
        sa.Column('symptoms',   sa.Text(),      nullable=False),
        sa.Column('solution',   sa.Text(),      nullable=False),
        sa.Column('equipment',  sa.String(256), nullable=True),
        sa.Column('tags',       sa.String(512), nullable=True),
        sa.Column('is_public',  sa.Boolean(),   server_default='true'),
        sa.Column('views',      sa.Integer(),   server_default='0'),
        sa.Column('author_id',  sa.Integer(),   sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(),  nullable=True),
        sa.Column('updated_at', sa.DateTime(),  nullable=True),
    )


def downgrade():
    op.drop_table('fault_records')