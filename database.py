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
    # === 银行利息系统 ===
    last_interest_claimed = Column(DateTime)    # 上次结算利息时间
    accumulated_interest = Column(Integer, default=0)  # 累计未领取利息
    weapon = Column(String, default=None)     # 装备武器
    attack = Column(Integer, default=0)       # 战力数值
    intimacy = Column(Integer, default=0)     # 好感度
    last_checkin = Column(DateTime)      # 上次签到时间
    last_tarot = Column(DateTime)        # 上次塔罗牌抽取时间
    # === 悬赏任务追踪字段 ===
    daily_chat_count = Column(Integer, default=0)      # 今日聊天条数
    daily_forge_count = Column(Integer, default=0)     # 今日锻造次数
    daily_tarot_count = Column(Integer, default=0)     # 今日占卜次数
    daily_box_count = Column(Integer, default=0)       # 今日盲盒次数
    daily_gift_count = Column(Integer, default=0)      # 今日转赠次数
    last_chat_time = Column(DateTime)                  # 上次聊天时间（连击用）
    chat_combo = Column(Integer, default=0)            # 连续聊天连击数
    items = Column(Text, default="")                  # 道具背包 (逗号分隔存储)
    # === 商店道具效果字段 ===
    lucky_boost = Column(Boolean, default=False)      # 幸运草：下次签到暴击率UP
    shield_active = Column(Boolean, default=False)    # 防御卷轴：下次决斗失败不掉钱
    extra_tarot = Column(Integer, default=0)          # 额外塔罗次数
    extra_gacha = Column(Integer, default=0)          # 额外盲盒次数
    free_forges = Column(Integer, default=0)          # 免费锻造券
    free_forges_big = Column(Integer, default=0)      # 高级锻造券（稀有度UP）
    # === 保底系统 ===
    gacha_pity_counter = Column(Integer, default=0)   # 盲盒保底计数（连续未出SR+次数）
    lose_streak = Column(Integer, default=0)          # 连败计数（用于安慰机制）
    # === 成就系统 ===
    achievements = Column(Text, default="")          # 已完成成就列表（逗号分隔）
    total_checkin_days = Column(Integer, default=0)  # 累计签到天数
    consecutive_checkin = Column(Integer, default=0) # 连续签到天数
    last_checkin_date = Column(DateTime)             # 上次签到日期（用于连续签到计算）
    # === 商店限购字段 ===
    last_box_buy_date = Column(DateTime)             # 上次购买神秘宝箱日期
    daily_box_buy_count = Column(Integer, default=0) # 今日购买神秘宝箱次数

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
    try:
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
        return user
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
