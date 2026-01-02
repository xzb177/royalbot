"""
测试配置文件
"""
import os
import sys
import tempfile

# 设置测试环境
os.environ["DB_TYPE"] = "sqlite"
os.environ["DB_PATH"] = ":memory:"  # 内存数据库

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


import pytest
from database.models import Base
from database.repository import engine, SessionLocal
from telegram import Update, User, Chat, Message
from datetime import datetime


@pytest.fixture(scope="function")
def db_session():
    """创建测试用的数据库会话"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        # 清理所有表
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_user():
    """模拟 Telegram 用户"""
    return User(
        id=123456,
        is_bot=False,
        first_name="Test",
        username="testuser"
    )


@pytest.fixture
def mock_chat():
    """模拟 Telegram 聊天"""
    return Chat(
        id=123456,
        type="private"
    )


@pytest.fixture
def mock_message(mock_user, mock_chat):
    """模拟 Telegram 消息"""
    return Message(
        message_id=1,
        date=datetime.now(),
        chat=mock_chat,
        from_user=mock_user,
        text="/test"
    )


@pytest.fixture
def mock_update(mock_message):
    """模拟 Telegram Update"""
    return Update(
        update_id=1,
        message=mock_message
    )
