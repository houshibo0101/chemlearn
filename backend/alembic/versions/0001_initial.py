"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-28 22:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """初始版本 - 数据库已存在，此迁移仅用于标记基线"""
    pass


def downgrade() -> None:
    pass
