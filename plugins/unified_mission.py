"""
统一任务系统 - 融合每日任务 + 悬赏任务
- 每日任务：每天3个随机小任务，完成后自动发奖
- 悬赏任务：全群竞争，先完成者得大奖
- 标签页切换，界面统一
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import get_session, UserBinding
from utils import reply_with_auto_delete
from datetime import datetime, date, timedelta
import random

# ==========================================
# 📋 每日任务配置
# ==========================================
DAILY_TASKS = {
    "chat_10": {"name": "话痨少女", "desc": "在群聊发送10条消息", "reward": 30, "emoji": "💬", "target": 10},
    "chat_20": {"name": "社交达人", "desc": "在群聊发送20条消息", "reward": 50, "emoji": "🗣️", "target": 20},
    "checkin": {"name": "每日签到", "desc": "完成今日签到", "reward": 20, "emoji": "🍬", "target": 1},
    "lucky_used": {"name": "幸运尝试", "desc": "使用幸运草签到一次", "reward": 25, "emoji": "🍀", "target": 1},
    "tarot": {"name": "命运窥探", "desc": "进行一次塔罗占卜", "reward": 25, "emoji": "🔮", "target": 1},
    "forge": {"name": "铁匠学徒", "desc": "锻造一次武器", "reward": 25, "emoji": "⚒️", "target": 1},
    "poster": {"name": "盲盒玩家", "desc": "抽取一次命运盲盒", "reward": 25, "emoji": "🎰", "target": 1},
    "duel": {"name": "勇者试炼", "desc": "参与一次决斗", "reward": 30, "emoji": "⚔️", "target": 1},
    "gift": {"name": "传递爱心", "desc": "向他人转赠魔力", "reward": 30, "emoji": "💝", "target": 1},
    "shop_buy": {"name": "购物达人", "desc": "在商店购买任意商品", "reward": 25, "emoji": "🛒", "target": 1},
    "wheel": {"name": "幸运转盘", "desc": "使用一次幸运转盘", "reward": 20, "emoji": "🎡", "target": 1},
    "tower": {"name": "通天塔", "desc": "挑战一次通天塔", "reward": 30, "emoji": "🗼", "target": 1},
    "resonance": {"name": "灵魂共鸣", "desc": "进行一次灵魂共鸣", "reward": 25, "emoji": "💫", "target": 1},
    "bank": {"name": "银行存取", "desc": "使用银行存取款一次", "reward": 15, "emoji": "🏦", "target": 1},
}

# 任务池 - 每天从中随机选3个
# 按成本分层，确保每天都有免费任务可做
# 移除高消费任务（forge, shop_buy），让新手也能完成
TASK_POOL = [
    ["chat_10", "chat_20"],  # 聊天类 (必选一个) - 免费
    [
        # 免费任务
        "checkin",    # 签到 - 免费（还赚钱）
        "wheel",      # 转盘 - 免费
        "resonance",  # 共鸣 - 免费
        "bank",       # 银行 - 免费
        # 低消费任务 (<25 MP)
        "poster",     # 盲盒 - 20MP（新手有3张券）
        "tarot",      # 塔罗 - 15MP买券
        # 有风险但免费/低成本
        "duel",       # 决斗 - 有风险但免费参与
        "tower",      # 通天塔 - 免费挑战
        "gift",       # 转赠 - 低成本
    ],
]

# 分层任务配置（用于确保任务平衡）
TASK_TIERS = {
    "free": ["checkin", "wheel", "resonance", "bank", "duel", "tower"],  # 完全免费
    "low_cost": ["poster", "tarot", "gift"],  # <50 MP
    "high_cost": ["forge", "shop_buy"],  # 高消费任务 - 已从每日任务池移除
}

# ==========================================
# 📜 悬赏任务配置
# ==========================================
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
    "tower": {
        "name": "通天塔挑战",
        "emoji": "🗼",
        "title": "屠龙者",
        "desc_template": "在通天塔击败 <b>{target}</b> 只怪物！",
        "target_range": (3, 8),
        "reward_range": (60, 150),
    },
    "wheel": {
        "name": "转盘挑战",
        "emoji": "🎡",
        "title": "幸运之星",
        "desc_template": "使用幸运转盘 <b>{target}</b> 次！",
        "target_range": (3, 10),
        "reward_range": (40, 100),
    },
}

# 悬赏令缓存 {chat_id: {...}}
CURRENT_BOUNTY = {}


# ==========================================
# 辅助函数
# ==========================================
def get_today():
    return datetime.now().date()


def get_user_daily_tasks(user: UserBinding) -> dict:
    """获取用户今日任务，如果没有则生成"""
    today = get_today()

    # 先检查是否需要刷新（生成新任务）
    need_refresh = False
    if user.task_date:
        last_date = user.task_date.date() if isinstance(user.task_date, datetime) else user.task_date
        if last_date < today:
            need_refresh = True
    else:
        need_refresh = True

    if need_refresh:
        selected_tasks = []
        # 1. 聊天任务（必选）
        selected_tasks.append(random.choice(TASK_POOL[0]))

        # 2. 确保至少1个免费任务
        free_tasks = [t for t in TASK_POOL[1] if t in TASK_TIERS["free"]]
        selected_tasks.append(random.choice(free_tasks))

        # 3. 第三个任务随机（可以是任何任务）
        remaining = [t for t in TASK_POOL[1] if t not in selected_tasks]
        selected_tasks.append(random.choice(remaining))

        user.task_date = datetime.now()
        user.daily_tasks = ",".join(selected_tasks)
        user.task_progress = "0,0,0"

    # 确保读取最新的 task_progress
    task_ids = (user.daily_tasks or "").split(",")
    # 如果 user.task_progress 是空的，初始化为 "0,0,0"
    progress_str = user.task_progress or "0,0,0"
    progress_list = progress_str.split(",")

    tasks = {}
    for i, tid in enumerate(task_ids):
        if tid in DAILY_TASKS:
            target = DAILY_TASKS[tid]["target"]
            progress = int(progress_list[i]) if i < len(progress_list) else 0
            tasks[tid] = {
                **DAILY_TASKS[tid],
                "progress": progress,
                "done": progress >= target,
                "target": target
            }

    return tasks


def update_task_progress(user: UserBinding, task_type: str, delta: int = 1) -> tuple:
    """
    更新每日任务进度
    返回：(是否完成新任务，任务名称，奖励)
    """
    task_ids = (user.daily_tasks or "").split(",")
    if not task_ids or not user.task_date:
        return False, None, 0

    today = get_today()
    last_date = user.task_date.date() if isinstance(user.task_date, datetime) else user.task_date
    if last_date < today:
        return False, None, 0

    progress_list = ((user.task_progress or "0,0,0").split(","))
    new_completed = False
    task_name = None
    reward = 0

    for i, tid in enumerate(task_ids):
        if tid not in DAILY_TASKS:
            continue
        target = DAILY_TASKS[tid]["target"]
        current = int(progress_list[i]) if i < len(progress_list) else 0
        if current >= target:
            continue

        should_update = False
        if task_type == "chat" and tid in ["chat_10", "chat_20"]:
            should_update = True
        elif task_type == "checkin" and tid == "checkin":
            should_update = True
        elif task_type == "lucky" and tid == "lucky_used":
            should_update = True
        elif task_type == "tarot" and tid == "tarot":
            should_update = True
        elif task_type == "forge" and tid == "forge":
            should_update = True
        elif task_type == "poster" and tid == "poster":
            should_update = True
        elif task_type == "duel" and tid == "duel":
            should_update = True
        elif task_type == "gift" and tid == "gift":
            should_update = True
        elif task_type == "shop" and tid == "shop_buy":
            should_update = True

        if should_update:
            new_val = min(current + delta, target)
            progress_list[i] = str(new_val)

            if new_val >= target and current < target:
                new_completed = True
                task_name = DAILY_TASKS[tid]["name"]
                reward = DAILY_TASKS[tid]["reward"]

    user.task_progress = ",".join(progress_list)
    return new_completed, task_name, reward


# ==========================================
# 统一任务界面
# ==========================================
async def mission_main(update: Update, context: ContextTypes.DEFAULT_TYPE, tab: str = "daily"):
    """统一任务主界面"""
    msg = update.effective_message
    query = update.callback_query if hasattr(update, 'callback_query') and update.callback_query else None

    if not msg and not query:
        return

    user_id = update.effective_user.id

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not u or not u.emby_account:
            target = query.edit_message_text if query else msg.reply_html
            await target("💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        vip_badge = " 👑" if u.is_vip else ""

        # 构建界面
        if tab == "daily":
            tasks = get_user_daily_tasks(u)
            session.commit()

            completed = sum(1 for t in tasks.values() if t["done"])
            total = len(tasks)
            total_reward = sum(t["reward"] for t in tasks.values() if not t["done"])

            txt = (
                f"📋 <b>每 日 任 务</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>{u.emby_account}</b>{vip_badge}\n"
                f"📊 进度: <b>{completed}/{total}</b> | 💰 奖励: <b>{total_reward}</b> MP\n"
                f"━━━━━━━━━━━━━━━━━━\n"
            )

            for task in tasks.values():
                status = "✅" if task["done"] else "⬜"
                txt += (
                    f"{status} {task['emoji']} <b>{task['name']}</b> — "
                    f"{task['progress']}/{task['target']} ({task['reward']} MP)\n"
                )

            txt += (
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>💡 完成任务自动发奖 | 👑 VIP +50%</i>"
            )

            buttons = [
                [InlineKeyboardButton("🔄 刷新任务 (20MP)", callback_data="mission_refresh_daily")],
                [InlineKeyboardButton("📜 悬赏任务", callback_data="mission_tab_bounty")],
            ]

        elif tab == "bounty":
            chat_id = update.effective_chat.id if update.effective_chat else user_id
            bounty = CURRENT_BOUNTY.get(chat_id)

            if bounty:
                bounty_type = bounty["type"]
                bounty_info = BOUNTY_TYPES[bounty_type]

                if bounty_type == "quiz":
                    desc = f"🧠 <b>魔法谜题：</b> <code>{bounty.get('question', '?')}</code>"
                else:
                    target = bounty.get("target", 1)
                    desc = bounty_info["desc_template"].format(target=target)

                txt = (
                    f"📜 <b>悬 赏 任 务</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{bounty_info['emoji']} {desc}\n"
                    f"💰 奖励: <b>{bounty['reward']}</b> MP\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"<i>\"先完成者得奖！\"</i>"
                )

                buttons = [
                    [InlineKeyboardButton("🎲 新悬赏", callback_data="mission_refresh_bounty"),
                     InlineKeyboardButton("📋 每日任务", callback_data="mission_tab_daily")],
                ]
            else:
                txt = (
                    f"📜 <b>悬 赏 任 务</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"<i>暂无悬赏，点击下方按钮发布~</i>"
                )

                buttons = [
                    [InlineKeyboardButton("🎲 发布悬赏", callback_data="mission_post_bounty"),
                     InlineKeyboardButton("📋 每日任务", callback_data="mission_tab_daily")],
                ]


    # 发送/编辑消息（在 with 块外）
    if query:
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            pass
    else:
        await msg.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))


# ==========================================
# 悬赏任务发布
# ==========================================
async def post_bounty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发布新的悬赏任务"""
    msg = update.effective_message
    if not msg:
        return

    chat_id = msg.chat.id

    # 检查当前是否有未完成任务
    if chat_id in CURRENT_BOUNTY:
        bounty = CURRENT_BOUNTY[chat_id]
        bounty_type = bounty["type"]
        bounty_info = BOUNTY_TYPES[bounty_type]

        await reply_with_auto_delete(
            msg,
            f"⚠️ <b>悬赏令已存在！</b>\n"
            f"当前任务：{bounty_info['emoji']} <b>{bounty_info['name']}</b>\n"
            f"请先完成它！"
        )
        return

    # 随机选择任务类型
    task_type = random.choice(list(BOUNTY_TYPES.keys()))
    task_info = BOUNTY_TYPES[task_type]

    target = random.randint(*task_info["target_range"])
    reward = random.randint(*task_info["reward_range"])

    if task_type == "quiz":
        a, b = random.randint(10, 99), random.randint(10, 99)
        op = random.choice(["+", "-", "*"])
        if op == "*":
            a, b = random.randint(2, 12), random.randint(2, 12)

        answer = str(eval(f"{a}{op}{b}"))
        question = f"{a} {op} {b} = ?"

        CURRENT_BOUNTY[chat_id] = {
            "type": "quiz",
            "answer": answer,
            "question": question,
            "target": 1,
            "reward": reward,
            "start_time": datetime.now(),
        }
    else:
        CURRENT_BOUNTY[chat_id] = {
            "type": task_type,
            "target": target,
            "progress": {},
            "snapshot": {},
            "reward": reward,
            "start_time": datetime.now(),
        }

    txt = (
        f"📜 <b>【 公 会 · 紧 急 悬 赏 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{task_info['emoji']} <b>{task_info['name']}</b>\n"
    )

    if task_type == "quiz":
        txt += f"🧠 <b>魔法谜题：</b> <code>{question}</code>\n"
    else:
        txt += f"{task_info['desc_template'].format(target=target)}\n"

    txt += (
        f"\n💰 <b>悬赏金额：</b> <b>{reward} MP</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"猎人们，行动起来！\"</i>"
    )

    sent_msg = await msg.reply_html(txt)
    CURRENT_BOUNTY[chat_id]["msg"] = sent_msg


# ==========================================
# 悬赏进度检查
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

    if task_type != trigger_type:
        return

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=uid).first()

        if not u:
            return

        completed = False
        title = ""

        if task_type == "chat":
            current = mission["progress"].get(uid, 0) + 1
            mission["progress"][uid] = current
            if current >= mission["target"]:
                completed = True
                title = BOUNTY_TYPES["chat"]["title"]

        elif task_type == "duel":
            current_count = u.daily_duel_count or 0
            if uid not in mission["snapshot"]:
                mission["snapshot"][uid] = current_count
            else:
                delta = current_count - mission["snapshot"][uid]
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
    correct_answer = mission["answer"]

    # 尝试多种匹配方式
    is_correct = False

    # 1. 精确匹配
    if user_text == correct_answer:
        is_correct = True
    # 2. 去空格匹配（如 "45-97"）
    elif user_text.replace(" ", "") == correct_answer:
        is_correct = True
    # 3. 中文数字格式 (如 "负五十二" 或 "负52")
    elif user_text.startswith("负") or user_text.startswith("minus") or user_text.startswith("-"):
        num_part = user_text[1:] if user_text[0] in "负-" else user_text[5:]
        try:
            if int(num_part) == int(correct_answer):
                is_correct = True
        except ValueError:
            pass

    if is_correct:
        await settle_bounty(update, context, update.effective_user.id, BOUNTY_TYPES["quiz"]["title"])


async def settle_bounty(update: Update, context: ContextTypes.DEFAULT_TYPE, winner_id: int, title: str):
    """结算悬赏任务"""
    chat_id = update.effective_chat.id
    mission = CURRENT_BOUNTY.get(chat_id)

    if not mission:
        return

    reward = mission["reward"]

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=winner_id).first()

        bonus_msg = ""
        winner_name = update.effective_user.first_name
        points_awarded = False

        if u:
            if u.is_vip:
                bonus = int(reward * 0.2)
                reward += bonus
                bonus_msg = f" (👑 VIP加成 +{bonus})"

            u.points += reward
            winner_name = u.emby_account or winner_name
            points_awarded = True
            session.commit()
        else:
            # 未绑定用户，提示绑定后奖励
            bonus_msg = f" (请先 /bind 绑定账号后联系管理员领取)"


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
        f"<i>\"真是令人惊叹的行动力！\"</i>"
    )

    try:
        if "msg" in mission:
            await mission["msg"].delete()
    except Exception:
        pass

    del CURRENT_BOUNTY[chat_id]


# ==========================================
# 消息监听（聊天挖矿 + 悬赏进度 + 数学题）
# ==========================================
async def on_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """监听所有消息，处理聊天挖矿和悬赏进度"""
    user = update.effective_user
    if user.is_bot:
        return

    chat = update.effective_chat
    if chat.type == "private":
        return

    # 先检查数学题（即使未绑定也能回答）
    await check_quiz_answer(update, context)

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user.id).first()

        if not u:
            return

        # 检查每日任务进度
        new_completed, task_name, base_reward = update_task_progress(u, "chat", 1)

        # 始终提交 session 以保存 task_progress
        session.commit()

        if new_completed:
            reward = base_reward
            if u.is_vip:
                reward = int(reward * 1.5)

            # 任务完成后额外奖励魔力
            with get_session() as reward_session:
                reward_user = reward_session.query(UserBinding).filter_by(tg_id=user.id).first()
                if reward_user:
                    reward_user.points += reward
                    reward_session.commit()

            msg = (
                f"🎉 <b>【 每 日 任 务 · 完 成 ！】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✨ <b>完成任务：</b> {task_name}\n"
                f"💰 <b>获得奖励：</b> +{reward} MP\n"
                f"{'👑 VIP加成 +50%' if u.is_vip else ''}\n"
                f"━━━━━━━━━━━━━━━━━━"
            )
            await reply_with_auto_delete(update.message, msg, disable_notification=True)


    # 检查悬赏进度（在 with 块外）
    await check_bounty_progress(update, context, "chat")


# ==========================================
# 供其他模块调用的函数
# ==========================================
async def track_and_check_task(user_id: int, task_type: str) -> tuple:
    """
    追踪并检查任务进度
    返回：(是否有新完成，消息文本)
    """
    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not u:
            return False, None

        new_completed, task_name, base_reward = update_task_progress(u, task_type, 1)

        if new_completed:
            reward = base_reward
            if u.is_vip:
                reward = int(reward * 1.5)

            u.points += reward
            session.commit()

            msg = (
                f"🎉 <b>【 每 日 任 务 · 完 成 ！】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✨ <b>完成任务：</b> {task_name}\n"
                f"💰 <b>获得奖励：</b> +{reward} MP\n"
                f"{'👑 VIP加成 +50%' if u.is_vip else ''}\n"
                f"━━━━━━━━━━━━━━━━━━"
            )
            return True, msg

        return False, None


async def get_task_status(user_id: int) -> dict:
    """
    获取用户当前任务状态（实时）
    返回任务字典，包含最新进度
    """
    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not u:
            return {}

        # 强制刷新以确保获取最新数据
        session.refresh(u)

        return get_user_daily_tasks(u)


# ==========================================
# 回调处理
# ==========================================
async def mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理任务界面回调"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "mission_tab_daily":
        await mission_main(update, context, "daily")
    elif data == "mission_tab_bounty":
        await mission_main(update, context, "bounty")
    elif data == "mission_post_bounty":
        # 发布悬赏后刷新界面
        chat_id = query.message.chat.id
        # 创建假的 update 用于 post_bounty
        fake_update = type('Update', (), {
            'effective_message': query.message,
            'effective_chat': query.message.chat,
            'effective_user': query.from_user,
        })()
        await post_bounty(fake_update, context)
        # 刷新悬赏界面
        await mission_main(update, context, "bounty")
    elif data == "mission_refresh_bounty":
        # 刷新悬赏（删除旧的，发布新的）
        chat_id = query.message.chat.id
        if chat_id in CURRENT_BOUNTY:
            # 删除旧悬赏的消息
            try:
                old_bounty = CURRENT_BOUNTY[chat_id]
                if "msg" in old_bounty:
                    await old_bounty["msg"].delete()
            except Exception:
                pass
            del CURRENT_BOUNTY[chat_id]
        # 发布新悬赏
        fake_update = type('Update', (), {
            'effective_message': query.message,
            'effective_chat': query.message.chat,
            'effective_user': query.from_user,
        })()
        await post_bounty(fake_update, context)
        # 刷新界面
        await mission_main(update, context, "bounty")
    elif data == "mission_refresh_daily":
        # 刷新每日任务（花费MP）
        user_id = query.from_user.id
        refresh_cost = 20  # 刷新消耗20MP

        with get_session() as session:
            u = session.query(UserBinding).filter_by(tg_id=user_id).first()

            if not u or not u.emby_account:
                await query.edit_message_text("💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
                return

            # 检查魔力
            if u.points < refresh_cost:
                await query.edit_message_text(
                    f"💸 <b>【 魔 力 不 足 】</b>\n\n"
                    f"刷新任务需要 <b>{refresh_cost} MP</b>\n"
                    f"当前余额：{u.points} MP",
                    parse_mode='HTML'
                )
                return

            # 扣除消耗
            u.points -= refresh_cost

            # 重新生成每日任务
            selected_tasks = []
            # 1. 聊天任务（必选）
            selected_tasks.append(random.choice(TASK_POOL[0]))

            # 2. 确保至少1个免费任务
            free_tasks = [t for t in TASK_POOL[1] if t in TASK_TIERS["free"]]
            selected_tasks.append(random.choice(free_tasks))

            # 3. 第三个任务随机（可以是任何任务）
            remaining = [t for t in TASK_POOL[1] if t not in selected_tasks]
            selected_tasks.append(random.choice(remaining))

            u.task_date = datetime.now()
            u.daily_tasks = ",".join(selected_tasks)
            u.task_progress = "0,0,0"

            session.commit()

            remaining_points = u.points

        # 刷新成功
        await query.edit_message_text(
            f"🔄 <b>【 任 务 已 刷 新 】</b>\n\n"
            f"💰 消耗：{refresh_cost} MP\n"
            f"💎 余额：{remaining_points} MP\n\n"
            f"<i>\"新任务已生成，加油完成喵~(｡•̀ᴗ-)✧\"</i>",
            parse_mode='HTML'
        )
        # 延迟后刷新界面
        await mission_main(update, context, "daily")


# ==========================================
# 注册处理器
# ==========================================
def register(app):
    # 任务主命令（/mission）
    app.add_handler(CommandHandler("mission", mission_main))

    # 任务相关回调
    app.add_handler(CallbackQueryHandler(mission_callback, pattern=r"^mission_"))

    # 监听所有文本消息（用于每日任务进度追踪）
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_chat_message))
