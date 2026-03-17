"""project expansion: documents, orders link, designer, created_by, new statuses

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------
    # 1. Расширяем таблицу projects
    # ------------------------------------------------------------------
    op.add_column('projects', sa.Column('designer_id',   sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('projects', sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))

    # engineer_id делаем nullable (раньше было NOT NULL)
    op.alter_column('projects', 'engineer_id', nullable=True)

    # ------------------------------------------------------------------
    # 2. project_documents — документация проектировщика
    # ------------------------------------------------------------------
    op.create_table(
        'project_documents',
        sa.Column('id',             sa.Integer(),     primary_key=True),
        sa.Column('project_id',     sa.Integer(),     sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('doc_type',       sa.String(32),    nullable=False),
        sa.Column('title',          sa.String(256),   nullable=False),
        sa.Column('filename',       sa.String(256),   nullable=False),
        sa.Column('original_name',  sa.String(256),   nullable=False),
        sa.Column('file_size',      sa.Integer(),     nullable=True),
        sa.Column('version',        sa.String(32),    nullable=True),
        sa.Column('notes',          sa.String(512),   nullable=True),
        sa.Column('uploaded_by_id', sa.Integer(),     sa.ForeignKey('users.id'), nullable=False),
        sa.Column('uploaded_at',    sa.DateTime(),    nullable=True),
    )

    # ------------------------------------------------------------------
    # 3. project_orders — привязка заказов склада к проекту
    # ------------------------------------------------------------------
    op.create_table(
        'project_orders',
        sa.Column('id',            sa.Integer(),   primary_key=True),
        sa.Column('project_id',    sa.Integer(),   sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('order_id',      sa.Integer(),   sa.ForeignKey('orders.id'),   nullable=False),
        sa.Column('created_by_id', sa.Integer(),   sa.ForeignKey('users.id'),    nullable=False),
        sa.Column('created_at',    sa.DateTime(),  nullable=True),
        sa.Column('notes',         sa.String(256), nullable=True),
    )


def downgrade():
    op.drop_table('project_orders')
    op.drop_table('project_documents')
    op.drop_column('projects', 'created_by_id')
    op.drop_column('projects', 'designer_id')