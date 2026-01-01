"""
悬赏公会系统 (Mission) - 增强版
多种悬赏任务 + 聊天挖矿玩法
"""

from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete
from datetime import datetime, timedelta
import random

# ==========================================
# 📜 悬赏令缓存 (内存)
# ==========================================
# 结构: {
#   chat_id: {
#     "type": "chat|duel|tarot|forge|box|gift|quiz",
#     "target": N,
#     "progress": {user_id: count},
#     "snapshot": {user_id: initial_val},
#     "reward": N,
#     "start_time": datetime
#   }
# }
CURRENT_BOUNTY = {}

# ==========================================
# 💰 聊天挖矿配置
# ==========================================
# 基础掉落率 (15%)
DROP_RATE = 15
# 连击加成: 每连续聊天+5%
COMBO_BONUS = 5
# 最大连击倍数
MAX_COMBO_MULTIPLIER = 3
# 连击判定时间(秒)
COMBO_TIMEOUT = 60
# 活跃时段加成 (20:00-23:59)
PRIME_TIME_BONUS = 0.5
# 稀有掉落率 (1%)
RARE_DROP_RATE = 1

# 时段配置
PRIME_TIME_START = 20
PRIME_TIME_END = 23

# 关键词彩蛋
KEYWORD_EGGS = {
    "云海": {"emoji": "☁️", "bonus": 5, "msg": "云海深处，魔力涌动！"},
    "看板娘": {"emoji": "🎀", "bonus": 8, "msg": "哼哼，叫人家干嘛~"},
    "老婆": {"emoji": "💕", "bonus": 3, "msg": "你、你才不是我老婆！"},
    "早": {"emoji": "🌅", "bonus": 2, "msg": "早安，新的冒险开始了！"},
    "晚安": {"emoji": "🌙", "bonus": 2, "msg": "晚安，做个好梦~"},
    "加油": {"emoji": "💪", "bonus": 2, "msg": "一起加油！"},
    "谢谢": {"emoji": "🙏", "bonus": 2, "msg": "不客气哒~"},
    "哈哈哈哈": {"emoji": "😂", "bonus": 3, "msg": "笑什么呢~"},
    "喵": {"emoji": "🐱", "bonus": 2, "msg": "喵呜~"},
    "汪": {"emoji": "🐕", "bonus": 2, "msg": "汪汪！"},
    "草": {"emoji": "🌿", "bonus": 1, "msg": "大自然的力量..."},
    "牛逼": {"emoji": "🐮", "bonus": 3, "msg": "厉害厉害！"},
    "666": {"emoji": "✨", "bonus": 3, "msg": "操作666！"},
    "泪目": {"emoji": "😭", "bonus": 2, "msg": "呜呜呜..."},
}

# 悬赏任务配置
BOUNTY_TYPES = {
    "chat": {
        "name": "话痨挑战",
        "emoji": "🗣️",
        "title": "嘴遁王者",
        "desc_template": "谁先在这个群发送 <b>{target}</b> 条消息？",
        "target_range": (15, 40),
        "reward_range": (40, 100),
    },
    "duel": {
        "name": "决斗挑战",
        "emoji": "⚔️",
        "title": "决斗之王",
        "desc_template": "谁能先赢下 <b>{target}</b> 场魔法决斗？",
        "target_range": (1, 2),
        "reward_range": (80, 150),
    },
    "tarot": {
        "name": "占卜挑战",
        "emoji": "🔮",
        "title": "命运先知",
        "desc_template": "进行 <b>{target}</b> 次塔罗占卜，窥探命运！",
        "target_range": (3, 8),
        "reward_range": (50, 120),
    },
    "forge": {
        "name": "锻造挑战",
        "emoji": "⚒️",
        "title": "炼金大师",
        "desc_template": "在铁匠铺锻造 <b>{target}</b> 把武器！",
        "target_range": (2, 5),
        "reward_range": (60, 140),
    },
    "box": {
        "name": "盲盒挑战",
        "emoji": "🎰",
        "title": "欧皇附体",
        "desc_template": "抽取 <b>{target}</b> 个命运盲盒！",
        "target_range": (3, 10),
        "reward_range": (40, 100),
    },
    "gift": {
        "name": "传递爱心",
        "emoji": "💝",
        "title": "慈善家",
        "desc_template": "向 <b>{target}</b> 位不同的人转赠魔力！",
        "target_range": (2, 4),
        "reward_range": (60, 130),
    },
    "quiz": {
        "name": "智慧试炼",
        "emoji": "🧠",
        "title": "智慧贤者",
        "desc_template": "解开数学谜题！直接发送答案！",
        "target_range": (1, 1),
        "reward_range": (30, 80),
    },
}


# ==========================================
# 💰 模块一：聊天挖矿系统 (增强版)
# ==========================================
async def passive_chat_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """被动聊天奖励 - 增强版"""
    user = update.effective_user
    if user.is_bot:
        return

    chat = update.effective_chat
    if chat.type == "private":
        return  # 私聊不触发

    text = update.message.text.lower() if update.message.text else ""

    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()

    if not u:
        session.close()
        return

    # === 1. 连击系统 ===
    now = datetime.now()
    combo_multiplier = 1.0

    if u.last_chat_time:
        time_diff = (now - u.last_chat_time).total_seconds()
        if time_diff <= COMBO_TIMEOUT:
            # 在连击时间内，连击+1
            u.chat_combo = (u.chat_combo or 0) + 1
            # 计算连击加成
            combo_add = min(u.chat_combo * COMBO_BONUS / 100, MAX_COMBO_MULTIPLIER - 1)
            combo_multiplier = 1 + combo_add
        else:
            # 超时，重置连击
            u.chat_combo = 1
    else:
        u.chat_combo = 1

    u.last_chat_time = now

    # === 2. 时段加成 ===
    hour = now.hour
    is_prime_time = PRIME_TIME_START <= hour <= PRIME_TIME_END
    time_multiplier = 1 + PRIME_TIME_BONUS if is_prime_time else 1

    # === 3. 基础掉落判定 ===
    drop_roll = random.randint(1, 100)
    did_drop = drop_roll <= DROP_RATE

    # === 4. 关键词彩蛋 (必定触发) ===
    keyword_bonus = 0
    keyword_msg = None
    for keyword, egg in KEYWORD_EGGS.items():
        if keyword in text:
            keyword_bonus = egg["bonus"]
            keyword_msg = f"{egg['emoji']} {egg['msg']}"
            break

    # === 5. 稀有掉落 ===
    is_rare = random.randint(1, 100) <= RARE_DROP_RATE

    # === 计算奖励 ===
    base_reward = 0
    reward_breakdown = []

    if did_drop or is_rare or keyword_bonus > 0:
        # 基础奖励
        base = random.randint(3, 8) if u.is_vip else random.randint(1, 3)

        # 连击加成
        if u.chat_combo >= 5:
            combo_extra = int(base * (combo_multiplier - 1))
            if combo_extra > 0:
                reward_breakdown.append(f"连击x{u.chat_combo}+{combo_extra}")

        # 时段加成
        if is_prime_time:
            time_extra = int(base * PRIME_TIME_BONUS)
            reward_breakdown.append(f"深夜+{time_extra}")

        # 稀有暴击
        if is_rare:
            rare_bonus = random.randint(20, 50)
            base += rare_bonus
            reward_breakdown.append(f"稀有暴击+{rare_bonus}")

        # 关键词加成
        if keyword_bonus > 0:
            base += keyword_bonus
            reward_breakdown.append(f"关键词+{keyword_bonus}")

        # 应用倍率
        final_reward = int(base * combo_multiplier * time_multiplier)
        u.points += final_reward
        u.daily_chat_count = (u.daily_chat_count or 0) + 1

        session.commit()

        # === 消息通知 (只在小概率时显示，防止刷屏) ===
        should_notify = (
            is_rare or
            keyword_msg or
            (did_drop and random.randint(1, 8) == 1)  # 1/8的普通掉落会说话
        )

        if should_notify:
            title = "✨ <b>[VIP 暴击]</b>" if u.is_vip else "💰 <b>[拾取]</b>"
            if is_rare:
                title = "🌟 <b>[稀有掉落]</b>"

            breakdown_str = " + ".join(reward_breakdown) if reward_breakdown else ""

            msg = f"{title} 获得了 <code>{final_reward} MP</code>"
            if breakdown_str:
                msg += f"\n<i>({breakdown_str})</i>"
            if keyword_msg:
                msg += f"\n{keyword_msg}"
            if u.chat_combo >= 5:
                msg += f"\n🔥 <b>连击 x{u.chat_combo}!</b>"

            await reply_with_auto_delete(
                update.message,
                msg,
                disable_notification=True
            )

    session.close()

    # === 6. 检查数学题答案 ===
    await check_quiz_answer(update, context)

    # === 7. 检查悬赏进度 ===
    await check_bounty_progress(update, context, "chat")


# ==========================================
# 📜 模块二：发布悬赏任务
# ==========================================
async def post_mission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发布新的悬赏任务"""
    chat_id = update.effective_chat.id

    # 防止刷屏：如果当前有未完成任务，不允许发新的
    if chat_id in CURRENT_BOUNTY:
        bounty = CURRENT_BOUNTY[chat_id]
        bounty_type = bounty["type"]
        bounty_info = BOUNTY_TYPES[bounty_type]

        await reply_with_auto_delete(
            update.message,
            f"⚠️ <b>悬赏令已存在！</b>\n"
            f"当前任务：{bounty_info['emoji']} <b>{bounty_info['name']}</b>\n"
            f"请先完成它！"
        )
        return

    # 随机选择任务类型
    task_type = random.choice(list(BOUNTY_TYPES.keys()))
    task_info = BOUNTY_TYPES[task_type]

    # 随机目标值和奖励
    target = random.randint(*task_info["target_range"])
    reward = random.randint(*task_info["reward_range"])

    # 生成任务描述
    if task_type == "quiz":
        # 数学题特殊处理
        a, b = random.randint(10, 99), random.randint(10, 99)
        op = random.choice(["+", "-", "*"])
        if op == "*":
            a, b = random.randint(2, 12), random.randint(2, 12)

        answer = str(eval(f"{a}{op}{b}"))
        desc = f"🧠 <b>魔法谜题：</b> <code>{a} {op} {b} = ?</code>"

        CURRENT_BOUNTY[chat_id] = {
            "type": "quiz",
            "answer": answer,
            "target": 1,
            "reward": reward,
            "start_time": datetime.now(),
        }
    else:
        desc = task_info["desc_template"].format(target=target)

        CURRENT_BOUNTY[chat_id] = {
            "type": task_type,
            "target": target,
            "progress": {},
            "snapshot": {},
            "reward": reward,
            "start_time": datetime.now(),
        }

    # 发送悬赏令
    txt = (
        f"📜 <b>【 公 会 · 紧 急 悬 赏 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{task_info['emoji']} <b>{task_info['name']}</b>\n"
        f"{desc}\n\n"
        f"💰 <b>悬赏金额：</b> <b>{reward} MP</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>“猎人们，行动起来！”</i>"
    )

    msg = await update.message.reply_html(txt)

    # 保存消息对象用于后续删除
    CURRENT_BOUNTY[chat_id]["msg"] = msg


# ==========================================
# 🕵️ 模块三：进度监控
# ==========================================
async def check_bounty_progress(update: Update, context: ContextTypes.DEFAULT_TYPE, trigger_type: str):
    """检查悬赏任务进度"""
    chat_id = update.effective_chat.id
    mission = CURRENT_BOUNTY.get(chat_id)

    if not mission:
        return

    user = update.effective_user
    uid = user.id
    task_type = mission["type"]

    # 只有触发类型匹配才检查
    if task_type != trigger_type:
        return

    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=uid).first()

    if not u:
        session.close()
        return

    completed = False
    title = ""

    # === 各类任务进度检查 ===
    if task_type == "chat":
        current = mission["progress"].get(uid, 0) + 1
        mission["progress"][uid] = current
        if current >= mission["target"]:
            completed = True
            title = BOUNTY_TYPES["chat"]["title"]

    elif task_type == "duel":
        current_wins = u.win or 0
        if uid not in mission["snapshot"]:
            mission["snapshot"][uid] = current_wins
        else:
            delta = current_wins - mission["snapshot"][uid]
            mission["progress"][uid] = delta
            if delta >= mission["target"]:
                completed = True
                title = BOUNTY_TYPES["duel"]["title"]

    elif task_type == "tarot":
        current_count = u.daily_tarot_count or 0
        if uid not in mission["snapshot"]:
            mission["snapshot"][uid] = current_count
        else:
            delta = current_count - mission["snapshot"][uid]
            mission["progress"][uid] = delta
            if delta >= mission["target"]:
                completed = True
                title = BOUNTY_TYPES["tarot"]["title"]

    elif task_type == "forge":
        current_count = u.daily_forge_count or 0
        if uid not in mission["snapshot"]:
            mission["snapshot"][uid] = current_count
        else:
            delta = current_count - mission["snapshot"][uid]
            mission["progress"][uid] = delta
            if delta >= mission["target"]:
                completed = True
                title = BOUNTY_TYPES["forge"]["title"]

    elif task_type == "box":
        current_count = u.daily_box_count or 0
        if uid not in mission["snapshot"]:
            mission["snapshot"][uid] = current_count
        else:
            delta = current_count - mission["snapshot"][uid]
            mission["progress"][uid] = delta
            if delta >= mission["target"]:
                completed = True
                title = BOUNTY_TYPES["box"]["title"]

    elif task_type == "gift":
        current_count = u.daily_gift_count or 0
        if uid not in mission["snapshot"]:
            mission["snapshot"][uid] = current_count
        else:
            delta = current_count - mission["snapshot"][uid]
            mission["progress"][uid] = delta
            if delta >= mission["target"]:
                completed = True
                title = BOUNTY_TYPES["gift"]["title"]

    session.close()

    # === 任务完成结算 ===
    if completed:
        await settle_bounty(update, context, uid, title)


async def check_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """检查数学题答案"""
    chat_id = update.effective_chat.id

    if chat_id not in CURRENT_BOUNTY:
        return

    mission = CURRENT_BOUNTY[chat_id]
    if mission["type"] != "quiz":
        return

    user_text = update.message.text.strip()

    if user_text == mission["answer"]:
        await settle_bounty(update, context, update.effective_user.id, BOUNTY_TYPES["quiz"]["title"])


# ==========================================
# 🎁 模块四：结算发奖
# ==========================================
async def settle_bounty(update: Update, context: ContextTypes.DEFAULT_TYPE, winner_id: int, title: str):
    """结算悬赏任务"""
    chat_id = update.effective_chat.id
    mission = CURRENT_BOUNTY.get(chat_id)

    if not mission:
        return

    reward = mission["reward"]

    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=winner_id).first()

    bonus_msg = ""
    winner_name = update.effective_user.first_name

    if u:
        # VIP 加成
        if u.is_vip:
            bonus = int(reward * 0.2)
            reward += bonus
            bonus_msg = f" (👑 VIP加成 +{bonus})"

        u.points += reward
        winner_name = u.emby_account or winner_name
        session.commit()

    session.close()

    # 发送完成消息
    task_type = mission["type"]
    task_emoji = BOUNTY_TYPES[task_type]["emoji"]

    await reply_with_auto_delete(
        update.message,
        f"🎉 <b>【 悬 赏 · 完 美 达 成 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{task_emoji} <b>头衔：</b> {title}\n"
        f"🏆 <b>猎人：</b> {winner_name}\n"
        f"💰 <b>赏金：</b> <b>+{reward} MP</b>{bonus_msg}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>“真是令人惊叹的行动力！”</i>"
    )

    # 尝试删除原悬赏令
    try:
        if "msg" in mission:
            await mission["msg"].delete()
    except Exception:
        pass

    # 清除任务
    del CURRENT_BOUNTY[chat_id]


# ==========================================
# 🔧 辅助函数：供其他插件调用
# ==========================================
async def track_activity(user_id: int, activity_type: str):
    """
    追踪用户活动（供其他插件调用）
    activity_type: "tarot", "forge", "box", "gift"
    """
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user_id).first()

    if u:
        if activity_type == "tarot":
            u.daily_tarot_count = (u.daily_tarot_count or 0) + 1
        elif activity_type == "forge":
            u.daily_forge_count = (u.daily_forge_count or 0) + 1
        elif activity_type == "box":
            u.daily_box_count = (u.daily_box_count or 0) + 1
        elif activity_type == "gift":
            u.daily_gift_count = (u.daily_gift_count or 0) + 1

        session.commit()

    session.close()


# ==========================================
# 📋 注册处理器
# ==========================================
def register(app):
    """注册插件处理器"""
    app.add_handler(CommandHandler("mission", post_mission))
    app.add_handler(CommandHandler("task", post_mission))

    # 监听所有文本消息：挖矿 + 检查进度 + 数学题
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, passive_chat_reward))
