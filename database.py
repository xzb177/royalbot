from sqlalchemy import create_engine, Column, Integer, String, Boolean, BigInteger, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class UserBinding(Base):
    __tablename__ = 'bindings'

    tg_id = Column(BigInteger, primary_key=True)
    emby_account = Column(String)
    is_vip = Column(Boolean, default=False)
    win = Column(Integer, default=0)     # 胜场
    lost = Column(Integer, default=0)    # 负场
    points = Column(Integer, default=0)       # 流动魔力 (钱包)
    bank_points = Column(Integer, default=0)  # 库藏魔力 (银行)
    weapon = Column(String, default=None)     # 装备武器
    attack = Column(Integer, default=0)       # 战力数值
    last_checkin = Column(DateTime)      # 上次签到时间
    last_tarot = Column(DateTime)        # 上次塔罗牌抽取时间

class VIPApplication(Base):
    __tablename__ = 'vip_applications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg_id = Column(BigInteger)           # 申请人ID
    username = Column(String)            # 申请人用户名
    emby_account = Column(String)        # Emby账号
    status = Column(String, default='pending')  # pending/approved/rejected
    message_id = Column(Integer)         # 发给管理员的消息ID
    admin_note = Column(Text)            # 管理员备注
    created_at = Column(DateTime, default=datetime.now)
    reviewed_at = Column(DateTime)       # 审核时间

# 初始化数据库
engine = create_engine('sqlite:///data/magic.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def create_or_update_user(tg_id, emby_account=None):
    session = Session()
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
    session.close()
    return user
