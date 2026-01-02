"""
幸运空投系统 - 随机掉落宝箱
- 每隔一段时间在群聊随机掉落宝箱
- 第一个点击的人获得
- 增加群聊活跃度
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import Session, UserBinding
from datetime import datetime, timedelta
import random
import asyncio

# 空投配置
AIRDROP_CONFIG = {
    "min_interval": 1800,   # 最小间隔30分钟
    "max_interval": 5400,   # 最大间隔90分钟
    "duration": 120,        # 宝箱存在时间120秒
}

# 宝箱类型
CHEST_TYPES = [
    {"name": "青铜宝箱", "emoji": "🥉", "min": 30, "max": 80, "chance": 50},
    {"name": "白银宝箱", "emoji": "🥈", "min": 60, "max": 150, "chance": 30},
    {"name": "黄金宝箱", "emoji": "🥇", "min": 100, "max": 300, "chance": 15},
    {"name": "钻石宝箱", "emoji": "💎", "min": 200, "max": 500, "chance": 4},
    {"name": "传说宝箱", "emoji": "🌟", "min": 500, "max": 1000, "chance": 1},
]

# 存储活跃的空投 {chat_id: {"msg": msg, "reward": N, "expiry": datetime, "opened_by": set}}
ACTIVE_AIRDROPS = {}


def pick_random_chest() -> dict:
    """随机选择一个宝箱类型"""
    pool = []
    for chest in CHEST_TYPES:
        pool.extend([chest] * chest["chance"])
    return random.choice(pool)


async def spawn_airdrop(context):
    """定时任务：在活跃群聊中生成空投"""
    # 获取有绑定用户的群聊列表
    session = Session()
    users = session.query(UserBinding).filter(UserBinding.emby_account != None).all()

    if not users:
        session.close()
        return

    # 随机选一个用户的群聊（简化处理）
    # 实际应该维护一个活跃群聊列表
    selected_user = random.choice(users)

    # 生成随机奖励
    chest = pick_random_chest()
    reward = random.randint(chest["min"], chest["max"])

    session.close()

    # 发送空投消息（需要在群聊环境中）
    # 这里只存储数据，实际发送由触发器完成
    # 或者可以由管理员手动触发


async def airdrop_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """手动触发空投（管理员或随机触发）"""
    msg = update.effective_message
    if not msg or msg.chat.type == "private":
        return

    chat_id = msg.chat.id

    # 检查是否已有空投
    if chat_id in ACTIVE_AIRDROPS:
        existing = ACTIVE_AIRDROPS[chat_id]
        if existing["expiry"] > datetime.now():
            await reply_with_auto_delete(msg, "⚠️ <b>当前已有空投宝箱！</b>")
            return

    # 生成新空投
    chest = pick_random_chest()
    reward = random.randint(chest["min"], chest["max"])

    expiry = datetime.now() + timedelta(seconds=AIRDROP_CONFIG["duration"])

    txt = (
        f"✨ <b>【 幸 运 空 投 降 临 ！】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{chest['emoji']} <b>{chest['name']}</b>\n"
        f"💰 <b>包含：</b> {reward} MP\n"
        f"⏰ <b>有效期：</b> {AIRDROP_CONFIG['duration']}秒\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"第一个点击的人获得宝箱！\"</i>"
    )

    buttons = [[InlineKeyboardButton("🎁 打开宝箱", callback_data=f"airdrop_open_{reward}_{chest['emoji']}")]]

    sent_msg = await msg.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    ACTIVE_AIRDROPS[chat_id] = {
        "msg": sent_msg,
        "reward": reward,
        "expiry": expiry,
        "opened_by": set(),
        "chest_emoji": chest['emoji'],
        "chest_name": chest['name']
    }

    # 设置自动过期
    asyncio.create_task(airdrop_expire(chat_id, AIRDROP_CONFIG["duration"]))


async def airdrop_expire(chat_id: int, delay: int):
    """空投过期任务"""
    await asyncio.sleep(delay)

    if chat_id in ACTIVE_AIRDROPS:
        data = ACTIVE_AIRDROPS[chat_id]
        if data["expiry"] <= datetime.now():
            try:
                await data["msg"].edit_text(
                    f"💨 <b>【 宝 箱 消 失 了 】</b>\n\n没有人捡到这个宝箱...",
                    parse_mode='HTML'
                )
            except Exception:
                pass
            del ACTIVE_AIRDROPS[chat_id]


async def airdrop_open_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理开宝箱回调"""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    user_id = query.from_user.id

    # 检查空投是否存在
    if chat_id not in ACTIVE_AIRDROPS:
        await query.edit_message_text("💨 <b>宝箱已消失...</b>", parse_mode='HTML')
        return

    data = ACTIVE_AIRDROPS[chat_id]

    # 检查是否过期
    if data["expiry"] <= datetime.now():
        await query.edit_message_text("💨 <b>宝箱已过期...</b>", parse_mode='HTML')
        del ACTIVE_AIRDROPS[chat_id]
        return

    # 检查是否已打开
    if user_id in data["opened_by"]:
        await query.answer("你已经打开过这个宝箱了！", show_alert=True)
        return

    # 标记为已打开（第一个打开的人获得）
    data["opened_by"].add(user_id)

    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user_id).first()

    if not u or not u.emby_account:
        await query.edit_message_text("💔 <b>请先绑定账号才能领取宝箱！</b>", parse_mode='HTML')
        session.close()
        return

    reward = data["reward"]
    chest_emoji = data["chest_emoji"]
    chest_name = data["chest_name"]

    # VIP加成
    if u.is_vip:
        bonus = int(reward * 0.5)
        total = reward + bonus
        u.points += total
        vip_text = f"👑 <b>VIP加成：</b> +{bonus} MP\n"
    else:
        total = reward
        u.points += reward
        vip_text = ""

    session.commit()
    session.close()

    # 删除空投
    del ACTIVE_AIRDROPS[chat_id]

    txt = (
        f"{chest_emoji} <b>【 宝 箱 已 开 启 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎉 <b>开启者：</b> {query.from_user.first_name}\n"
        f"📦 <b>宝箱：</b> {chest_name}\n"
        f"💰 <b>获得：</b> +{reward} MP\n"
        f"{vip_text}"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>总计：</b> {total} MP"
    )

    try:
        await query.edit_message_text(txt, parse_mode='HTML')
    except Exception:
        await query.message.reply_html(txt)


def register(app):
    app.add_handler(CommandHandler("airdrop", airdrop_manual))
    app.add_handler(CallbackQueryHandler(airdrop_open_callback, pattern=r"^airdrop_open_"))
