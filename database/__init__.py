"""
数据库包统一导出
提供简洁的导入接口

使用方式:
    # 方式1: 直接从 database 导入（推荐）
    from database import UserBinding, VIPApplication, get_user, get_or_create_user

    # 方式2: 分层导入
    from database.models import UserBinding
    from database.repository import get_user, get_or_create_user
"""

# === 模型类 ===
from database.models import Base, UserBinding, VIPApplication, RedPacket

# === 数据库会话 ===
from database.repository import (
    get_session,
    get_session_raw,
    SessionLocal,
    engine
)

# 向后兼容：Session 别名
Session = SessionLocal

# === 用户操作 ===
from database.repository import (
    get_user,
    create_user,
    get_or_create_user,
    update_user,
    save_user,
    get_all_users,
    get_top_users_by_attack,
    get_top_users_by_bank,
    get_users_by_vip,
    get_user_count,
    get_vip_count
)

# === VIP申请操作 ===
from database.repository import (
    create_vip_application,
    get_pending_applications,
    get_application_by_id,
    get_application_by_tg_id,
    update_application_status,
    approve_vip_application,
    cancel_user_pending_applications
)

# === 兼容旧版 ===
from database.repository import create_or_update_user


__all__ = [
    # 模型
    'Base',
    'UserBinding',
    'VIPApplication',
    'RedPacket',

    # 会话
    'get_session',
    'get_session_raw',
    'SessionLocal',
    'Session',  # 向后兼容
    'engine',

    # 用户操作
    'get_user',
    'create_user',
    'get_or_create_user',
    'update_user',
    'save_user',
    'get_all_users',
    'get_top_users_by_attack',
    'get_top_users_by_bank',
    'get_users_by_vip',
    'get_user_count',
    'get_vip_count',

    # VIP申请操作
    'create_vip_application',
    'get_pending_applications',
    'get_application_by_id',
    'get_application_by_tg_id',
    'update_application_status',
    'approve_vip_application',
    'cancel_user_pending_applications',

    # 兼容旧版
    'create_or_update_user',
]
