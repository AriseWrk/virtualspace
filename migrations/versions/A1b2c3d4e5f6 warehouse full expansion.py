"""warehouse full expansion: prices, reserve, receipts, write_offs, inventory

Revision ID: a1b2c3d4e5f6
Revises: 45595fa3a100
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '7628b30b942a'
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------
    # 1. Расширяем таблицу items
    # ------------------------------------------------------------------
    op.add_column('items', sa.Column('reserved_qty', sa.Float(), nullable=False, server_default='0'))
    op.add_column('items', sa.Column('incoming_qty', sa.Float(), nullable=False, server_default='0'))
    op.add_column('items', sa.Column('cost_price',   sa.Float(), nullable=True,  server_default='0'))
    op.add_column('items', sa.Column('sale_price',   sa.Float(), nullable=True,  server_default='0'))

    # ------------------------------------------------------------------
    # 2. stock_movements — универсальный журнал движений
    # ------------------------------------------------------------------
    op.create_table(
        'stock_movements',
        sa.Column('id',            sa.Integer(),     primary_key=True),
        sa.Column('item_id',       sa.Integer(),     sa.ForeignKey('items.id'),   nullable=False),
        sa.Column('move_type',     sa.String(32),    nullable=False),
        sa.Column('quantity',      sa.Float(),       nullable=False),
        sa.Column('unit_cost',     sa.Float(),       nullable=True),
        sa.Column('from_location', sa.String(128),   nullable=True),
        sa.Column('to_location',   sa.String(128),   nullable=True),
        sa.Column('order_id',      sa.Integer(),     sa.ForeignKey('orders.id'),  nullable=True),
        sa.Column('document_ref',  sa.String(128),   nullable=True),
        sa.Column('notes',         sa.Text(),        nullable=True),
        sa.Column('created_by_id', sa.Integer(),     sa.ForeignKey('users.id'),   nullable=False),
        sa.Column('created_at',    sa.DateTime(),    nullable=True),
    )

    # ------------------------------------------------------------------
    # 3. receipts — заголовки приходований
    # ------------------------------------------------------------------
    op.create_table(
        'receipts',
        sa.Column('id',            sa.Integer(),     primary_key=True),
        sa.Column('number',        sa.String(32),    unique=True, nullable=False),
        sa.Column('supplier',      sa.String(256),   nullable=True),
        sa.Column('status',        sa.String(32),    nullable=False, server_default='draft'),
        sa.Column('notes',         sa.Text(),        nullable=True),
        sa.Column('receipt_date',  sa.DateTime(),    nullable=True),
        sa.Column('created_by_id', sa.Integer(),     sa.ForeignKey('users.id'),   nullable=False),
        sa.Column('created_at',    sa.DateTime(),    nullable=True),
        sa.Column('updated_at',    sa.DateTime(),    nullable=True),
    )

    # ------------------------------------------------------------------
    # 4. receipt_items — строки приходований
    # ------------------------------------------------------------------
    op.create_table(
        'receipt_items',
        sa.Column('id',         sa.Integer(), primary_key=True),
        sa.Column('receipt_id', sa.Integer(), sa.ForeignKey('receipts.id'), nullable=False),
        sa.Column('item_id',    sa.Integer(), sa.ForeignKey('items.id'),    nullable=False),
        sa.Column('quantity',   sa.Float(),   nullable=False),
        sa.Column('unit_cost',  sa.Float(),   nullable=True, server_default='0'),
    )

    # ------------------------------------------------------------------
    # 5. write_offs — заголовки списаний
    # ------------------------------------------------------------------
    op.create_table(
        'write_offs',
        sa.Column('id',            sa.Integer(),   primary_key=True),
        sa.Column('number',        sa.String(32),  unique=True, nullable=False),
        sa.Column('reason',        sa.String(32),  nullable=False, server_default='other'),
        sa.Column('status',        sa.String(32),  nullable=False, server_default='draft'),
        sa.Column('notes',         sa.Text(),      nullable=True),
        sa.Column('created_by_id', sa.Integer(),   sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at',    sa.DateTime(),  nullable=True),
        sa.Column('updated_at',    sa.DateTime(),  nullable=True),
    )

    # ------------------------------------------------------------------
    # 6. write_off_items — строки списаний
    # ------------------------------------------------------------------
    op.create_table(
        'write_off_items',
        sa.Column('id',           sa.Integer(), primary_key=True),
        sa.Column('write_off_id', sa.Integer(), sa.ForeignKey('write_offs.id'), nullable=False),
        sa.Column('item_id',      sa.Integer(), sa.ForeignKey('items.id'),      nullable=False),
        sa.Column('quantity',     sa.Float(),   nullable=False),
    )

    # ------------------------------------------------------------------
    # 7. inventory_checks — сессии инвентаризации
    # ------------------------------------------------------------------
    op.create_table(
        'inventory_checks',
        sa.Column('id',            sa.Integer(),   primary_key=True),
        sa.Column('number',        sa.String(32),  unique=True, nullable=False),
        sa.Column('status',        sa.String(32),  nullable=False, server_default='draft'),
        sa.Column('notes',         sa.Text(),      nullable=True),
        sa.Column('created_by_id', sa.Integer(),   sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at',    sa.DateTime(),  nullable=True),
        sa.Column('finished_at',   sa.DateTime(),  nullable=True),
    )

    # ------------------------------------------------------------------
    # 8. inventory_check_items — строки инвентаризации
    # ------------------------------------------------------------------
    op.create_table(
        'inventory_check_items',
        sa.Column('id',           sa.Integer(),   primary_key=True),
        sa.Column('check_id',     sa.Integer(),   sa.ForeignKey('inventory_checks.id'), nullable=False),
        sa.Column('item_id',      sa.Integer(),   sa.ForeignKey('items.id'),            nullable=False),
        sa.Column('expected_qty', sa.Float(),     nullable=False),
        sa.Column('actual_qty',   sa.Float(),     nullable=True),
        sa.Column('notes',        sa.String(256), nullable=True),
    )


def downgrade():
    op.drop_table('inventory_check_items')
    op.drop_table('inventory_checks')
    op.drop_table('write_off_items')
    op.drop_table('write_offs')
    op.drop_table('receipt_items')
    op.drop_table('receipts')
    op.drop_table('stock_movements')

    op.drop_column('items', 'sale_price')
    op.drop_column('items', 'cost_price')
    op.drop_column('items', 'incoming_qty')
    op.drop_column('items', 'reserved_qty')