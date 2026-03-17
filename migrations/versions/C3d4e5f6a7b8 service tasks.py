"""service tasks module

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'service_tasks',
        sa.Column('id',              sa.Integer(),    primary_key=True),
        sa.Column('number',          sa.String(32),   unique=True, nullable=False),
        sa.Column('object_id',       sa.Integer(),    sa.ForeignKey('service_objects.id'), nullable=True),
        sa.Column('object_name',     sa.String(256),  nullable=False),
        sa.Column('object_address',  sa.String(512),  nullable=True),
        sa.Column('work_type',       sa.String(32),   nullable=False, server_default='to'),
        sa.Column('priority',        sa.String(16),   nullable=False, server_default='normal'),
        sa.Column('status',          sa.String(32),   nullable=False, server_default='new'),
        sa.Column('planned_date',    sa.DateTime(),   nullable=True),
        sa.Column('description',     sa.Text(),       nullable=True),
        sa.Column('attachment',      sa.String(256),  nullable=True),
        sa.Column('attachment_name', sa.String(256),  nullable=True),
        sa.Column('created_by_id',   sa.Integer(),    sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at',      sa.DateTime(),   nullable=True),
        sa.Column('updated_at',      sa.DateTime(),   nullable=True),
    )

    op.create_table(
        'service_task_engineers',
        sa.Column('id',          sa.Integer(), primary_key=True),
        sa.Column('task_id',     sa.Integer(), sa.ForeignKey('service_tasks.id'), nullable=False),
        sa.Column('engineer_id', sa.Integer(), sa.ForeignKey('users.id'),         nullable=False),
    )

    op.create_table(
        'service_task_reports',
        sa.Column('id',              sa.Integer(),   primary_key=True),
        sa.Column('task_id',         sa.Integer(),   sa.ForeignKey('service_tasks.id'), nullable=False),
        sa.Column('arrived_at',      sa.DateTime(),  nullable=True),
        sa.Column('departed_at',     sa.DateTime(),  nullable=True),
        sa.Column('verdict',         sa.String(32),  nullable=True),
        sa.Column('notes',           sa.Text(),      nullable=True),
        sa.Column('attachment',      sa.String(256), nullable=True),
        sa.Column('attachment_name', sa.String(256), nullable=True),
        sa.Column('filled_by_id',    sa.Integer(),   sa.ForeignKey('users.id'), nullable=True),
        sa.Column('filled_at',       sa.DateTime(),  nullable=True),
    )


def downgrade():
    op.drop_table('service_task_reports')
    op.drop_table('service_task_engineers')
    op.drop_table('service_tasks')