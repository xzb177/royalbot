"""add_achievement_and_duel_fields

Revision ID: 63df8d6e35b5
Revises:
Create Date: 2026-01-02 05:10:00.032175

添加成就系统和决斗增强相关字段：
- total_earned: 累计获得MP
- total_spent: 累计消费MP
- win_streak: 决斗连胜记录
- last_win_streak_date: 上次连胜日期
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63df8d6e35b5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库结构"""
    # 添加成就相关字段
    op.add_column('bindings', sa.Column('total_earned', sa.Integer(), nullable=True))
    op.add_column('bindings', sa.Column('total_spent', sa.Integer(), nullable=True))

    # 添加决斗连胜字段
    op.add_column('bindings', sa.Column('win_streak', sa.Integer(), nullable=True))
    op.add_column('bindings', sa.Column('last_win_streak_date', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """回滚数据库结构"""
    op.drop_column('bindings', 'last_win_streak_date')
    op.drop_column('bindings', 'win_streak')
    op.drop_column('bindings', 'total_spent')
    op.drop_column('bindings', 'total_earned')
