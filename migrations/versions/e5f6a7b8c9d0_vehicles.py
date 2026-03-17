"""vehicles garage module

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'vehicles',
        sa.Column('id',              sa.Integer(),  primary_key=True),
        sa.Column('name',            sa.String(128), nullable=False),
        sa.Column('plate',           sa.String(32),  unique=True, nullable=False),
        sa.Column('year',            sa.Integer(),   nullable=True),
        sa.Column('color',           sa.String(32),  nullable=True),
        sa.Column('status',          sa.String(32),  nullable=False, server_default='available'),
        sa.Column('mileage',         sa.Integer(),   nullable=False, server_default='0'),
        sa.Column('driver_id',       sa.Integer(),   sa.ForeignKey('users.id'), nullable=True),
        sa.Column('sto_date',        sa.Date(),      nullable=True),
        sa.Column('sto_next_date',   sa.Date(),      nullable=True),
        sa.Column('insurance_date',  sa.Date(),      nullable=True),
        sa.Column('inspection_date', sa.Date(),      nullable=True),
        sa.Column('notes',           sa.Text(),      nullable=True),
        sa.Column('created_at',      sa.DateTime(),  nullable=True),
        sa.Column('updated_at',      sa.DateTime(),  nullable=True),
    )

    op.create_table(
        'vehicle_trips',
        sa.Column('id',            sa.Integer(),   primary_key=True),
        sa.Column('vehicle_id',    sa.Integer(),   sa.ForeignKey('vehicles.id'), nullable=False),
        sa.Column('driver_id',     sa.Integer(),   sa.ForeignKey('users.id'),   nullable=True),
        sa.Column('date',          sa.Date(),      nullable=False),
        sa.Column('destination',   sa.String(256), nullable=False),
        sa.Column('purpose',       sa.String(256), nullable=True),
        sa.Column('passengers',    sa.String(256), nullable=True),
        sa.Column('mileage_start', sa.Integer(),   nullable=True),
        sa.Column('mileage_end',   sa.Integer(),   nullable=True),
        sa.Column('departed_at',   sa.DateTime(),  nullable=True),
        sa.Column('arrived_at',    sa.DateTime(),  nullable=True),
        sa.Column('notes',         sa.Text(),      nullable=True),
        sa.Column('created_at',    sa.DateTime(),  nullable=True),
    )

    op.create_table(
        'vehicle_requests',
        sa.Column('id',              sa.Integer(),   primary_key=True),
        sa.Column('vehicle_id',      sa.Integer(),   sa.ForeignKey('vehicles.id'), nullable=True),
        sa.Column('requester_id',    sa.Integer(),   sa.ForeignKey('users.id'),    nullable=False),
        sa.Column('status',          sa.String(32),  nullable=False, server_default='new'),
        sa.Column('planned_date',    sa.Date(),      nullable=False),
        sa.Column('destination',     sa.String(256), nullable=False),
        sa.Column('purpose',         sa.String(256), nullable=True),
        sa.Column('passengers',      sa.Integer(),   nullable=True, server_default='1'),
        sa.Column('notes',           sa.Text(),      nullable=True),
        sa.Column('reviewed_by_id',  sa.Integer(),   sa.ForeignKey('users.id'), nullable=True),
        sa.Column('review_note',     sa.String(256), nullable=True),
        sa.Column('created_at',      sa.DateTime(),  nullable=True),
    )


def downgrade():
    op.drop_table('vehicle_requests')
    op.drop_table('vehicle_trips')
    op.drop_table('vehicles')