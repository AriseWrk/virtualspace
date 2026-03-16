"""add section fields to service objects

Revision ID: 7628b30b942a
Revises: 45595fa3a100
Create Date: 2026-03-15 23:22:54.616396

"""
from alembic import op
import sqlalchemy as sa


revision = '7628b30b942a'
down_revision = '45595fa3a100'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('service_objects', sa.Column('section', sa.String(length=32), nullable=True))
    op.add_column('service_objects', sa.Column('estimate_sum', sa.Float(), nullable=True))
    op.add_column('service_objects', sa.Column('installation_stage', sa.String(length=32), nullable=True))
    op.add_column('service_objects', sa.Column('handover_date', sa.DateTime(), nullable=True))
    op.add_column('service_objects', sa.Column('contract_number', sa.String(length=128), nullable=True))

    op.execute("UPDATE service_objects SET section = 'service' WHERE section IS NULL")

    op.alter_column('service_objects', 'section', nullable=False)


def downgrade():
    op.drop_column('service_objects', 'contract_number')
    op.drop_column('service_objects', 'handover_date')
    op.drop_column('service_objects', 'installation_stage')
    op.drop_column('service_objects', 'estimate_sum')
    op.drop_column('service_objects', 'section')