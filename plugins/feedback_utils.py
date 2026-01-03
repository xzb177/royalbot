"""
通用反馈工具模块
提供进度条、动画特效、随机反馈等通用功能
风格：活泼热闹（花里胡哨）
"""

import random

# ==========================================
# 📊 进度条生成
# ==========================================

def progress_bar(current: int, total: int, length: int = 15) -> str:
    """
    生成进度条（花里胡哨风格）

    Args:
        current: 当前进度
        total: 总进度
        length: 进度条长度

    Returns:
        进度条字符串，如 "▓▓▓▓▓▓▓▓▓▓░░░░░ 🌟 67%"
    """
    if total <= 0:
        return "░" * length + " 0%"

    ratio = min(1.0, current / total)
    filled = int(ratio * length)
    percentage = int(ratio * 100)

    # 进度条字符
    bar = "▓" * filled + "░" * (length - filled)

    # 根据完成度选择emoji
    if percentage >= 100:
        emoji = "🎉"
    elif percentage >= 75:
        emoji = "🌟"
    elif percentage >= 50:
        emoji = "⭐"
    elif percentage >= 25:
        emoji = "💫"
    else:
        emoji = "🌱"

    return f"{bar} {emoji} {percentage}%"


def mini_progress(current: int, total: int) -> str:
    """迷你进度条，用于紧凑显示"""
    if total <= 0:
        return "[░░░░░░░░░░] 0%"
    ratio = min(1.0, current / total)
    filled = int(ratio * 10)
    return f"[{'█' * filled}{'░' * (10 - filled)}] {int(ratio * 100)}%"


# ==========================================
# ✨ 加载动画
# ==========================================

LOADING_ANIMATIONS = [
    "✨ 命运之轮转动中...",
    "🔮 魔法阵展开中...",
    "⭐ 星光汇聚中...",
    "🌈 彩虹桥搭建中...",
    "💫 传送魔法准备...",
    "🎁 礼物打包中...",
    "🌸 魔力注入中...",
    "🎀 悄悄准备中...",
]

def random_loading() -> str:
    """获取随机加载动画"""
    return random.choice(LOADING_ANIMATIONS)


# ==========================================
# 💥 暴击特效
# ==========================================

# 暴击特效文字（花里胡哨）
CRIT_EFFECTS = {
    2: [
        "💫 双倍星光！",
        "✨✨ 闪耀暴击 ✨✨",
        "🌟 星光爆发 x2！",
        "💎 双倍闪耀！",
        "⭐⭐ 双星连珠！"
    ],
    3: [
        "✨ 三重闪耀！",
        "💎 三倍奇迹！",
        "🌈 三彩光辉！",
        "🌟🌟🌟 三星连闪！",
        "💫💫💫 三重暴击！"
    ],
    5: [
        "🌠 传说奇迹！",
        "🏆 五倍传说！！",
        "👑 神话降临！！",
        "✨✨✨✨✨ 五星光耀！！",
        "💎💎💎💎💎 传说五倍！！"
    ]
}

def get_crit_effect(multiplier: int) -> str:
    """
    获取暴击特效文字

    Args:
        multiplier: 倍数 (2, 3, 5)

    Returns:
        随机特效文字
    """
    effects = CRIT_EFFECTS.get(multiplier, CRIT_EFFECTS[2])
    return random.choice(effects)


# ==========================================
# 🎉 成功动画
# ==========================================

SUCCESS_ANIMATIONS = [
    "🎉", "🎊", "✨", "💫", "⭐", "🌟", "💖", "🎀",
    "🌸", "🌺", "🎑", "🏆", "🥇", "👑", "💎", "🔮"
]

def random_success() -> str:
    """获取随机成功动画emoji"""
    return random.choice(SUCCESS_ANIMATIONS)


def success_burst(count: int = 3) -> str:
    """获取一串成功动画"""
    emojis = random.sample(SUCCESS_ANIMATIONS, min(count, len(SUCCESS_ANIMATIONS)))
    return " ".join(emojis)


# ==========================================
# 📈 升级/提升动画
# ==========================================

LEVEL_UP_ANIMATIONS = [
    "⬆️ LEVEL UP！",
    "📈 实力暴涨！",
    "🚀 突破界限！",
    "🌟 觉醒成功！",
    "💫 进化！",
    "✨ 蜕变完成！",
    "🎊 超越极限！",
]

def random_level_up() -> str:
    """获取随机升级动画"""
    return random.choice(LEVEL_UP_ANIMATIONS)


# ==========================================
# 🔥 战力变化显示
# ==========================================

def format_power_change(old_value: int, new_value: int) -> str:
    """
    格式化战力变化显示

    Args:
        old_value: 旧值
        new_value: 新值

    Returns:
        格式化的变化文本
    """
    diff = new_value - old_value

    if diff > 0:
        # 战力提升
        arrows = "⬆️" * min(3, 1 + diff // 100)
        return f"📈 {arrows} 战力提升：+{diff} ⚡"
    elif diff < 0:
        # 战力下降
        arrows = "⬇️" * min(3, 1 + abs(diff) // 100)
        return f"📉 {arrows} 战力变化：{diff}"
    else:
        return "➡️ 战力持平"


def detailed_power_change(old_value: int, new_value: int) -> str:
    """详细的战力变化显示（多行）"""
    diff = new_value - old_value

    lines = [
        "📊 战力变化：",
        f"   旧战力：{old_value} ⬇️" if diff >= 0 else f"   旧战力：{old_value} ⬆️",
        f"   新战力：{new_value} ⬆️" if diff >= 0 else f"   新战力：{new_value} ⬇️",
    ]

    if diff > 0:
        bolts = "⚡" * min(5, 1 + diff // 50)
        lines.append(f"   🚀 提升：+{diff} {bolts}")
    elif diff < 0:
        lines.append(f"   📉 变化：{diff}")

    return "\n".join(lines)


# ==========================================
# 🎁 稀有度特效
# ==========================================

RARITY_EFFECTS = {
    "N": ["✨", "💫"],
    "R": ["🔵", "💎"],
    "SR": ["🟣", "⭐", "✨"],
    "SSR": ["🟡", "🌟", "💫", "✨✨"],
    "UR": ["🌈", "🌠", "✨✨✨", "👑", "💎💎"],
}

def get_rarity_effect(rarity: str) -> str:
    """获取稀有度特效"""
    effects = RARITY_EFFECTS.get(rarity.upper(), RARITY_EFFECTS["N"])
    return " ".join(random.choice(effects) for _ in range(random.randint(2, 4)))


# ==========================================
# 🎊 综合反馈生成
# ==========================================

def generate_reward_feedback(
    base_reward: int,
    actual_reward: int,
    reward_name: str = "MP"
) -> str:
    """
    生成奖励反馈文字

    Args:
        base_reward: 基础奖励
        actual_reward: 实际奖励
        reward_name: 奖励名称

    Returns:
        格式化的奖励反馈
    """
    lines = []

    # 基础奖励
    lines.append(f"💰 基础奖励：+{base_reward} {reward_name}")

    # 计算倍数
    multiplier = actual_reward / base_reward if base_reward > 0 else 1

    if multiplier > 1.5:
        # 三倍或以上
        if multiplier >= 4.5:
            effect = get_crit_effect(5)
            lines.append(f"🌠✨ {effect} ✨🌠")
        elif multiplier >= 2.5:
            effect = get_crit_effect(3)
            lines.append(f"✨ {effect}")
        else:
            effect = get_crit_effect(2)
            lines.append(f"💫 {effect}")

        bonus = actual_reward - base_reward
        lines.append(f"💰💰💰 额外 +{bonus} {reward_name} 💰💰💰")
        lines.append(f"🎊🎊 总计：+{actual_reward} {reward_name}！🎊🎊")

    elif multiplier > 1:
        # 有加成但不到双倍
        bonus = actual_reward - base_reward
        lines.append(f"✨ 加成奖励：+{bonus} {reward_name}")

    return "\n".join(lines)


def generate_completion_feedback(
    task_name: str,
    progress: int,
    total: int,
    reward: int
) -> str:
    """
    生成任务完成反馈

    Args:
        task_name: 任务名称
        progress: 当前进度
        total: 总进度
        reward: 奖励

    Returns:
        格式化的完成反馈
    """
    lines = [
        f"🎉 {random_success()} 【 任 务 完 成 】 {random_success()}",
        "━━━━━━━━━━━━━━━━━━",
        f"✨ 完成任务：{task_name}",
        f"📊 完成进度：{progress}/{total}",
        f"💰 获得奖励：+{reward} MP",
        "━━━━━━━━━━━━━━━━━━",
    ]

    # 随机鼓励语
    encouragements = [
        "太棒了！继续加油喵~",
        "不愧是你！(｡•̀ᴗ-)✧",
        "魔法少女的实力又提升了喵！",
        "这节奏，是要成为传奇的节奏喵！",
        "看板娘为你骄傲喵~ (≧◡≦)",
    ]
    lines.append(f"💫 {random.choice(encouragements)}")

    return "\n".join(lines)
