"""
成就系统 - 魔法少女版
- 追踪玩家里程碑
- 完成成就获得奖励
- 专属称号展示
- 自动检查并颁发成就
"""
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding
from utils import reply_with_auto_delete
from datetime import datetime

# ==========================================
# 🏆 成就配置
# ==========================================
ACHIEVEMENTS = {
    # === 新手友好成就 (新增) ===
    "first_checkin": {
        "name": "🌱 初次相遇",
        "desc": "完成第一次签到",
        "reward": 10,
        "reward_type": "points",
        "emoji": "🌱",
        "category": "新手",
        "check": lambda u: (u.total_checkin_days or 0) >= 1
    },
    "bound": {
        "name": "📜 魔法契约",
        "desc": "缔结魔法契约",
        "reward": 20,
        "reward_type": "points",
        "emoji": "📜",
        "category": "新手",
        "check": lambda u: u.emby_account is not None and u.emby_account != ""
    },
    "first_forge": {
        "name": "⚒️ 铁匠学徒",
        "desc": "完成第一次锻造",
        "reward": 30,
        "reward_type": "points",
        "emoji": "⚒️",
        "category": "新手",
        "check": lambda u: u.weapon is not None and u.weapon != ""
    },

    # === 签到成就 ===
    "checkin_1": {
        "name": "🍬 甜蜜开始",
        "desc": "连续签到1天",
        "reward": 5,
        "reward_type": "points",
        "emoji": "🍬",
        "category": "签到",
        "check": lambda u: (u.consecutive_checkin or 0) >= 1
    },
    "checkin_3": {
        "name": "🌸 三日坚持",
        "desc": "连续签到3天",
        "reward": 15,
        "reward_type": "points",
        "emoji": "🌸",
        "category": "签到",
        "check": lambda u: (u.consecutive_checkin or 0) >= 3
    },
    "checkin_7": {
        "name": "📅 坚持签到",
        "desc": "连续签到7天",
        "reward": 50,
        "reward_type": "points",
        "emoji": "📅",
        "category": "签到",
        "check": lambda u: u.consecutive_checkin >= 7 if u.consecutive_checkin else False
    },
    "checkin_30": {
        "name": "📆 签到达人",
        "desc": "连续签到30天",
        "reward": 300,
        "reward_type": "points",
        "emoji": "📆",
        "category": "签到",
        "title": "勤勉的魔法少女",
        "check": lambda u: u.consecutive_checkin >= 30 if u.consecutive_checkin else False
    },
    "checkin_100": {
        "name": "🏅 签到大师",
        "desc": "累计签到100天",
        "reward": 1000,
        "reward_type": "points",
        "emoji": "🏅",
        "category": "签到",
        "title": "时间领主",
        "check": lambda u: u.total_checkin_days >= 100 if u.total_checkin_days else False
    },

    # === 决斗成就 ===
    "duel_1": {
        "name": "⚔️ 初露锋芒",
        "desc": "赢得首场决斗",
        "reward": 20,
        "reward_type": "points",
        "emoji": "⚔️",
        "category": "决斗",
        "check": lambda u: u.win >= 1 if u.win else False
    },
    "duel_10": {
        "name": "🗡️ 决斗新手",
        "desc": "赢得10场决斗",
        "reward": 100,
        "reward_type": "points",
        "emoji": "🗡️",
        "category": "决斗",
        "check": lambda u: u.win >= 10 if u.win else False
    },
    "duel_50": {
        "name": "⚔️ 决斗老手",
        "desc": "赢得50场决斗",
        "reward": 500,
        "reward_type": "points",
        "emoji": "⚔️",
        "category": "决斗",
        "title": "格斗家",
        "check": lambda u: u.win >= 50 if u.win else False
    },
    "duel_100": {
        "name": "🏆 决斗王者",
        "desc": "赢得100场决斗",
        "reward": 1000,
        "reward_type": "points",
        "emoji": "🏆",
        "category": "决斗",
        "title": "决斗冠军",
        "check": lambda u: u.win >= 100 if u.win else False
    },
    "win_streak_5": {
        "name": "🔥 连胜新星",
        "desc": "决斗连胜5场",
        "reward": 100,
        "reward_type": "points",
        "emoji": "🔥",
        "category": "决斗",
        "title": "热血战士",
        "check": lambda u: u.win_streak >= 5 if u.win_streak else False
    },
    "win_streak_10": {
        "name": "🌟 连胜大师",
        "desc": "决斗连胜10场",
        "reward": 300,
        "reward_type": "points",
        "emoji": "🌟",
        "category": "决斗",
        "title": "不败传说",
        "check": lambda u: u.win_streak >= 10 if u.win_streak else False
    },

    # === 收藏成就 ===
    "collect_10": {
        "name": "🎒 收藏家",
        "desc": "获得10件不同物品",
        "reward": 100,
        "reward_type": "points",
        "emoji": "🎒",
        "category": "收藏",
        "check": lambda u: len(set(u.items.split(","))) >= 10 if u.items else False
    },
    "collect_50": {
        "name": "📦 藏品丰富",
        "desc": "获得50件不同物品",
        "reward": 500,
        "reward_type": "points",
        "emoji": "📦",
        "category": "收藏",
        "title": "收藏大师",
        "check": lambda u: len(set(u.items.split(","))) >= 50 if u.items else False
    },
    "collect_ur": {
        "name": "🌈 欧皇附体",
        "desc": "获得一件UR物品",
        "reward": 200,
        "reward_type": "points",
        "emoji": "🌈",
        "category": "收藏",
        "title": "命运眷顾者",
        "check": lambda u: any("UR" in i or "绝版" in i or "限定" in i for i in (u.items.split(",") if u.items else []))
    },

    # === 财富成就 ===
    "wealth_10000": {
        "name": "💰 小富翁",
        "desc": "累计获得10000 MP",
        "reward": 100,
        "reward_type": "points",
        "emoji": "💰",
        "category": "财富",
        "title": "魔力小富豪",
        "check": lambda u: u.total_earned >= 10000 if u.total_earned else False
    },
    "wealth_50000": {
        "name": "💎 大富豪",
        "desc": "累计获得50000 MP",
        "reward": 500,
        "reward_type": "points",
        "emoji": "💎",
        "category": "财富",
        "title": "魔力大亨",
        "check": lambda u: u.total_earned >= 50000 if u.total_earned else False
    },
    "wealth_100000": {
        "name": "👑 财神降临",
        "desc": "累计获得100000 MP",
        "reward": 2000,
        "reward_type": "points",
        "emoji": "👑",
        "category": "财富",
        "title": "星之财阀",
        "check": lambda u: u.total_earned >= 100000 if u.total_earned else False
    },
    "spend_5000": {
        "name": "🛒 购物狂",
        "desc": "累计消费5000 MP",
        "reward": 100,
        "reward_type": "points",
        "emoji": "🛒",
        "category": "财富",
        "title": "消费达人",
        "check": lambda u: u.total_spent >= 5000 if u.total_spent else False
    },
    "spend_50000": {
        "name": "💸 挥金如土",
        "desc": "累计消费50000 MP",
        "reward": 1000,
        "reward_type": "points",
        "emoji": "💸",
        "category": "财富",
        "title": "至尊VIP",
        "check": lambda u: u.total_spent >= 50000 if u.total_spent else False
    },

    # === 战力成就 ===
    "power_100": {
        "name": "🌱 初出茅庐",
        "desc": "战力达到100",
        "reward": 30,
        "reward_type": "points",
        "emoji": "🌱",
        "category": "战力",
        "check": lambda u: u.attack >= 100 if u.attack else False
    },
    "power_500": {
        "name": "💪 渐入佳境",
        "desc": "战力达到500",
        "reward": 100,
        "reward_type": "points",
        "emoji": "💪",
        "category": "战力",
        "check": lambda u: u.attack >= 500 if u.attack else False
    },
    "power_1000": {
        "name": "🔥 魔导士",
        "desc": "战力达到1000",
        "reward": 300,
        "reward_type": "points",
        "emoji": "🔥",
        "category": "战力",
        "title": "大魔导师",
        "check": lambda u: u.attack >= 1000 if u.attack else False
    },
    "power_5000": {
        "name": "⭐ 传奇",
        "desc": "战力达到5000",
        "reward": 1000,
        "reward_type": "points",
        "emoji": "⭐",
        "category": "战力",
        "title": "传说大魔导",
        "check": lambda u: u.attack >= 5000 if u.attack else False
    },
    "power_10000": {
        "name": "👑 星辰主宰",
        "desc": "战力达到10000",
        "reward": 3000,
        "reward_type": "points",
        "emoji": "👑",
        "category": "战力",
        "title": "星辰战神",
        "check": lambda u: u.attack >= 10000 if u.attack else False
    },

    # === 战力突破成就 ===
    "breakthrough_1": {
        "name": "🌱 突破初窥",
        "desc": "完成第1次战力突破",
        "reward": 50,
        "reward_type": "points",
        "emoji": "🌱",
        "category": "突破",
        "check": lambda u: u.breakthrough_level >= 1 if u.breakthrough_level else False
    },
    "breakthrough_2": {
        "name": "🌿 突破渐进",
        "desc": "完成第2次战力突破",
        "reward": 100,
        "reward_type": "points",
        "emoji": "🌿",
        "category": "突破",
        "check": lambda u: u.breakthrough_level >= 2 if u.breakthrough_level else False
    },
    "breakthrough_3": {
        "name": "🔥 突破纯青",
        "desc": "完成第3次战力突破",
        "reward": 200,
        "reward_type": "points",
        "emoji": "🔥",
        "category": "突破",
        "title": "突破达人",
        "check": lambda u: u.breakthrough_level >= 3 if u.breakthrough_level else False
    },
    "breakthrough_5": {
        "name": "💫 突破入神",
        "desc": "完成第5次战力突破",
        "reward": 500,
        "reward_type": "points",
        "emoji": "💫",
        "category": "突破",
        "title": "大突破者",
        "check": lambda u: u.breakthrough_level >= 5 if u.breakthrough_level else False
    },
    "breakthrough_7": {
        "name": "✨ 突破超凡",
        "desc": "完成第7次战力突破",
        "reward": 1000,
        "reward_type": "points",
        "emoji": "✨",
        "category": "突破",
        "title": "超凡入圣",
        "check": lambda u: u.breakthrough_level >= 7 if u.breakthrough_level else False
    },
    "breakthrough_10": {
        "name": "🌈 突破虚空",
        "desc": "完成第10次战力突破（满级）",
        "reward": 5000,
        "reward_type": "points",
        "emoji": "🌈",
        "category": "突破",
        "title": "虚空主宰",
        "check": lambda u: u.breakthrough_level >= 10 if u.breakthrough_level else False
    },
    "breakthrough_spent_10000": {
        "name": "💸 突破豪客",
        "desc": "突破累计消耗10000 MP",
        "reward": 200,
        "reward_type": "points",
        "emoji": "💸",
        "category": "突破",
        "check": lambda u: u.total_mp_spent_breakthrough >= 10000 if u.total_mp_spent_breakthrough else False
    },
    "breakthrough_spent_50000": {
        "name": "👑 突破至尊",
        "desc": "突破累计消耗50000 MP",
        "reward": 1000,
        "reward_type": "points",
        "emoji": "👑",
        "category": "突破",
        "title": "突破大亨",
        "check": lambda u: u.total_mp_spent_breakthrough >= 50000 if u.total_mp_spent_breakthrough else False
    },

    # === 铁匠成就 ===
    "forge_10": {
        "name": "⚒️ 打铁新手",
        "desc": "累计锻造10次",
        "reward": 50,
        "reward_type": "points",
        "emoji": "⚒️",
        "category": "锻造",
        "check": lambda u: False  # 需要在forge中追踪total_forges字段
    },
    "forge_100": {
        "name": "🔧 锻造大师",
        "desc": "累计锻造100次",
        "reward": 500,
        "reward_type": "points",
        "emoji": "🔧",
        "category": "锻造",
        "title": "炼金术士",
        "check": lambda u: False
    },

    # === 通天塔成就 ===
    "tower_10": {
        "name": "🗼 登塔者",
        "desc": "通天塔到达第10层",
        "reward": 50,
        "reward_type": "points",
        "emoji": "🗼",
        "category": "通天塔",
        "check": lambda u: (u.tower_max_floor or 0) >= 10
    },
    "tower_50": {
        "name": "🏯 高塔征服者",
        "desc": "通天塔到达第50层",
        "reward": 200,
        "reward_type": "points",
        "emoji": "🏯",
        "category": "通天塔",
        "title": "登塔达人",
        "check": lambda u: (u.tower_max_floor or 0) >= 50
    },
    "tower_100": {
        "name": "🏰 通天主宰",
        "desc": "通天塔到达第100层",
        "reward": 500,
        "reward_type": "points",
        "emoji": "🏰",
        "category": "通天塔",
        "title": "屠龙勇士",
        "check": lambda u: (u.tower_max_floor or 0) >= 100
    },
    "tower_kills_50": {
        "name": "⚔️ 怪物猎人",
        "desc": "通天塔击败50只怪物",
        "reward": 100,
        "reward_type": "points",
        "emoji": "⚔️",
        "category": "通天塔",
        "check": lambda u: (u.tower_total_wins or 0) >= 50
    },
    "tower_kills_200": {
        "name": "🗡️ 屠魔大师",
        "desc": "通天塔击败200只怪物",
        "reward": 300,
        "reward_type": "points",
        "emoji": "🗡️",
        "category": "通天塔",
        "title": "魔物终结者",
        "check": lambda u: (u.tower_total_wins or 0) >= 200
    },

    # === 灵魂共鸣成就 ===
    "resonance_10": {
        "name": "💫 初次共鸣",
        "desc": "进行10次灵魂共鸣",
        "reward": 50,
        "reward_type": "points",
        "emoji": "💫",
        "category": "共鸣",
        "check": lambda u: (u.resonance_count or 0) >= 10
    },
    "resonance_50": {
        "name": "💖 灵魂相连",
        "desc": "进行50次灵魂共鸣",
        "reward": 200,
        "reward_type": "points",
        "emoji": "💖",
        "category": "共鸣",
        "title": "羁绊使者",
        "check": lambda u: (u.resonance_count or 0) >= 50
    },
    "resonance_100": {
        "name": "💕 命运红绳",
        "desc": "进行100次灵魂共鸣",
        "reward": 500,
        "reward_type": "points",
        "emoji": "💕",
        "category": "共鸣",
        "title": "灵魂伴侣",
        "check": lambda u: (u.resonance_count or 0) >= 100
    },
    "intimacy_500": {
        "name": "💓 亲密好友",
        "desc": "好感度达到500",
        "reward": 100,
        "reward_type": "points",
        "emoji": "💓",
        "category": "共鸣",
        "check": lambda u: (u.intimacy or 0) >= 500
    },
    "intimacy_1000": {
        "name": "💗 深情知己",
        "desc": "好感度达到1000",
        "reward": 300,
        "reward_type": "points",
        "emoji": "💗",
        "category": "共鸣",
        "title": "命中注定",
        "check": lambda u: (u.intimacy or 0) >= 1000
    },

    # === 幸运转盘成就 ===
    "wheel_10": {
        "name": "🎡 幸运儿",
        "desc": "使用幸运转盘10次",
        "reward": 50,
        "reward_type": "points",
        "emoji": "🎡",
        "category": "转盘",
        "check": lambda u: False  # 需要追踪wheel_total字段
    },
    "wheel_50": {
        "name": "🍀 运气爆棚",
        "desc": "使用幸运转盘50次",
        "reward": 200,
        "reward_type": "points",
        "emoji": "🍀",
        "category": "转盘",
        "title": "天选之人",
        "check": lambda u: False
    },
}


# ==========================================
# 🎖️ 成就检查与颁发（供其他插件调用）
# ==========================================

async def broadcast_achievement_unlock(user: UserBinding, achievement: dict, context: ContextTypes.DEFAULT_TYPE = None):
    """
    将成就解锁消息广播到所有用户所在的群聊

    Args:
        user: 解锁成就的用户
        achievement: 成就信息字典
        context: Telegram context
    """
    if not context or not context.bot:
        return

    # 获取成就信息
    emoji = achievement.get("emoji", "🏆")
    name = achievement.get("name", "未知成就")
    reward = achievement.get("reward", 0)
    title = achievement.get("title", "")

    # 构建炫耀消息
    vip_badge = " 👑" if user.is_vip else ""
    txt = (
        f"🏆 <b>【 成 就 解 锁 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 恭喜 <b>{user.emby_account}</b>{vip_badge}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} <b>{name}</b>\n"
    )

    if title:
        txt += f"🏅 获得称号：<b>{title}</b>\n"

    if reward > 0:
        txt += f"💰 奖励：<b>+{reward} MP</b>\n"

    txt += (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"太厉害了！大家快来膜拜喵~\"</i>"
    )

    # 发送到所有有权限的群聊
    try:
        # 获取bot所在的所有群聊
        from telegram import Chat
        # 这里使用用户所在的群聊列表（如果有存储的话）
        # 或者发送到配置的公告群

        # 简化版：发送到默认公告群（如果配置了）
        # 这里可以通过环境变量或配置文件设置公告群ID

        # 获取用户当前所在的聊天（通过context传进来）
        # 如果achievement是在群里触发的，就发到那个群
        pass
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"广播成就失败: {e}")


def check_and_award_achievement(user: UserBinding, achievement_id: str, session=None, context=None, chat_id=None) -> dict:
    """
    检查并颁发成就
    返回: {"new": bool, "reward": int, "name": str, "title": str, "emoji": str, "broadcasted": bool}

    Args:
        user: 用户对象
        achievement_id: 成就ID
        session: 数据库session
        context: Telegram context (用于广播)
        chat_id: 触发成就的聊天ID (用于发送炫耀消息)
    """
    if achievement_id not in ACHIEVEMENTS:
        return {"new": False, "reward": 0, "name": "", "title": "", "emoji": "", "broadcasted": False}

    # 检查是否已完成
    completed = set(user.achievements.split(",")) if user.achievements else set()
    if achievement_id in completed:
        return {"new": False, "reward": 0, "name": "", "title": "", "emoji": "", "broadcasted": False}

    # 检查条件（如果定义了check函数）
    achievement = ACHIEVEMENTS[achievement_id]
    if "check" in achievement and not achievement["check"](user):
        return {"new": False, "reward": 0, "name": "", "title": "", "emoji": "", "broadcasted": False}

    # 颁发成就
    completed.add(achievement_id)
    user.achievements = ",".join(filter(None, completed))

    # 发放奖励
    reward = achievement["reward"]
    if achievement["reward_type"] == "points":
        user.points += reward

    result = {
        "new": True,
        "reward": reward,
        "name": achievement["name"],
        "title": achievement.get("title", ""),
        "emoji": achievement["emoji"],
        "broadcasted": False
    }

    # 如果是在群聊中触发且是重要成就，发送炫耀消息
    if context and chat_id:
        try:
            # 判断是否是重要成就（奖励>=100或有称号）
            is_important = reward >= 100 or achievement.get("title")

            if is_important:
                vip_badge = " 👑" if user.is_vip else ""
                emoji = achievement.get("emoji", "🏆")
                ach_name = achievement.get("name", "未知成就")

                # 统一的消息样式
                txt = (
                    f"🏆 <b>【 成 就 解 锁 】</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{emoji} <b>{ach_name}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"👤 恭喜 <b>{user.emby_account}</b>{vip_badge}\n"
                )

                if achievement.get("title"):
                    txt += f"🏅 获得称号：<b>{achievement['title']}</b>\n"

                if reward > 0:
                    txt += f"💰 奖励：<b>+{reward} MP</b>\n"

                txt += "━━━━━━━━━━━━━━━━━━\n"
                txt += "<i>\"太厉害了！大家快来膜拜喵~\"</i>"

                # 发送到群聊
                import asyncio
                asyncio.create_task(context.bot.send_message(chat_id=chat_id, text=txt, parse_mode='HTML'))
                result["broadcasted"] = True
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"发送成就炫耀消息失败: {e}")

    return result


def check_all_achievements(user: UserBinding, session=None, context=None, chat_id=None) -> list:
    """
    检查所有可完成的成就
    返回: 新完成的成就列表

    Args:
        user: 用户对象
        session: 数据库session
        context: Telegram context (用于广播重要成就)
        chat_id: 触发检查的聊天ID (用于发送炫耀消息)
    """
    new_achievements = []
    completed = set(user.achievements.split(",")) if user.achievements else set()

    for ach_id, achievement in ACHIEVEMENTS.items():
        if ach_id in completed:
            continue
        if "check" in achievement and achievement["check"](user):
            result = check_and_award_achievement(user, ach_id, session, context, chat_id)
            if result["new"]:
                new_achievements.append(result)

    return new_achievements


def get_achievement_progress(user: UserBinding) -> dict:
    """获取用户成就进度"""
    completed = set(user.achievements.split(",")) if user.achievements else set()

    # 统计
    by_category = {}
    total = len(ACHIEVEMENTS)
    done = len(completed)

    for ach_id, ach in ACHIEVEMENTS.items():
        cat = ach["category"]
        if cat not in by_category:
            by_category[cat] = {"total": 0, "done": 0}
        by_category[cat]["total"] += 1
        if ach_id in completed:
            by_category[cat]["done"] += 1

    return {
        "total": total,
        "done": done,
        "percentage": int(done / total * 100) if total > 0 else 0,
        "by_category": by_category
    }


def get_user_titles(user: UserBinding) -> list:
    """获取用户已解锁的称号列表"""
    completed = set(user.achievements.split(",")) if user.achievements else set()
    titles = []

    for ach_id in completed:
        if ach_id in ACHIEVEMENTS and "title" in ACHIEVEMENTS[ach_id]:
            titles.append(ACHIEVEMENTS[ach_id]["title"])

    return titles


def get_next_achievements(user: UserBinding, limit: int = 3) -> list:
    """
    获取用户即将解锁的成就（进度提示）

    Args:
        user: 用户对象
        limit: 返回数量限制

    Returns:
        即将解锁的成就列表，包含进度信息
    """
    completed = set(user.achievements.split(",")) if user.achievements else set()
    next_achievements = []

    # 计算每个未完成成就的进度
    for ach_id, achievement in ACHIEVEMENTS.items():
        if ach_id in completed:
            continue

        # 获取进度
        progress_info = get_achievement_single_progress(user, ach_id, achievement)
        if progress_info:
            progress_info["id"] = ach_id
            next_achievements.append(progress_info)

    # 按进度百分比排序，显示最接近完成的
    next_achievements.sort(key=lambda x: x["percentage"], reverse=True)
    return next_achievements[:limit]


def get_achievement_single_progress(user: UserBinding, ach_id: str, achievement: dict) -> dict:
    """
    获取单个成就的进度

    Returns:
        {
            "name": "成就名称",
            "emoji": "🏆",
            "desc": "成就描述",
            "current": 当前值,
            "target": 目标值,
            "percentage": 百分比,
            "remaining": 还差多少
        }
    """
    # 根据不同成就类型计算进度
    if ach_id == "first_checkin" or ach_id == "checkin_1":
        current = user.total_checkin_days or 0
        target = 1
    elif ach_id == "checkin_3":
        current = user.consecutive_checkin or 0
        target = 3
    elif ach_id.startswith("checkin_"):
        if "100" in ach_id:
            current = user.total_checkin_days or 0
            target = 100
        elif "30" in ach_id:
            current = user.consecutive_checkin or 0
            target = 30
        elif "7" in ach_id:
            current = user.consecutive_checkin or 0
            target = 7
        else:
            current = user.consecutive_checkin or 0
            target = 1

    elif ach_id == "bound":
        current = 1 if user.emby_account else 0
        target = 1
    elif ach_id == "first_forge":
        current = 1 if user.weapon and user.weapon != "" else 0
        target = 1

    elif ach_id.startswith("duel_"):
        if "100" in ach_id:
            current = user.win or 0
            target = 100
        elif "50" in ach_id:
            current = user.win or 0
            target = 50
        elif "10" in ach_id:
            current = user.win or 0
            target = 10
        else:  # 1
            current = user.win or 0
            target = 1

    elif ach_id.startswith("win_streak_"):
        current = user.win_streak or 0
        target = 10 if "10" in ach_id else 5

    elif ach_id.startswith("power_"):
        current = user.attack or 0
        if "10000" in ach_id:
            target = 10000
        elif "5000" in ach_id:
            target = 5000
        elif "1000" in ach_id:
            target = 1000
        elif "500" in ach_id:
            target = 500
        else:
            target = 100

    elif ach_id.startswith("tower_"):
        if "100" in ach_id:
            current = user.tower_max_floor or 0
            target = 100
        elif "50" in ach_id:
            current = user.tower_max_floor or 0
            target = 50
        else:  # 10
            current = user.tower_max_floor or 0
            target = 10

    elif ach_id.startswith("tower_kills_"):
        if "200" in ach_id:
            current = user.tower_total_wins or 0
            target = 200
        else:  # 50
            current = user.tower_total_wins or 0
            target = 50

    elif ach_id.startswith("resonance_"):
        current = user.resonance_count or 0
        if "100" in ach_id:
            target = 100
        elif "50" in ach_id:
            target = 50
        else:  # 10
            target = 10

    elif ach_id.startswith("intimacy_"):
        current = user.intimacy or 0
        target = 1000 if "1000" in ach_id else 500

    elif ach_id.startswith("wealth_"):
        current = user.total_earned or 0
        if "100000" in ach_id:
            target = 100000
        elif "50000" in ach_id:
            target = 50000
        else:  # 10000
            target = 10000

    elif ach_id.startswith("spend_"):
        current = user.total_spent or 0
        target = 50000 if "50000" in ach_id else 5000

    elif ach_id.startswith("collect_"):
        items = set(user.items.split(",")) if user.items else set()
        current = len(items)
        target = 50 if "50" in ach_id else 10

    else:
        # 无法计算进度的成就
        return None

    percentage = min(100, int(current / target * 100)) if target > 0 else 0

    return {
        "name": achievement["name"],
        "emoji": achievement["emoji"],
        "desc": achievement["desc"],
        "reward": achievement["reward"],
        "current": current,
        "target": target,
        "percentage": percentage,
        "remaining": max(0, target - current)
    }


# ==========================================
# 📜 成就展示命令
# ==========================================
async def achievement_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示成就列表"""
    query = getattr(update, "callback_query", None)
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user or not user.emby_account:
            await reply_with_auto_delete(msg, "💔 <b>请先绑定账号喵！</b>\n使用 <code>/bind 账号</code> 绑定后再来~")
            return

        # 获取聊天ID（如果在群聊中，用于广播成就）
        from telegram import Chat
        chat_id = msg.chat_id if msg.chat.type != Chat.PRIVATE else None

        # 自动检查新成就（传入context和chat_id用于广播）
        new_achievements = check_all_achievements(user, session, context, chat_id)
        if new_achievements:
            session.commit()

        completed = set(user.achievements.split(",")) if user.achievements else set()
        progress = get_achievement_progress(user)
        titles = get_user_titles(user)

        vip_badge = " 👑" if user.is_vip else ""

        # 按分类显示
        txt = (
            f"🏆 <b>【 成 就 殿 堂 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>冒险者：</b> {user.emby_account}{vip_badge}\n"
            f"📊 <b>完成度：</b> {progress['done']}/{progress['total']} ({progress['percentage']}%)\n"
        )

        # 显示已解锁称号
        if titles:
            txt += f"🏅 <b>已解锁称号：</b> {len(titles)} 个\n"

        txt += "━━━━━━━━━━━━━━━━━━\n"

        # 新成就提示
        if new_achievements:
            txt += f"\n🎉 <b>恭喜解锁新成就！</b>\n"
            for ach in new_achievements:
                txt += f"   {ach['emoji']} {ach['name']} (+{ach['reward']}MP)\n"
            txt += "━━━━━━━━━━━━━━━━━━\n"

        # [新增] 即将解锁的成就
        next_achievements = get_next_achievements(user, limit=3)
        if next_achievements:
            txt += f"\n🎯 <b>【 即 将 解 锁 】</b>\n"
            for ach in next_achievements:
                percentage = ach['percentage']
                bar_fill = "█" * (percentage // 10)
                bar_empty = "░" * (10 - percentage // 10)
                txt += f"\n{ach['emoji']} {ach['name']}\n"
                txt += f"   [{bar_fill}{bar_empty}] {percentage}% ({ach['current']}/{ach['target']})\n"
            txt += "━━━━━━━━━━━━━━━━━━\n"

        # 按分类展示成就
        categories = {}
        for ach_id, ach in ACHIEVEMENTS.items():
            cat = ach["category"]
            if cat not in categories:
                categories[cat] = []
            is_done = ach_id in completed
            status = "✅" if is_done else "⬜"
            reward_txt = f"+{ach['reward']}MP" if ach['reward'] > 0 else "🏅称号"
            title_txt = f" [{ach.get('title', '')}]" if ach.get('title') else ""
            categories[cat].append(f"{status} {ach['emoji']} {ach['name']}{title_txt} ({reward_txt})")

        for cat, items in categories.items():
            cat_progress = progress['by_category'].get(cat, {})
            cat_done = cat_progress.get('done', 0)
            cat_total = cat_progress.get('total', 0)
            txt += f"\n📌 <b>{cat}</b> ({cat_done}/{cat_total})\n"
            txt += "\n".join(items) + "\n"

        txt += "━━━━━━━━━━━━━━━━━━\n"
        txt += "<i>\"完成成就获得MP奖励和专属称号喵~(｡•̀ᴗ-)✧\"</i>"

        # 成就页面不使用自毁（保留查看）
        if query:
            await query.edit_message_text(txt, disable_web_page_preview=True, parse_mode='HTML')
        else:
            await msg.reply_html(txt, disable_web_page_preview=True)


async def achievement_titles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示已获得的称号"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user or not user.emby_account:
            await reply_with_auto_delete(msg, "💔 <b>请先绑定账号喵！</b>")
            return

        titles = get_user_titles(user)
        vip_badge = " 👑" if user.is_vip else ""

        txt = (
            f"🏅 <b>【 荣 耀 称 号 殿 堂 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>冒险者：</b> {user.emby_account}{vip_badge}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )

        if titles:
            for i, title in enumerate(titles, 1):
                txt += f"{i}. 🎖️ {title}\n"
            txt += f"\n🎊 <b>共 {len(titles)} 个称号</b>\n"
        else:
            txt += "💫 <i>还没有获得任何称号喵~\n去完成成就解锁吧！(｡•̀ᴗ-)✧</i>\n"

        txt += "━━━━━━━━━━━━━━━━━━\n"

        await reply_with_auto_delete(msg, txt)


# ==========================================
# 🔌 注册处理器
# ==========================================
def register(app):
    app.add_handler(CommandHandler("achievement", achievement_list))
    app.add_handler(CommandHandler("achievements", achievement_list))
    app.add_handler(CommandHandler("ach", achievement_list))
    app.add_handler(CommandHandler("titles", achievement_titles))
    app.add_handler(CommandHandler("mytitles", achievement_titles))
