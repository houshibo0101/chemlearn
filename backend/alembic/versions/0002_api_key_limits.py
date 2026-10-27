"""add api key limits

Revision ID: 0002_api_key_limits
Revises: 0001_initial
Create Date: 2026-09-28 22:05:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0002_api_key_limits'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """给api_keys表增加限额字段"""
    # 检查列是否存在，不存在才添加（兼容已有数据库）
    conn = op.get_bind()
    columns = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(api_keys)")).fetchall()]

    if 'daily_limit' not in columns:
        op.add_column('api_keys', sa.Column('daily_limit', sa.Integer(), nullable=True, server_default='1000'))
    if 'rate_limit_per_minute' not in columns:
        op.add_column('api_keys', sa.Column('rate_limit_per_minute', sa.Integer(), nullable=True, server_default='60'))
    if 'daily_call_count' not in columns:
        op.add_column('api_keys', sa.Column('daily_call_count', sa.Integer(), nullable=True, server_default='0'))
    if 'last_call_date' not in columns:
        op.add_column('api_keys', sa.Column('last_call_date', sa.String(length=10), nullable=True))
    if 'scope' not in columns:
        op.add_column('api_keys', sa.Column('scope', sa.String(length=256), nullable=True, server_default='all'))


def downgrade() -> None:
    pass
