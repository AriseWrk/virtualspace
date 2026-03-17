"""app settings table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'app_settings',
        sa.Column('id',    sa.Integer(),    primary_key=True),
        sa.Column('key',   sa.String(64),   unique=True, nullable=False),
        sa.Column('value', sa.Text(),       nullable=True),
        sa.Column('label', sa.String(128),  nullable=True),
    )
    # Начальные значения
    op.execute("""
        INSERT INTO app_settings (key, value, label) VALUES
        ('office_address',  '',  'Адрес офиса (начальная точка маршрута)'),
        ('yandex_maps_key', '',  'Ключ Яндекс Карты JS API'),
        ('yandex_geo_key',  '',  'Ключ Яндекс Геокодер API')
    """)


def downgrade():
    op.drop_table('app_settings')