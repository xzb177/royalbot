"""
成就系统 - 魔法少女版
- 追踪玩家里程碑
- 完成成就获得奖励
- 专属称号展示
"""
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete
from datetime import datetime, timedelta

# ==========================================
# 🏆 成就配置
# ==========================================

ACHIEVEMENTS = {
    # 签到成就
    "checkin_7": {
        "name": "📅 坚持签到",
        "desc": "连续签到7天",
        "reward": 50,
        "reward_type": "points",
        "emoji": "📅",
        "category": "签到"
    },
    "checkin_30": {
        "name": "📆 签到达人",
        "desc": "连续签到30天",
        "reward": 300,
        "reward_type": "points",
        "emoji": "📆",
        "category": "签到",
        "title": "勤勉的魔法少女"
    },
    "checkin_100": {
        "name": "🏅 签到大师",
        "desc": "累计签到100天",
        "reward": 1000,
        "reward_type": "points",
        "emoji": "🏅",
        "category": "签到",
        "title": "时间领主"
    },

    # 决斗成就
    "duel_1": {
        "name": "⚔️ 初露锋芒",
        "desc": "赢得首场决斗",
        "reward": 20,
        "reward_type": "points",
        "emoji": "⚔️",
        "category": "决斗"
    },
    "duel_10": {
        "name": "🗡️ 决斗新手",
        "desc": "赢得10场决斗",
        "reward": 100,
        "reward_type": "points",
        "emoji": "🗡️",
        "category": "决斗"
    },
    "duel_100": {
        "name": "🏆 决斗王者",
        "desc": "赢得100场决斗",
        "reward": 1000,
        "reward_type": "points",
        "emoji": "🏆",
        "category": "决斗",
        "title": "决斗冠军"
    },

    # 收藏成就
    "collect_10": {
        "name": "🎒 收藏家",
        "desc": "获得10件不同物品",
        "reward": 100,
        "reward_type": "points",
        "emoji": "🎒",
        "category": "收藏"
    },
    "collect_ur": {
        "name": "🌈 欧皇附体",
        "desc": "获得一件UR物品",
        "reward": 200,
        "reward_type": "points",
        "emoji": "🌈",
        "category": "收藏",
        "title": "命运眷顾者"
    },

    # 财富成就
    "wealth_10000": {
        "name": "💰 小富翁",
        "desc": "累计获得10000 MP",
        "reward": 0,
        "reward_type": "title_only",
        "emoji": "💰",
        "category": "财富",
        "title": "魔力小富豪"
    },
    "wealth_50000": {
        "name": "💎 大富豪",
        "desc": "累计获得50000 MP",
        "reward": 0,
        "reward_type": "title_only",
        "emoji": "💎",
        "category": "财富",
        "title": "魔力大亨"
    },
    "spend_5000": {
        "name": "🛒 购物狂",
        "desc": "累计消费5000 MP",
        "reward": 0,
        "reward_type": "title_only",
        "emoji": "🛒",
        "category": "财富",
        "title": "消费达人"
    },

    # 战力成就
    "power_500": {
        "name": "💪 渐入佳境",
        "desc": "战力达到500",
        "reward": 100,
        "reward_type": "points",
        "emoji": "💪",
        "category": "战力"
    },
    "power_1000": {
        "name": "🔥 魔导士",
        "desc": "战力达到1000",
        "reward": 300,
        "reward_type": "points",
        "emoji": "🔥",
        "category": "战力",
        "title": "大魔导师"
    },
    "power_5000": {
        "name": "⭐ 传奇",
        "desc": "战力达到5000",
        "reward": 1000,
        "reward_type": "points",
        "emoji": "⭐",
        "category": "战力",
        "title": "传说大魔导"
    },
}


# ==========================================
# 🎖️ 成就检查函数（供其他插件调用）
# ==========================================
def check_and_award_achievement(user: UserBinding, achievement_id: str) -> dict:
    """
    检查并颁发成就
    返回: {"new": bool, "reward": int, "name": str}
    """
    if achievement_id not in ACHIEVEMENTS:
        return {"new": False, "reward": 0, "name": ""}

    # 检查是否已完成
    completed = user.achievements.split(",") if user.achievements else []
    if achievement_id in completed:
        return {"new": False, "reward": 0, "name": ""}

    # 颁发成就
    achievement = ACHIEVEMENTS[achievement_id]
    completed.append(achievement_id)
    user.achievements = ",".join(completed)

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


# ==========================================
# 📜 成就展示命令
# ==========================================
async def achievement_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示成就列表"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    session = Session()
    user = session.query(UserBinding).filter_by(tg_id=user_id).first()

    if not user or not user.emby_account:
        session.close()
        await reply_with_auto_delete(msg, "💔 <b>请先绑定账号喵！</b>\n使用 <code>/bind 账号</code> 绑定后再来~")
        return

    completed = set(user.achievements.split(",")) if user.achievements else set()
    progress = get_achievement_progress(user)

    vip_badge = " 👑" if user.is_vip else ""

    # 按分类显示
    txt = (
        f"🏆 <b>【 成 就 殿 堂 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>冒险者：</b> {user.emby_account}{vip_badge}\n"
        f"📊 <b>完成度：</b> {progress['done']}/{progress['total']} ({progress['percentage']}%)\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )

    # 按分类展示
    categories = {}
    for ach_id, ach in ACHIEVEMENTS.items():
        cat = ach["category"]
        if cat not in categories:
            categories[cat] = []
        is_done = ach_id in completed
        status = "✅" if is_done else "⬜"
        reward_txt = f"+{ach['reward']}MP" if ach['reward'] > 0 else "🏅称号"
        categories[cat].append(f"{status} {ach['emoji']} {ach['name']} ({reward_txt})")

    for cat, items in categories.items():
        txt += f"\n📌 <b>{cat}</b>\n"
        txt += "\n".join(items) + "\n"

    txt += "━━━━━━━━━━━━━━━━━━\n"
    txt += "<i>\"完成成就获得MP奖励和专属称号喵~(｡•̀ᴗ-)✧\"</i>"

    await reply_with_auto_delete(msg, txt)
    session.close()


# ==========================================
# 🔌 注册处理器
# ==========================================
def register(app):
    app.add_handler(CommandHandler("achievement", achievement_list))
    app.add_handler(CommandHandler("achievements", achievement_list))
    app.add_handler(CommandHandler("ach", achievement_list))
