"""
幸运事件系统
处理随机暴击、双倍奖励等随机事件
配置：普通（15%双倍，1.5%三倍，0.15%五倍）
[修复记录] - 2026-01-03
- 提升双倍暴击概率从 5% → 10% → 15%（改善玩家体验）
- 提升三倍暴击概率从 0.5% → 1% → 1.5%
- 提升五倍暴击概率从 0.05% → 0.1% → 0.15%
"""

import random
import logging

logger = logging.getLogger(__name__)

# ==========================================
# 🍀 幸运概率配置
# ==========================================

# 普通配置 - 暴击概率（提升后）
LUCKY_RATES = {
    "double": 0.15,      # 15% 双倍（5%→10%→15%）
    "triple": 0.015,     # 1.5% 三倍（0.5%→1%→1.5%）
    "quintuple": 0.0015  # 0.15% 五倍（0.05%→0.1%→0.15%）
}

# VIP 加成 - VIP 用户有更高概率
VIP_LUCKY_BONUS = {
    "double": 0.02,      # VIP 额外 +2% 双倍
    "triple": 0.003,     # VIP 额外 +0.3% 三倍
    "quintuple": 0.0003  # VIP 额外 +0.03% 五倍
}


# ==========================================
# 🎲 幸运检测
# ==========================================

def check_lucky(is_vip: bool = False) -> dict:
    """
    检查是否触发幸运事件

    Args:
        is_vip: 是否VIP用户

    Returns:
        字典，包含倍数和特效信息
        {
            "triggered": bool,      # 是否触发
            "multiplier": int,      # 倍数 (1, 2, 3, 5)
            "effect": str,          # 特效文字
            "tier": str             # 等级名称
        }
    """
    # 获取概率
    double_rate = LUCKY_RATES["double"]
    triple_rate = LUCKY_RATES["triple"]
    quintuple_rate = LUCKY_RATES["quintuple"]

    if is_vip:
        double_rate += VIP_LUCKY_BONUS["double"]
        triple_rate += VIP_LUCKY_BONUS["triple"]
        quintuple_rate += VIP_LUCKY_BONUS["quintuple"]

    # 检查五倍暴击（先检查高倍率）
    if random.random() < quintuple_rate:
        from .feedback_utils import get_crit_effect
        return {
            "triggered": True,
            "multiplier": 5,
            "effect": get_crit_effect(5),
            "tier": "quintuple"
        }

    # 检查三倍暴击
    if random.random() < triple_rate:
        from .feedback_utils import get_crit_effect
        return {
            "triggered": True,
            "multiplier": 3,
            "effect": get_crit_effect(3),
            "tier": "triple"
        }

    # 检查双倍暴击
    if random.random() < double_rate:
        from .feedback_utils import get_crit_effect
        return {
            "triggered": True,
            "multiplier": 2,
            "effect": get_crit_effect(2),
            "tier": "double"
        }

    # 未触发
    return {
        "triggered": False,
        "multiplier": 1,
        "effect": "",
        "tier": "none"
    }


def calculate_lucky_reward(base_reward: int, is_vip: bool = False) -> dict:
    """
    计算幸运奖励

    Args:
        base_reward: 基础奖励
        is_vip: 是否VIP用户

    Returns:
        字典，包含实际奖励和幸运信息
        {
            "base": int,           # 基础奖励
            "actual": int,         # 实际奖励
            "bonus": int,          # 额外奖励
            "multiplier": int,     # 倍数
            "effect": str,         # 特效文字
            "triggered": bool      # 是否触发
        }
    """
    lucky = check_lucky(is_vip)

    multiplier = lucky["multiplier"]
    actual = base_reward * multiplier
    bonus = actual - base_reward

    result = {
        "base": base_reward,
        "actual": actual,
        "bonus": bonus,
        "multiplier": multiplier,
        "effect": lucky["effect"],
        "triggered": lucky["triggered"]
    }

    if lucky["triggered"]:
        logger.info(f"幸运事件触发: {multiplier}倍暴击, 基础={base_reward}, 实际={actual}")

    return result


# ==========================================
# 🎁 特殊掉落系统
# ==========================================

# 各种掉落物品及概率
DROP_TABLE = {
    "lucky_grass": {  # 幸运草
        "rate": 0.05,  # 5%
        "vip_rate": 0.08,  # VIP 8%
        "name": "🍀 幸运草",
        "amount_range": (1, 1),
    },
    "extra_gacha": {  # 盲盒券
        "rate": 0.02,  # 2%
        "vip_rate": 0.03,  # VIP 3%
        "name": "🎰 盲盒券",
        "amount_range": (1, 1),
    },
    "free_forge": {  # 免费锻造
        "rate": 0.03,  # 3%
        "vip_rate": 0.05,  # VIP 5%
        "name": "⚒️ 免费锻造券",
        "amount_range": (1, 2),
    },
}


def check_random_drop(is_vip: bool = False) -> dict:
    """
    检查随机掉落

    Args:
        is_vip: 是否VIP用户

    Returns:
        字典，包含掉落信息
        {
            "dropped": bool,       # 是否掉落
            "name": str,           # 物品名称
            "amount": int,         # 数量
            "type": str            # 物品类型
        }
    """
    for drop_type, drop_info in DROP_TABLE.items():
        rate = drop_info["vip_rate"] if is_vip else drop_info["rate"]

        if random.random() < rate:
            amount = random.randint(*drop_info["amount_range"])
            logger.info(f"随机掉落触发: {drop_info['name']} x{amount}")
            return {
                "dropped": True,
                "name": drop_info["name"],
                "amount": amount,
                "type": drop_type
            }

    return {
        "dropped": False,
        "name": "",
        "amount": 0,
        "type": "none"
    }


# ==========================================
# 🔥 连胜加成系统
# ==========================================

def get_streak_bonus(streak: int) -> dict:
    """
    计算连胜加成概率

    Args:
        streak: 连胜场数

    Returns:
        加成概率字典
    """
    # 连胜越高，暴击概率越高
    bonus_double = min(0.05, streak * 0.005)  # 最高额外5%
    bonus_triple = min(0.02, streak * 0.002)  # 最高额外2%

    return {
        "double_bonus": bonus_double,
        "triple_bonus": bonus_triple,
    }


def check_lucky_with_streak(streak: int, is_vip: bool = False) -> dict:
    """
    带连胜加成的幸运检测

    Args:
        streak: 连胜场数
        is_vip: 是否VIP用户

    Returns:
        幸运结果字典
    """
    base_rates = {
        "double": LUCKY_RATES["double"],
        "triple": LUCKY_RATES["triple"],
        "quintuple": LUCKY_RATES["quintuple"],
    }

    # VIP加成
    if is_vip:
        base_rates["double"] += VIP_LUCKY_BONUS["double"]
        base_rates["triple"] += VIP_LUCKY_BONUS["triple"]
        base_rates["quintuple"] += VIP_LUCKY_BONUS["quintuple"]

    # 连胜加成
    streak_bonus = get_streak_bonus(streak)
    base_rates["double"] += streak_bonus["double_bonus"]
    base_rates["triple"] += streak_bonus["triple_bonus"]

    # 检查五倍暴击
    if random.random() < base_rates["quintuple"]:
        from .feedback_utils import get_crit_effect
        return {
            "triggered": True,
            "multiplier": 5,
            "effect": get_crit_effect(5),
            "tier": "quintuple",
            "streak_bonus": streak_bonus
        }

    # 检查三倍暴击
    if random.random() < base_rates["triple"]:
        from .feedback_utils import get_crit_effect
        return {
            "triggered": True,
            "multiplier": 3,
            "effect": get_crit_effect(3),
            "tier": "triple",
            "streak_bonus": streak_bonus
        }

    # 检查双倍暴击
    if random.random() < base_rates["double"]:
        from .feedback_utils import get_crit_effect
        return {
            "triggered": True,
            "multiplier": 2,
            "effect": get_crit_effect(2),
            "tier": "double",
            "streak_bonus": streak_bonus
        }

    return {
        "triggered": False,
        "multiplier": 1,
        "effect": "",
        "tier": "none",
        "streak_bonus": streak_bonus
    }


# ==========================================
# 📊 幸运统计
# ==========================================

# 全局幸运统计（可选，用于记录玩家幸运值）
LUCKY_STATS = {}  # {user_id: {"total": int, "crits": int, "best": int}}


def record_lucky_event(user_id: int, multiplier: int):
    """记录幸运事件"""
    if user_id not in LUCKY_STATS:
        LUCKY_STATS[user_id] = {"total": 0, "crits": 0, "best": 1}

    LUCKY_STATS[user_id]["total"] += 1
    if multiplier > 1:
        LUCKY_STATS[user_id]["crits"] += 1
        if multiplier > LUCKY_STATS[user_id]["best"]:
            LUCKY_STATS[user_id]["best"] = multiplier


def get_user_lucky_stats(user_id: int) -> dict:
    """获取用户幸运统计"""
    return LUCKY_STATS.get(user_id, {"total": 0, "crits": 0, "best": 1})


# ==========================================
# 🎊 特殊幸运事件
# ==========================================

SPECIAL_EVENTS = {
    "rainbow": {
        "name": "🌈 彩虹奇迹",
        "rate": 0.001,  # 0.1%
        "effect": "彩虹色光芒笼罩了整个魔法阵！",
    },
    "starfall": {
        "name": "⭐ 流星雨",
        "rate": 0.0005,  # 0.05%
        "effect": "天空中划过无数流星！",
    },
    "aurora": {
        "name": "🌌 极光降临",
        "rate": 0.0001,  # 0.01%
        "effect": "绚丽的极光点亮了整个夜空！",
    },
}


def check_special_event() -> dict:
    """
    检查特殊幸运事件

    Returns:
        特殊事件信息
    """
    for event_type, event_info in SPECIAL_EVENTS.items():
        if random.random() < event_info["rate"]:
            logger.info(f"特殊事件触发: {event_info['name']}")
            return {
                "triggered": True,
                "type": event_type,
                "name": event_info["name"],
                "effect": event_info["effect"],
            }

    return {
        "triggered": False,
        "type": "none",
        "name": "",
        "effect": "",
    }
