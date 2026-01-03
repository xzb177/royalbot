#!/usr/bin/env python3
"""
SQLite -> PostgreSQL 数据迁移脚本
执行方式: docker exec royalbot python scripts/migrate_to_postgres.py
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from database.models import Base, UserBinding, VIPApplication, RedPacket
from datetime import datetime
import json


def migrate_model(model_class, sqlite_session, pg_session, model_name):
    """通用的模型迁移函数"""
    print(f"\n📦 迁移 {model_name}...")

    # 获取 SQLite 数据
    items = sqlite_session.query(model_class).all()
    print(f"   发现 {len(items)} 条记录")

    if len(items) == 0:
        print(f"   ⚠️ 没有数据，跳过")
        return 0

    # 获取表名
    table_name = model_class.__table__.name

    # 清空 PostgreSQL 中的现有数据
    pg_session.execute(text(f"DELETE FROM {table_name}"))
    pg_session.commit()

    migrated = 0
    for item in items:
        # 获取所有列名
        columns = [c.name for c in model_class.__table__.columns]

        # 动态构建数据字典
        item_data = {}
        for col in columns:
            if hasattr(item, col):
                value = getattr(item, col)
                # 处理 None 值
                item_data[col] = value

        # 创建新对象
        new_item = model_class(**item_data)
        pg_session.add(new_item)
        migrated += 1

        # 每10条提交一次
        if migrated % 10 == 0:
            print(f"   已迁移 {migrated}/{len(items)} 条")
            pg_session.commit()

    pg_session.commit()
    print(f"✅ {model_name} 迁移完成: {migrated} 条")
    return migrated


def migrate_sqlite_to_postgres():
    """将 SQLite 数据迁移到 PostgreSQL"""

    # SQLite 源数据库
    sqlite_engine = create_engine("sqlite:///data/magic.db", echo=False)

    # PostgreSQL 目标数据库
    pg_url = os.getenv("DB_URL", "postgresql://royalbot:RoyalBot_2026_Secure_Key_8847@postgres:5432/royalbot")
    pg_engine = create_engine(pg_url, echo=False)

    print("=" * 50)
    print("🔄 开始迁移 SQLite -> PostgreSQL")
    print("=" * 50)

    # 创建 PostgreSQL 表结构
    print("\n📋 创建 PostgreSQL 表结构...")
    Base.metadata.create_all(pg_engine)
    print("✅ 表结构创建完成")

    # 创建会话
    SessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)
    sqlite_session = SessionLocal()

    PgSessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    pg_session = PgSessionLocal()

    try:
        # 检查 SQLite 中的数据
        total_users = sqlite_session.query(UserBinding).count()
        print(f"\n📊 SQLite 数据统计:")
        print(f"   用户: {total_users}")
        print(f"   VIP申请: {sqlite_session.query(VIPApplication).count()}")
        print(f"   红包: {sqlite_session.query(RedPacket).count()}")

        if total_users == 0:
            print("\n⚠️ SQLite 中没有用户数据，跳过迁移")
            return

        # 迁移各表
        migrate_model(UserBinding, sqlite_session, pg_session, "用户数据")
        migrate_model(VIPApplication, sqlite_session, pg_session, "VIP 申请")
        migrate_model(RedPacket, sqlite_session, pg_session, "红包")

    except Exception as e:
        pg_session.rollback()
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        sqlite_session.close()
        pg_session.close()

    print("\n" + "=" * 50)
    print("✅ 数据迁移完成！")
    print("=" * 50)

    # 验证
    print("\n🔍 验证 PostgreSQL 数据...")
    pg_session = PgSessionLocal()
    user_count = pg_session.query(UserBinding).count()
    vip_count = pg_session.query(UserBinding).filter_by(is_vip=True).count()
    app_count = pg_session.query(VIPApplication).count()
    packet_count = pg_session.query(RedPacket).count()

    print(f"   用户总数: {user_count}")
    print(f"   VIP 用户: {vip_count}")
    print(f"   VIP 申请: {app_count}")
    print(f"   红包数量: {packet_count}")

    # 抽查一个用户数据
    sample_user = pg_session.query(UserBinding).first()
    if sample_user:
        print(f"\n📝 抽查用户 {sample_user.tg_id}:")
        print(f"   points: {sample_user.points}")
        print(f"   is_vip: {sample_user.is_vip}")
        print(f"   emby_account: {sample_user.emby_account}")

    pg_session.close()


if __name__ == "__main__":
    migrate_sqlite_to_postgres()
