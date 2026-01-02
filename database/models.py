"""
数据模型层
定义所有 SQLAlchemy 数据库模型

性能优化：为常用查询字段添加索引
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, BigInteger, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class UserBinding(Base):
    """用户数据模型 - 主表"""
    __tablename__ = 'bindings'

    # === 索引定义（性能优化） ===
    __table_args__ = (
        Index('idx_attack', 'attack'),          # 战力排行榜
        Index('idx_bank_points', 'bank_points'), # 财富排行榜
        Index('idx_is_vip', 'is_vip'),          # VIP用户查询
        Index('idx_win', 'win'),                # 胜场排行
        Index('idx_total_earned', 'total_earned'), # 财富成就
    )

    # === 基础字段 ===
    tg_id = Column(BigInteger, primary_key=True)
    emby_account = Column(String)
    is_vip = Column(Boolean, default=False)
    win = Column(Integer, default=0)     # 胜场
    lost = Column(Integer, default=0)    # 负场

    # === 魔力系统 ===
    points = Column(Integer, default=0)       # 流动魔力 (钱包)
    bank_points = Column(Integer, default=0)  # 库藏魔力 (银行)
    last_interest_claimed = Column(DateTime)    # 上次结算利息时间
    accumulated_interest = Column(Integer, default=0)  # 累计未领取利息

    # === 战力系统 ===
    weapon = Column(String, default=None)     # 装备武器
    attack = Column(Integer, default=0)       # 战力数值
    intimacy = Column(Integer, default=0)     # 好感度

    # === 时间记录 ===
    last_checkin = Column(DateTime)      # 上次签到时间
    last_tarot = Column(DateTime)        # 上次塔罗牌抽取时间

    # === 悬赏任务追踪 ===
    daily_chat_count = Column(Integer, default=0)      # 今日聊天条数
    daily_forge_count = Column(Integer, default=0)     # 今日锻造次数
    daily_tarot_count = Column(Integer, default=0)     # 今日占卜次数
    daily_box_count = Column(Integer, default=0)       # 今日盲盒次数
    daily_gift_count = Column(Integer, default=0)      # 今日转赠次数
    last_chat_time = Column(DateTime)                  # 上次聊天时间（连击用）
    chat_combo = Column(Integer, default=0)            # 连续聊天连击数

    # === 背包系统 ===
    items = Column(Text, default="")                  # 道具背包 (逗号分隔存储)

    # === 商店道具效果 ===
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
    total_earned = Column(Integer, default=0)        # 累计获得MP总额（财富成就用）
    total_spent = Column(Integer, default=0)         # 累计消费MP总额（财富成就用）
    win_streak = Column(Integer, default=0)          # 决斗连胜记录
    last_win_streak_date = Column(DateTime)         # 上次连胜日期（重置用）

    # === 商店限购 ===
    last_box_buy_date = Column(DateTime)             # 上次购买神秘宝箱日期
    daily_box_buy_count = Column(Integer, default=0) # 今日购买神秘宝箱次数

    # === 每日任务系统 ===
    task_date = Column(DateTime)                     # 任务刷新日期
    daily_tasks = Column(Text, default="")           # 今日任务列表
    task_progress = Column(Text, default="0,0,0")    # 任务进度

    # === 幸运转盘系统 ===
    last_wheel_date = Column(DateTime)               # 上次转转盘日期
    wheel_spins_today = Column(Integer, default=0)   # 今日已转次数

    # === 在线活跃度系统 ===
    daily_presence_points = Column(Integer, default=0)   # 今日活跃点数
    total_presence_points = Column(Integer, default=0)   # 累计活跃点数
    last_active_time = Column(DateTime)              # 上次活跃时间
    presence_levels_claimed = Column(Text, default="")  # 已领取的活跃等级


class VIPApplication(Base):
    """VIP 申请模型"""
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
