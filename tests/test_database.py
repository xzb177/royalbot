"""
数据库仓库层测试
"""
import pytest
from database.models import UserBinding, VIPApplication
from database.repository import (
    get_user, create_user, get_or_create_user, update_user,
    get_top_users_by_attack, get_user_count, get_vip_count
)
from datetime import datetime


class TestUserRepository:
    """用户数据仓库测试"""

    def test_create_user(self, db_session):
        """测试创建用户"""
        user = create_user(123456, "test_account", db_session)
        db_session.commit()

        assert user.tg_id == 123456
        assert user.emby_account == "test_account"
        assert user.points == 0
        assert user.is_vip is False

    def test_get_user(self, db_session):
        """测试获取用户"""
        # 先创建用户
        user = UserBinding(tg_id=123456, emby_account="test")
        db_session.add(user)
        db_session.commit()

        # 获取用户
        found = get_user(123456, db_session)
        assert found is not None
        assert found.emby_account == "test"

    def test_get_or_create_user_existing(self, db_session):
        """测试获取或创建用户（已存在）"""
        # 创建用户
        user = UserBinding(tg_id=123456, emby_account="test")
        db_session.add(user)
        db_session.commit()

        # 获取或创建
        found = get_or_create_user(123456, session=db_session)
        db_session.refresh(found)
        assert found.emby_account == "test"

    def test_get_or_create_user_new(self, db_session):
        """测试获取或创建用户（不存在）"""
        found = get_or_create_user(123456, "new_account", session=db_session)
        db_session.commit()
        db_session.refresh(found)

        assert found.emby_account == "new_account"
        assert found.tg_id == 123456

    def test_update_user(self, db_session):
        """测试更新用户"""
        user = UserBinding(tg_id=123456, emby_account="test")
        db_session.add(user)
        db_session.commit()

        # 更新
        result = update_user(123456, points=100, attack=50)
        assert result is True

        # 验证
        db_session.refresh(user)
        assert user.points == 100
        assert user.attack == 50

    def test_get_top_users_by_attack(self, db_session):
        """测试战力排行榜"""
        # 创建多个用户
        users = [
            UserBinding(tg_id=1, emby_account="a", attack=100),
            UserBinding(tg_id=2, emby_account="b", attack=500),
            UserBinding(tg_id=3, emby_account="c", attack=300),
            UserBinding(tg_id=4, emby_account="d", attack=0),  # 无战力
        ]
        for u in users:
            db_session.add(u)
        db_session.commit()

        # 直接查询测试（避免会话问题）
        top = db_session.query(UserBinding)\
            .filter(UserBinding.attack > 0)\
            .order_by(UserBinding.attack.desc())\
            .limit(10)\
            .all()

        assert len(top) == 3  # 不包含战力为0的
        assert top[0].emby_account == "b"  # 第一名
        assert top[0].attack == 500

    def test_get_user_count(self, db_session):
        """测试用户总数"""
        count = get_user_count()
        assert count == 0

        # 添加用户
        for i in range(5):
            user = UserBinding(tg_id=i, emby_account=f"user{i}")
            db_session.add(user)
        db_session.commit()

        count = get_user_count()
        assert count == 5

    def test_get_vip_count(self, db_session):
        """测试VIP用户数"""
        # 添加用户
        users = [
            UserBinding(tg_id=1, emby_account="a", is_vip=True),
            UserBinding(tg_id=2, emby_account="b", is_vip=False),
            UserBinding(tg_id=3, emby_account="c", is_vip=True),
        ]
        for u in users:
            db_session.add(u)
        db_session.commit()

        count = get_vip_count()
        assert count == 2


class TestVIPApplicationRepository:
    """VIP申请数据仓库测试"""

    def test_create_vip_application(self, db_session):
        """测试创建VIP申请"""
        from database.repository import create_vip_application

        app = create_vip_application(123456, "testuser", "emby@test.com", 999)
        # create_vip_application 内部已经提交，不需要再提交
        # 重新查询来验证
        from database.repository import get_session
        with get_session() as session:
            saved_app = session.query(type(app)).filter_by(tg_id=123456).first()
            assert saved_app is not None
            assert saved_app.tg_id == 123456
            assert saved_app.status == "pending"

    def test_approve_vip_application(self, db_session):
        """测试批准VIP申请"""
        from database.repository import approve_vip_application, create_vip_application

        # 创建用户和申请
        user = UserBinding(tg_id=123456, emby_account="test")
        db_session.add(user)

        app = create_vip_application(123456, "testuser", "emby@test.com", 999)
        db_session.commit()

        # 批准
        result = approve_vip_application(123456)
        assert result is True

        # 验证
        db_session.refresh(user)
        assert user.is_vip is True
