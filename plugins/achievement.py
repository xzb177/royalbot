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
    # === 签到成就 ===
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
}


# ==========================================
# 🎖️ 成就检查与颁发（供其他插件调用）
# ==========================================
def check_and_award_achievement(user: UserBinding, achievement_id: str, session=None) -> dict:
    """
    检查并颁发成就
    返回: {"new": bool, "reward": int, "name": str, "title": str, "emoji": str}
    """
    if achievement_id not in ACHIEVEMENTS:
        return {"new": False, "reward": 0, "name": "", "title": "", "emoji": ""}

    # 检查是否已完成
    completed = set(user.achievements.split(",")) if user.achievements else set()
    if achievement_id in completed:
        return {"new": False, "reward": 0, "name": "", "title": "", "emoji": ""}

    # 检查条件（如果定义了check函数）
    achievement = ACHIEVEMENTS[achievement_id]
    if "check" in achievement and not achievement["check"](user):
        return {"new": False, "reward": 0, "name": "", "title": "", "emoji": ""}

    # 颁发成就
    completed.add(achievement_id)
    user.achievements = ",".join(filter(None, completed))

    # 发放奖励
    reward = achievement["reward"]
    if achievement["reward_type"] == "points":
        user.points += reward

    return {
        "new": True,
        "reward": reward,
        "name": achievement["name"],
        "title": achievement.get("title", ""),
        "emoji": achievement["emoji"]
    }


def check_all_achievements(user: UserBinding, session=None) -> list:
    """
    检查所有可完成的成就
    返回: 新完成的成就列表
    """
    new_achievements = []
    completed = set(user.achievements.split(",")) if user.achievements else set()

    for ach_id, achievement in ACHIEVEMENTS.items():
        if ach_id in completed:
            continue
        if "check" in achievement and achievement["check"](user):
            result = check_and_award_achievement(user, ach_id, session)
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


# ==========================================
# 📜 成就展示命令
# ==========================================
async def achievement_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示成就列表"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user or not user.emby_account:
            await reply_with_auto_delete(msg, "💔 <b>请先绑定账号喵！</b>\n使用 <code>/bind 账号</code> 绑定后再来~")
            return

        # 自动检查新成就
        new_achievements = check_all_achievements(user, session)
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
