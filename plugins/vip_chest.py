"""
VIP专属宝箱系统
- VIP用户每日可开启一次专属宝箱
- 必定获得有价值的奖励
- 有几率开出稀有物品
"""
import random
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding
from utils import edit_with_auto_delete, reply_with_auto_delete

logger = logging.getLogger(__name__)


# ==========================================
# 宝箱奖励配置
# ==========================================
CHEST_REWARDS = [
    # 权重, 类型, 名称, 数量/范围, emoji
    (350, "points", "500-1000 MP", (500, 1000), "💰"),
    (250, "lucky_boost", "幸运草", 1, "🍀"),
    (150, "extra_gacha", "盲盒券", 1, "🎰"),
    (100, "free_forge_big", "高级锻造券", 1, "⚒️"),
    (80, "free_resonance", "灵魂共鸣券", 1, "💝"),
    (50, "ur_fragment", "UR武器碎片", 1, "🔮"),
    (20, "points_bonus", "1000 MP暴击", 1000, "💫"),
]

# 稀有度效果文案
RARITY_EFFECTS = {
    "common": [
        "✨ 宝箱缓缓打开，一道光芒闪过...",
        "🌟 锁扣发出清脆的声响，宝藏显现...",
        "💫 金色的雾气散去，奖励在等待...",
    ],
    "rare": [
        "🌠 宝箱发出耀眼的光芒！是稀有的奖励！",
        "✨✨ 空气中弥漫着魔力的波动...这感觉不一般！",
        "💫💫 宝箱震动了一下，似乎有什么好东西...",
    ],
    "epic": [
        "🌈🌈 彩色的光芒冲天而起！传说中的奖励！",
        "✨🌟✨ 整个房间都被照亮了！这是史诗级的奖励！",
        "💫🌠💫 空间都在震动！极其罕见的好运！",
    ],
}


def get_chest_reward() -> dict:
    """
    随机获取宝箱奖励

    返回: {
        'type': 奖励类型,
        'name': 奖励名称,
        'amount': 数量,
        'emoji': 图标,
        'rarity': 稀有度 (common/rare/epic),
        'effect': 效果描述,
    }
    """
    # 权重随机
    total_weight = sum(w for w, _, _, _, _ in CHEST_REWARDS)
    roll = random.randint(1, total_weight)
    cumulative = 0

    reward_data = None
    for weight, r_type, name, amount, emoji in CHEST_REWARDS:
        cumulative += weight
        if roll <= cumulative:
            reward_data = (r_type, name, amount, emoji)
            break

    r_type, name, amount, emoji = reward_data

    # 确定稀有度和效果
    if r_type in ["ur_fragment", "points_bonus"]:
        rarity = "epic"
        effect = random.choice(RARITY_EFFECTS["epic"])
    elif r_type in ["free_forge_big", "free_resonance"]:
        rarity = "rare"
        effect = random.choice(RARITY_EFFECTS["rare"])
    else:
        rarity = "common"
        effect = random.choice(RARITY_EFFECTS["common"])

    # 处理范围数量
    if isinstance(amount, tuple):
        amount = random.randint(*amount)

    return {
        'type': r_type,
        'name': name,
        'amount': amount,
        'emoji': emoji,
        'rarity': rarity,
        'effect': effect,
    }


async def apply_reward(user_id: int, reward: dict) -> str:
    """应用奖励到用户"""
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user:
            return "❌ 用户不存在"

        r_type = reward['type']
        amount = reward['amount']

        if r_type == "points":
            user.points += amount
            session.commit()
            return f"💰 <b>获得魔力：</b>+{amount} MP"

        elif r_type == "points_bonus":
            user.points += amount
            session.commit()
            return f"💫 <b>暴击奖励：</b>+{amount} MP"

        elif r_type == "lucky_boost":
            user.lucky_boost = True
            session.commit()
            return f"🍀 <b>幸运草：</b>下次签到必定暴击！"

        elif r_type == "extra_gacha":
            user.extra_gacha = (user.extra_gacha or 0) + amount
            session.commit()
            return f"🎰 <b>盲盒券：</b>+{amount} 张"

        elif r_type == "free_forge_big":
            user.free_forges_big = (user.free_forges_big or 0) + amount
            session.commit()
            return f"⚒️ <b>高级锻造券：</b>+{amount} 张（稀有度UP！）"

        elif r_type == "free_resonance":
            # 暂时用 extra_gacha 存储，或者需要新字段
            # 这里用一个简化的方式：用 points 暂存价值，实际使用时处理
            user.extra_gacha = (user.extra_gacha or 0) + amount
            session.commit()
            return f"💝 <b>灵魂共鸣券：</b>+{amount} 次（免费共鸣！）"

        elif r_type == "ur_fragment":
            # 存入 items 背包
            items = user.items or ""
            fragments = items.count("UR碎片") if "UR碎片" in items else 0
            new_count = fragments + amount
            # 更新背包
            item_list = items.split(",") if items else []
            # 移除旧的 UR碎片
            item_list = [i for i in item_list if i and i != "UR碎片"]
            # 添加新的
            item_list.extend(["UR碎片"] * new_count)
            user.items = ",".join(item_list)
            session.commit()
            return f"🔮 <b>UR武器碎片：</b>+{amount} 片（当前:{new_count}）"

        return "❓ 未知奖励"


def can_open_chest(user: UserBinding) -> tuple:
    """
    检查是否可以开启宝箱

    返回: (bool, str) - (是否可以, 原因描述)
    """
    if not user.is_vip:
        return False, "VIP专属功能"

    # 检查是否今天已开启
    if user.last_chest_open:
        # 判断是否是今天
        now = datetime.now()
        last_open = user.last_chest_open
        if last_open.date() >= now.date():
            # 计算距离下次开启的时间
            next_open = last_open.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            remaining = next_open - now
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            return False, f"今日已开启，还需{hours}小时{minutes}分钟"

    return True, "可以开启"


async def chest_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """VIP宝箱面板"""
    query = getattr(update, "callback_query", None)
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user or not user.emby_account:
            await reply_with_auto_delete(
                msg,
                "💔 <b>请先缔结魔法契约喵！</b>\n"
                "使用 <code>/bind</code> 绑定后再来~"
            )
            return

        can_open, reason = can_open_chest(user)

        if not user.is_vip:
            # 非VIP用户看到的界面（营销用）
            text = (
                "💎 <b>【 V I P · 专 属 宝 箱 】</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "🌟 <b>VIP专属每日福利</b>\n"
                f"🔒 <b>状态：</b>需要VIP权限\n\n"
                f"<b>✨ 宝箱奖励池：</b>\n"
                f"💰 500-1000 MP  (35%)\n"
                f"🍀 幸运草      (25%)\n"
                f"🎰 盲盒券      (15%)\n"
                f"⚒️ 高级锻造券  (10%)\n"
                f"💝 灵魂共鸣券  (8%)\n"
                f"🔮 UR武器碎片  (5%)\n"
                f"💫 1000MP暴击  (2%)\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "<i>\"成为VIP，每天开启专属宝箱！\"</i>\n"
                f"💡 成为VIP后使用 <code>/chest</code> 开启"
            )
            buttons = [[InlineKeyboardButton("💎 成为VIP", callback_data="upgrade_vip")]]
            if query:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
            else:
                await msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
            return

        if not can_open:
            # 今天已开启
            text = (
                "💎 <b>【 V I P · 专 属 宝 箱 】</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"🔒 <b>今日已开启</b>\n\n"
                f"⏰ {reason}\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "<i>\"明天再来，新的宝藏在等你哦~(｡•̀ᴗ-)✧\"</i>"
            )
            buttons = [[InlineKeyboardButton("🔙 返回", callback_data="me_back")]]
            if query:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
            else:
                await msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
            return

        # 可以开启
        text = (
            "💎 <b>【 V I P · 专 属 宝 箱 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🔓 <b>宝箱等待开启...</b>\n\n"
            f"✨ <b>每日必得：</b>\n"
            f"💰 500-1000 MP (35%)\n"
            f"🍀 幸运草 (25%)\n"
            f"🎰 盲盒券 (15%)\n"
            f"⚒️ 高级锻造券 (10%)\n"
            f"💝 灵魂共鸣券 (8%)\n"
            f"🔮 UR武器碎片 (5%)\n"
            f"💫 1000MP暴击 (2%)\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "<i>\"Master，快来开启今天的宝藏吧！\"</i>"
        )
        buttons = [[InlineKeyboardButton("🔑 开启宝箱", callback_data="chest_open")]]
        if query:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        else:
            await msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def chest_open_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理开启宝箱回调"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user or not user.is_vip:
            await edit_with_auto_delete(
                query,
                "💔 <b>需要VIP权限才能开启宝箱喵！</b>"
            )
            return

        can_open, reason = can_open_chest(user)
        if not can_open:
            await edit_with_auto_delete(
                query,
                f"🔒 <b>【 宝 箱 冷 却 中 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"⏰ {reason}"
            )
            return

    # 显示开箱动画
    loading_texts = [
        "🔑 宝箱锁扣发出清脆的声响...\n<i>\"咔嚓...\"</i>",
        "✨ 金色的光芒从缝隙中透出...\n<i>\"好像有什么好东西...\"</i>",
        "🌟 宝箱缓缓打开...\n<i>\"Master，接住你的奖励！\"</i>",
    ]
    for i, text in enumerate(loading_texts):
        await query.edit_message_text(
            f"💎 <b>【 开 启 中 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{text}"
        )
        # 添加短暂延迟营造开箱感
        import asyncio
        await asyncio.sleep(0.5)

    # 获取奖励
    reward = get_chest_reward()

    # 应用奖励
    reward_text = await apply_reward(user_id, reward)

    # 更新开启时间
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if user:
            user.last_chest_open = datetime.now()
            session.commit()

    # 稀有度标题
    rarity_titles = {
        "common": "💫 奖励",
        "rare": "✨ 稀有奖励",
        "epic": "🌈 传说奖励",
    }
    rarity_title = rarity_titles.get(reward['rarity'], "💫 奖励")

    # 构建结果消息
    result_text = (
        f"💎 <b>【 V I P · 宝 箱 奖 励 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{reward['effect']}\n\n"
        f"<b>{rarity_title}</b>\n"
        f"{reward['emoji']} {reward['name']}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{reward_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"明天再来，新的宝藏在等你哦~(｡•̀ᴗ-)✧\"</i>"
    )

    buttons = [[InlineKeyboardButton("🔙 返回", callback_data="me_back")]]

    await query.edit_message_text(
        result_text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='HTML'
    )

    # 追踪任务
    try:
        from plugins.unified_mission import track_and_check_task
        await track_and_check_task(user_id, "chest")
    except Exception as e:
        logger.error(f"[宝箱任务追踪] 错误: {e}", exc_info=True)


async def me_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """返回到 /me 面板"""
    query = update.callback_query
    await query.answer()

    # 简单提示用户使用 /me 命令
    await query.edit_message_text(
        "💫 请使用 /me 命令返回个人面板",
        parse_mode='HTML'
    )


def register(app):
    app.add_handler(CommandHandler("chest", chest_panel))
    app.add_handler(CallbackQueryHandler(chest_open_callback, pattern="^chest_open$"))
    app.add_handler(CallbackQueryHandler(me_back_callback, pattern="^me_back$"))
