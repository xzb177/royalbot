"""
数据访问层 (Repository Pattern)
封装所有数据库操作，提供统一的接口

性能优化：
- SQLite 连接池配置
- 自动重连机制
- 会话缓存优化
"""
from contextlib import contextmanager
from typing import Optional, List
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool
from config import Config
from database.models import Base, UserBinding, VIPApplication


# === 数据库连接管理（性能优化） ===

if Config.DB_TYPE == "sqlite":
    # SQLite 优化配置
    engine = create_engine(
        Config.DB_URL,
        echo=Config.DB_ECHO,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,  # 30秒超时
        },
        poolclass=StaticPool,  # SQLite 使用静态池
    )

    # SQLite 性能优化 PRAGMA
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """设置 SQLite 性能优化参数"""
        cursor = dbapi_conn.cursor()
        # WAL 模式 - 允许读写并发
        cursor.execute("PRAGMA journal_mode=WAL")
        # 同步模式 - NORMAL 平衡性能和安全
        cursor.execute("PRAGMA synchronous=NORMAL")
        # 缓存大小 - 增加到 64MB
        cursor.execute("PRAGMA cache_size=-64000")
        # 临时存储在内存中
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

else:
    # PostgreSQL/MySQL 配置
    engine = create_engine(
        Config.DB_URL,
        echo=Config.DB_ECHO,
        poolclass=QueuePool,
        pool_size=10,           # 连接池大小
        max_overflow=20,        # 最大溢出连接数
        pool_timeout=30,        # 获取连接超时
        pool_recycle=3600,      # 连接回收时间（1小时）
        pool_pre_ping=True,     # 连接健康检查
    )

# 创建所有表
Base.metadata.create_all(engine)

# 会话工厂优化
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False  # 避免延迟加载问题，提升性能
)


@contextmanager
def get_session():
    """
    获取数据库会话的上下文管理器
    用法:
        with get_session() as session:
            user = session.query(UserBinding).first()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session_raw() -> Session:
    """
    获取原始数据库会话（需手动管理）
    用于需要跨函数传递会话的场景
    """
    return SessionLocal()


# === 用户数据操作 ===

def get_user(tg_id: int, session: Optional[Session] = None) -> Optional[UserBinding]:
    """获取用户"""
    if session:
        return session.query(UserBinding).filter_by(tg_id=tg_id).first()
    with get_session() as session:
        return session.query(UserBinding).filter_by(tg_id=tg_id).first()


def create_user(tg_id: int, emby_account: Optional[str] = None, session: Optional[Session] = None) -> UserBinding:
    """创建新用户"""
    user = UserBinding(tg_id=tg_id, emby_account=emby_account)
    if session:
        session.add(user)
        session.flush()
    else:
        with get_session() as session:
            session.add(user)
            session.flush()
    return user


def get_or_create_user(tg_id: int, emby_account: Optional[str] = None, session: Optional[Session] = None) -> UserBinding:
    """获取或创建用户（如果不存在）"""
    user = get_user(tg_id, session)
    if not user:
        user = create_user(tg_id, emby_account, session)
    return user


def update_user(tg_id: int, **kwargs) -> bool:
    """更新用户字段"""
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=tg_id).first()
        if not user:
            return False
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        return True


def save_user(user: UserBinding, session: Optional[Session] = None) -> bool:
    """保存用户修改"""
    try:
        if session:
            session.commit()
        else:
            # 用户是从其他会话获取的，需要合并到当前会话
            with get_session() as session:
                session.merge(user)
        return True
    except Exception:
        return False


def get_all_users(order_by: Optional[str] = None, limit: Optional[int] = None) -> List[UserBinding]:
    """获取所有用户"""
    with get_session() as session:
        query = session.query(UserBinding)
        if order_by:
            query = query.order_by(order_by)
        if limit:
            query = query.limit(limit)
        return query.all()


def get_top_users_by_attack(limit: int = 10) -> List[UserBinding]:
    """获取战力排行榜"""
    with get_session() as session:
        return session.query(UserBinding)\
            .filter(UserBinding.attack > 0)\
            .order_by(UserBinding.attack.desc())\
            .limit(limit)\
            .all()


def get_top_users_by_bank(limit: int = 10) -> List[UserBinding]:
    """获取银行财富排行榜"""
    with get_session() as session:
        return session.query(UserBinding)\
            .order_by(UserBinding.bank_points.desc())\
            .limit(limit)\
            .all()


def get_users_by_vip(is_vip: bool = True) -> List[UserBinding]:
    """获取VIP/普通用户列表"""
    with get_session() as session:
        return session.query(UserBinding)\
            .filter_by(is_vip=is_vip)\
            .all()


def get_user_count() -> int:
    """获取用户总数"""
    with get_session() as session:
        return session.query(UserBinding).count()


def get_vip_count() -> int:
    """获取VIP用户数"""
    with get_session() as session:
        return session.query(UserBinding).filter_by(is_vip=True).count()


# === VIP申请操作 ===

def create_vip_application(tg_id: int, username: str, emby_account: str, message_id: int) -> VIPApplication:
    """创建VIP申请"""
    app = VIPApplication(
        tg_id=tg_id,
        username=username,
        emby_account=emby_account,
        message_id=message_id,
        status='pending'
    )
    with get_session() as session:
        session.add(app)
        session.flush()
    return app


def get_pending_applications() -> List[VIPApplication]:
    """获取所有待审核申请"""
    with get_session() as session:
        return session.query(VIPApplication)\
            .filter_by(status='pending')\
            .order_by(VIPApplication.created_at)\
            .all()


def get_application_by_id(app_id: int) -> Optional[VIPApplication]:
    """根据ID获取申请"""
    with get_session() as session:
        return session.query(VIPApplication).filter_by(id=app_id).first()


def get_application_by_tg_id(tg_id: int) -> Optional[VIPApplication]:
    """根据用户ID获取最新申请"""
    with get_session() as session:
        return session.query(VIPApplication)\
            .filter_by(tg_id=tg_id)\
            .order_by(VIPApplication.created_at.desc())\
            .first()


def update_application_status(app_id: int, status: str, admin_note: Optional[str] = None) -> bool:
    """更新申请状态"""
    with get_session() as session:
        app = session.query(VIPApplication).filter_by(id=app_id).first()
        if not app:
            return False
        app.status = status
        if admin_note:
            app.admin_note = admin_note
        return True


def approve_vip_application(tg_id: int) -> bool:
    """批准VIP申请（同时更新用户状态）"""
    with get_session() as session:
        # 更新用户VIP状态
        user = session.query(UserBinding).filter_by(tg_id=tg_id).first()
        if not user:
            return False
        user.is_vip = True

        # 更新申请状态
        pending_apps = session.query(VIPApplication)\
            .filter_by(tg_id=tg_id, status='pending')\
            .all()
        for app in pending_apps:
            app.status = 'approved'

        return True


def cancel_user_pending_applications(tg_id: int) -> int:
    """取消用户所有待审核申请（重新绑定时使用）"""
    with get_session() as session:
        count = session.query(VIPApplication)\
            .filter_by(tg_id=tg_id, status='pending')\
            .delete()
        return count


# === 兼容旧版函数 ===

def create_or_update_user(tg_id, emby_account=None) -> UserBinding:
    """
    兼容旧版函数
    获取或创建用户，更新 emby_account
    """
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=tg_id).first()
        if not user:
            user = UserBinding(tg_id=tg_id, emby_account=emby_account)
            session.add(user)
        else:
            # 如果用户更新了 emby_account，清除该用户之前的待审核 VIP 申请
            if emby_account and user.emby_account != emby_account:
                user.emby_account = emby_account
                # 清除该用户之前的待审核申请
                session.query(VIPApplication).filter_by(
                    tg_id=tg_id,
                    status='pending'
                ).delete()
            elif emby_account:
                user.emby_account = emby_account
        session.commit()
        session.refresh(user)
        return user
