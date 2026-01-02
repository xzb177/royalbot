"""add_performance_indexes

Revision ID: b4c5e9a52f4d
Revises: 63df8d6e35b5
Create Date: 2026-01-02 05:16:24.362613

添加性能优化索引：
- idx_attack: 战力排行榜
- idx_bank_points: 财富排行榜
- idx_is_vip: VIP用户查询
- idx_win: 胜场排行
- idx_total_earned: 财富成就查询
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4c5e9a52f4d'
down_revision: Union[str, Sequence[str], None] = '63df8d6e35b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库结构"""
    # 创建性能优化索引
    op.create_index('idx_attack', 'bindings', ['attack'])
    op.create_index('idx_bank_points', 'bindings', ['bank_points'])
    op.create_index('idx_is_vip', 'bindings', ['is_vip'])
    op.create_index('idx_win', 'bindings', ['win'])
    op.create_index('idx_total_earned', 'bindings', ['total_earned'])


def downgrade() -> None:
    """回滚数据库结构"""
    op.drop_index('idx_total_earned', table_name='bindings')
    op.drop_index('idx_win', table_name='bindings')
    op.drop_index('idx_is_vip', table_name='bindings')
    op.drop_index('idx_bank_points', table_name='bindings')
    op.drop_index('idx_attack', table_name='bindings')
