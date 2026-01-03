"""
游戏配置文件 - Game Config
集中管理所有游戏数值和魔法数字
修改此处即可调整游戏平衡性
"""
from dataclasses import dataclass
from typing import Dict


# ==========================================
# 抽卡配置
# ==========================================

@dataclass
class GachaConfig:
    """抽卡系统配置"""

    # 稀有度概率
    UR_RATE: float = 0.01          # UR 基础概率 1%
    SSR_RATE: float = 0.04         # SSR 基础概率 4%
    SR_RATE: float = 0.15          # SR 基础概率 15%

    # 评分加成概率
    UR_SCORE_BONUS: float = 0.05   # UR 评分加成 5%
    SSR_SCORE_BONUS: float = 0.10  # SSR 评分加成 10%
    SR_SCORE_BONUS: float = 0.25   # SR 评分加成 25%

    # 保底配置
    PITY_COUNT: int = 80           # 保底触发次数
    PITY_START_LEVEL: int = 70     # 保底概率递增起始次数
    PITY_INCREMENT: float = 0.01   # 每抽增加的概率

    # 评分阈值
    UR_SCORE_THRESHOLD: float = 8.5
    SSR_SCORE_THRESHOLD: float = 7.5
    SR_SCORE_THRESHOLD: float = 6.5
    R_SCORE_THRESHOLD: float = 4.0
    CURSED_SCORE_THRESHOLD: float = 4.0
    CURSED_RATE: float = 0.15      # 低评分变诅咒概率

    # 返利
    UR_REFUND: int = 500           # UR 返利 MP
    SSR_REFUND: int = 100          # SSR 返利 MP
    SR_REFUND: int = 20            # SR 返利 MP

    # 消耗
    BASE_COST: int = 50            # 基础单抽消耗
    VIP_COST_MULTIPLIER: float = 0.5  # VIP 折扣

    # 每日免费
    DAILY_FREE: bool = True        # 每日免费次数


# ==========================================
# 决斗配置
# ==========================================

@dataclass
class DuelConfig:
    """决斗系统配置"""

    # 赌注限制
    MIN_BET: int = 10              # 最小赌注
    MAX_BET: int = 10000           # 最大赌注
    DEFAULT_BET: int = 50          # 默认赌注

    # 胜率计算
    BASE_WIN_RATE: float = 0.5     # 基础胜率 50%
    POWER_DIFF_FACTOR: float = 3000  # 每3000战力差距影响
    POWER_DIFF_BONUS: float = 0.25    # 战力差距最大加成

    # VIP 加成
    VIP_CHALLENGE_BONUS: float = 0.05  # VIP 挑战方 +5%
    VIP_DEFENSE_PENALTY: float = 0.03  # VIP 应战方 -3%

    # 胜率限制
    MIN_WIN_RATE: float = 0.15     # 最低胜率 15%
    MAX_WIN_RATE: float = 0.85     # 最高胜率 85%

    # 超时
    DUEL_TIMEOUT: int = 60         # 决斗超时秒数
    ACCEPT_TIMEOUT: int = 60       # 应战超时秒数

    # 败者安慰
    CONSOLATION_RATE: float = 0.1  # 赌注的 10%
    CONSOLATION_MAX: int = 20      # 最大安慰奖
    CONSOLATION_STREAK: int = 3    # 连败触发额外安慰
    CONSOLATION_STREAK_BONUS: int = 30  # 连败额外安慰

    # 连胜奖励
    STREAK_START: int = 5          # 连胜奖励起始场数
    STREAK_BONUS_PER: int = 5      # 每场连胜奖励 MP

    # 战力提升概率
    POWER_UP_RATE: float = 0.15    # 胜利后战力提升概率
    POWER_UP_MIN: int = 1          # 最小提升
    POWER_UP_MAX: int = 3          # 最大提升


# ==========================================
# 锻造配置
# ==========================================

@dataclass
class ForgeConfig:
    """锻造系统配置"""

    # 消耗
    BASE_COST: int = 150           # 基础锻造消耗
    VIP_COST_MULTIPLIER: float = 0.5  # VIP 折扣

    # 大锻造锤
    BIG_COST: int = 500            # 大锻造锤消耗
    BIG_VIP_COST: int = 250        # VIP 大锻造锤消耗

    # 保底
    PITY_R_PLUS: int = 10          # 10次必出 R+
    PITY_SR_PLUS: int = 30         # 30次必出 SR+

    # 稀有度分布（大锻造锤）
    MYTHIC_RATE: float = 0.03      # 神器 3%
    LEGENDARY_RATE: float = 0.09   # 传说 9% (累计12%)
    EPIC_RATE: float = 0.20        # 史诗 20% (累计32%)
    COMMON_RATE: float = 0.55      # 普通 55% (累计87%)
    TRASH_RATE: float = 0.13       # 咸鱼 13% (累计100%)


# ==========================================
# 签到配置
# ==========================================

@dataclass
class CheckinConfig:
    """签到系统配置"""

    # 奖励
    MIN_REWARD: int = 15            # 最小签到奖励
    MAX_REWARD: int = 25            # 最大签到奖励
    VIP_MULTIPLIER: float = 1.5     # VIP 倍率

    # 暴击
    CRIT_RATE: float = 0.1          # 基础暴击率 10%
    CRIT_MULTIPLIER: float = 2.0    # 暴击倍率
    VIP_CRIT_BONUS: float = 0.05    # VIP 额外暴击率

    # 连续签到进度条
    STREAK_CYCLE: int = 10          # 进度条周期（天）
    STREAK_BONUS: int = 50          # 完成周期奖励

    # 随机掉落
    DROP_RATE: float = 0.3          # 道具掉落率


# ==========================================
# 战力突破配置
# ==========================================

@dataclass
class BreakthroughConfig:
    """战力突破系统配置"""

    # VIP 折扣
    VIP_COST_MULTIPLIER: float = 0.7

    # 成功率
    BASE_SUCCESS_RATE: float = 0.5  # 基础成功率 50%
    LEVEL_PENALTY: float = 0.03     # 每级成功率降低
    VIP_BONUS: float = 0.1          # VIP 额外成功率
    MIN_SUCCESS_RATE: float = 0.1   # 最低成功率
    MAX_SUCCESS_RATE: float = 0.95  # 最高成功率

    # 失败返还
    FAILURE_REFUND_RATE: float = 0.3  # 失败返还 30%

    # 等级配置
    MAX_LEVEL: int = 10             # 最大突破等级


# 突破等级表
BREAKTHROUGH_LEVELS = {
    1: {"name": "初窥门径", "cost": 500, "power": 50, "emoji": "🌱"},
    2: {"name": "渐入佳境", "cost": 1000, "power": 100, "emoji": "🌿"},
    3: {"name": "炉火纯青", "cost": 2000, "power": 200, "emoji": "🔥"},
    4: {"name": "登堂入室", "cost": 4000, "power": 350, "emoji": "⚡"},
    5: {"name": "出神入化", "cost": 8000, "power": 500, "emoji": "💫"},
    6: {"name": "融会贯通", "cost": 15000, "power": 750, "emoji": "🌟"},
    7: {"name": "超凡入圣", "cost": 30000, "power": 1000, "emoji": "✨"},
    8: {"name": "法相天地", "cost": 50000, "power": 1500, "emoji": "🌌"},
    9: {"name": "万法归一", "cost": 100000, "power": 2000, "emoji": "🌠"},
    10: {"name": "破碎虚空", "cost": 200000, "power": 3000, "emoji": "🌈"},
}


# ==========================================
# 公会配置
# ==========================================

@dataclass
class GuildConfig:
    """公会系统配置"""

    # 创建公会
    CREATE_COST: int = 5000         # 创建费用
    VIP_COST_MULTIPLIER: float = 0.7  # VIP 折扣

    # 名称限制
    NAME_MIN_LEN: int = 2
    NAME_MAX_LEN: int = 12

    # 成员限制
    BASE_MAX_MEMBERS: int = 20      # 1级公会最大成员
    MEMBERS_PER_LEVEL: int = 10     # 每级增加成员


# 公会等级福利
GUILD_LEVELS = {
    1: {"name": "初级公会", "exp": 0, "max_members": 20, "checkin_bonus": 0},
    2: {"name": "中级公会", "exp": 1000, "max_members": 30, "checkin_bonus": 5},
    3: {"name": "高级公会", "exp": 5000, "max_members": 40, "checkin_bonus": 10, "forge_discount": 0.9},
    4: {"name": "精英公会", "exp": 15000, "max_members": 50, "checkin_bonus": 15, "forge_discount": 0.85},
    5: {"name": "传奇公会", "exp": 50000, "max_members": 60, "checkin_bonus": 20, "forge_discount": 0.7, "daily_gift": True},
    6: {"name": "史诗公会", "exp": 100000, "max_members": 70, "checkin_bonus": 30, "gacha_discount": 0.9},
    7: {"name": "神话公会", "exp": 200000, "max_members": 80, "checkin_bonus": 40, "gacha_discount": 0.8},
    8: {"name": "圣域公会", "exp": 500000, "max_members": 90, "checkin_bonus": 50, "all_discount": 0.8},
    9: {"name": "神域公会", "exp": 1000000, "max_members": 100, "checkin_bonus": 75, "all_discount": 0.7},
    10: {"name": "终极公会", "exp": 2000000, "max_members": 120, "checkin_bonus": 100, "all_discount": 0.5},
}


# ==========================================
# 外观配置
# ==========================================

# 头像框配置
AVATAR_FRAMES = {
    "default": {"name": "默认", "emoji": "⬜", "price": 0, "rarity": "N"},
    "bronze": {"name": "青铜边框", "emoji": "🟫", "price": 0, "rarity": "N"},
    "silver": {"name": "白银边框", "emoji": "⚪", "price": 500, "rarity": "R"},
    "gold": {"name": "黄金边框", "emoji": "🟡", "price": 1000, "rarity": "SR"},
    "fire": {"name": "烈焰边框", "emoji": "🔥", "price": 2000, "rarity": "SR"},
    "ice": {"name": "冰霜边框", "emoji": "❄️", "price": 2000, "rarity": "SR"},
    "diamond": {"name": "钻石边框", "emoji": "💎", "price": 3000, "rarity": "SSR"},
    "rainbow": {"name": "彩虹边框", "emoji": "🌈", "price": 5000, "rarity": "UR"},
    "void": {"name": "虚空边框", "emoji": "🌌", "price": 10000, "rarity": "UR"},
}

# 称号配置
TITLES = {
    "novice": {"name": "见习魔法师", "emoji": "🌱", "price": 0, "rarity": "N"},
    "warrior": {"name": "勇士", "emoji": "⚔️", "price": 300, "rarity": "R"},
    "champion": {"name": "冠军", "emoji": "🏆", "price": 1000, "rarity": "SR"},
    "lucky": {"name": "欧皇", "emoji": "🍀", "price": 2000, "rarity": "SR"},
    "legend": {"name": "传奇", "emoji": "🌟", "price": 3000, "rarity": "SSR"},
    "rich": {"name": "大富翁", "emoji": "💰", "price": 5000, "rarity": "UR"},
    "emperor": {"name": "皇帝", "emoji": "👑", "price": 10000, "rarity": "UR"},
}


# ==========================================
# VIP 配置
# ==========================================

@dataclass
class VIPConfig:
    """VIP 系统配置"""

    # 签到加成
    CHECKIN_MULTIPLIER: float = 1.5

    # 银行利率
    NORMAL_INTEREST_RATE: float = 0.005  # 0.5%
    VIP_INTEREST_RATE: float = 0.01       # 1%
    INTEREST_CAP_NORMAL: int = 50         # 普通用户上限
    INTEREST_CAP_VIP: int = 100           # VIP 上限

    # 商店折扣
    SHOP_DISCOUNT: float = 0.5            # 5折

    # 决斗加成
    DUEL_POWER_BONUS: float = 0.05        # +5% 战力

    # 免费次数
    EXTRA_WHEEL_SPIN: int = 1             # 额外转盘次数


# ==========================================
# 经济配置
# ==========================================

@dataclass
class EconomyConfig:
    """经济系统配置"""

    # 新手礼包
    NEWBIE_PACKAGE: int = 100            # 新手礼包 MP

    # 任务奖励
    TASK_MIN_REWARD: int = 15             # 最小任务奖励
    TASK_MAX_REWARD: int = 50             # 最大任务奖励
    TASK_VIP_BONUS: float = 1.5           # VIP 奖励倍率
    TASK_REFRESH_COST: int = 20           # 刷新任务花费

    # 悬赏任务
    BOUNTY_MIN_REWARD: int = 40           # 最小悬赏奖励
    BOUNTY_MAX_REWARD: int = 150          # 最大悬赏奖励

    # 转盘
    WHEEL_DAILY_FREE: int = 1             # 每日免费次数
    WHEEL_VIP_EXTRA: int = 1              # VIP 额外次数

    # 银行
    BANK_TRANSFER_FEE: float = 0.05       # 转账手续费（普通用户）

    # 转赠限制
    GIFT_DAILY_LIMIT: int = 5             # 每日转赠次数限制


# ==========================================
# 全局配置实例
# ==========================================

gacha = GachaConfig()
duel = DuelConfig()
forge = ForgeConfig()
checkin = CheckinConfig()
breakthrough = BreakthroughConfig()
guild = GuildConfig()
vip = VIPConfig()
economy = EconomyConfig()


# ==========================================
# 配置验证
# ==========================================

def validate_config() -> None:
    """验证配置的合理性"""
    errors = []

    # 验证概率
    if not (0 <= gacha.UR_RATE <= 1):
        errors.append(f"UR_RATE must be between 0 and 1, got {gacha.UR_RATE}")
    if not (0 <= duel.MIN_WIN_RATE <= duel.MAX_WIN_RATE <= 1):
        errors.append("WIN_RATE configuration invalid")

    # 验证数值
    if duel.MIN_BET > duel.MAX_BET:
        errors.append(f"MIN_BET ({duel.MIN_BET}) > MAX_BET ({duel.MAX_BET})")
    if forge.PITY_SR_PLUS <= forge.PITY_R_PLUS:
        errors.append("PITY_SR_PLUS must be > PITY_R_PLUS")

    if errors:
        raise ValueError(f"Config validation failed:\n" + "\n".join(errors))


# 启动时验证配置
try:
    validate_config()
except ValueError as e:
    print(f"⚠️ 配置验证失败: {e}")
