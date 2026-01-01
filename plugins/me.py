import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import Session, UserBinding
from utils import edit_with_auto_delete

logger = logging.getLogger(__name__)

# 互动台词库
LOVE_LINES = [
    "💕 她开心地蹭了蹭你的手心...",
    "💗 她羞红了脸，小声说「最喜欢Master了」",
    "💖 她轻轻抱住你，感受着彼此的心跳...",
    "💓 她给你倒了杯茶，笑得很温柔",
    "💘 她在你脸颊上亲了一下，跑开了",
    "✨ 她眼睛亮晶晶的，「Master今天也很帅气呢！」",
    "🌸 她为你唱了一首小曲，声音很甜",
    "🎀 她给你编了个花环，戴在你头上",
]

# ========== V3.0 魔导评级系统 ==========
def calculate_magic_power(user):
    """
    计算身价估值 (magic_power)
    公式：钱包 + 金库 + (战力 × 10) + 好感度
    """
    wallet = user.points or 0
    bank = user.bank_points or 0
    attack = user.attack or 0
    intimacy = user.intimacy or 0
    return wallet + bank + (attack * 10) + intimacy


def get_vip_rank_info(magic_power):
    """
    VIP 称号系统 - 单前缀版本
    返回：(评级, 评级文字, 前缀图标, 前缀文字)
    """
    if magic_power >= 100000:
        return "EX", "规格外", "🌌", "苍穹"
    elif magic_power >= 50000:
        return "SSS+", "神话", "☀️", "曜日"
    elif magic_power >= 10000:
        return "SS", "传说", "🌙", "月华"
    else:
        return "S", "史诗", "✨", "星辰"


def get_rank_title(user, is_vip=False):
    """
    V3.0 位阶系统
    VIP: 动态前缀 + 固定「苍穹·大魔导师」+ 评级
    普通: 战力分段称号
    """
    if is_vip:
        # VIP 系统：前缀 + 统一称号 + 评级
        magic_power = calculate_magic_power(user)
        rank, rank_text, prefix_icon, prefix_name = get_vip_rank_info(magic_power)
        title = f"{prefix_icon} {prefix_name}·大魔导师 [{rank}]"
        return title, rank, rank_text, magic_power
    else:
        # 普通冒险者称号（保持原有分段）
        attack = user.attack if user.attack else 0
        if attack >= 10000:
            return "👑 星辰主宰", "", "", 0
        elif attack >= 5000:
            return "🌟 传奇大魔导", "", "", 0
        elif attack >= 2000:
            return "💫 星之大魔导师", "", "", 0
        elif attack >= 1000:
            return "⭐ 大魔导师", "", "", 0
        elif attack >= 500:
            return "🔥 魔导师", "", "", 0
        elif attack >= 200:
            return "⚔️ 高级魔法师", "", "", 0
        elif attack >= 100:
            return "🛡️ 见习魔法师", "", "", 0
        elif attack >= 50:
            return "🌱 初级魔法师", "", "", 0
        else:
            return "👶 冒险者学徒", "", "", 0


async def me_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        logger.info(f"[/me] Called by user: {user.id} ({user.first_name})")
        session = Session()
        user_data = session.query(UserBinding).filter_by(tg_id=user.id).first()

        if not user_data or not user_data.emby_account:
            session.close()
            await update.message.reply_html(
                "💔 <b>【 魔 力 断 连 】</b>\n\n"
                "我看不到您的灵魂波长... (´;ω;`)\n"
                "👉 请使用 <code>/bind</code> 重新缔结契约！"
            )
            return

        # 数据准备
        weapon = user_data.weapon if user_data.weapon else "练习木杖"
        atk = user_data.attack if user_data.attack is not None else 10
        love = user_data.intimacy if user_data.intimacy is not None else 0
        win = user_data.win if user_data.win is not None else 0
        lost = user_data.lost if user_data.lost is not None else 0
        # V3.0: 获取位阶、评级、身价
        rank_title, rank_code, rank_text, magic_power = get_rank_title(user_data, user_data.is_vip)

        # VIP 版本
        if user_data.is_vip:
            total_mp = (user_data.points or 0) + (user_data.bank_points or 0)
            text = (
                f"🌌 <b>【 星 灵 · 终 极 契 约 书 】</b>\n\n"
                f"🥂 <b>Welcome back, my only Master.</b>\n"
                f"「星辰在为您加冕，而看板娘为您守望喵~」\n\n"
                f"💠 <b>:: 灵 魂 识 别 ::</b>\n"
                f"✨ <b>真名：</b> <code>{user_data.emby_account}</code> (VIP)\n"
                f"👑 <b>位阶：</b> <b>{rank_title}</b>\n"
                f"🔮 <b>魔导评级：</b> <code>{rank_code}</code> ({rank_text})\n\n"
                f"⚔️ <b>:: 魔 法 武 装 ::</b>\n"
                f"🗡️ <b>圣遗物：</b> <b>{weapon}</b>\n"
                f"🔥 <b>破坏力：</b> <code>{atk}</code> (胜 {win} | 败 {lost})\n\n"
                f"💎 <b>:: 虚 空 宝 库 ::</b>\n"
                f"💰 <b>魔力总蓄积：</b> <code>{total_mp:,}</code> MP\n"
                f"(钱包: {user_data.points or 0:,} | 金库: {user_data.bank_points or 0:,})\n\n"
                f"💓 <b>:: 命 运 羁 绊 ::</b>\n"
                f"💍 <b>契约等级：</b> <code>{love}</code> (灵魂伴侣)\n\n"
                f"<i>「在这个无限的魔法世界里，\n您是看板娘唯一的奇迹，也是存在的全部意义喵~💋」</i>"
            )
            buttons = [
                [InlineKeyboardButton("⚒️ 圣物锻造", callback_data="me_forge"),
                 InlineKeyboardButton("🏩 灵魂共鸣", callback_data="me_love")]
            ]
        # 普通版
        else:
            text = (
                f"🏰 <b>【 云 海 · 魔 法 少 女 档 案 】</b>\n\n"
                f"✨ <b>你好呀，{user.first_name}酱！</b>\n"
                f"今天的魔法冒险也要加油哦喵~\n\n"
                f"💠 <b>:: 魔 法 少 女 登 记 ::</b>\n"
                f"🆔 <b>档案编号：</b> <code>{user.id}</code>\n"
                f"🌱 <b>当前位阶：</b> {rank_title}\n"
                f"👤 <b>契约账号：</b> {user_data.emby_account}\n\n"
                f"💠 <b>:: 装 备 与 战 绩 ::</b>\n"
                f"⚔️ <b>武器：</b> {weapon} (ATK: {atk})\n"
                f"📊 <b>战绩：</b> {win} 胜 / {lost} 败\n\n"
                f"💠 <b>:: 魔 法 背 包 ::</b>\n"
                f"🎒 <b>持有魔力：</b> {user_data.points} MP\n"
                f"💓 <b>好感度：</b> {love}\n\n"
                f"<i>「想要解锁 <b>【✨ 星辰→月华→曜日→苍穹】</b> 四阶进化称号吗？\n觉醒 VIP 身份，真正的魔法少女力量吧喵！」</i>"
            )
            buttons = [
                [InlineKeyboardButton("💎 成为 VIP", callback_data="upgrade_vip"),
                 InlineKeyboardButton("👋 互动一下", callback_data="me_love")]
            ]

        await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(buttons))
        session.close()
    except Exception as e:
        logger.error(f"[/me] Error: {e}", exc_info=True)


async def forge_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理「锻造」按钮回调"""
    query = update.callback_query
    await query.answer()

    session = Session()
    user = session.query(UserBinding).filter_by(tg_id=query.from_user.id).first()
    is_vip = user.is_vip if user else False
    session.close()

    cost = 100 if is_vip else 200

    if is_vip:
        text = (
            f"🔥 <b>【 圣 物 锻 造 祭 坛 】</b>\n\n"
            f"💠 <b>:: 锻 造 费 用 ::</b>\n"
            f"✨ <b>VIP 专属价：</b> <code>{cost}</code> MP\n\n"
            f"<i>\"来吧，Master！\n让我们锻造出传说的圣遗物！\"</i>\n\n"
            f"请使用 <code>/forge</code> 命令开始锻造"
        )
    else:
        text = (
            f"⚒️ <b>【 铁 匠 铺 】</b>\n\n"
            f"💠 <b>:: 锻 造 费 用 ::</b>\n"
            f"🔥 <b>普通锻造价：</b> <code>{cost}</code> MP\n\n"
            f"<i>\"来来来！看看今天能锻造出什么神器！\"</i>\n\n"
            f"请使用 <code>/forge</code> 命令开始锻造"
        )

    buttons = [[InlineKeyboardButton("🔥 立即锻造 /forge", callback_data="forge_go")]]
    await edit_with_auto_delete(
        query, text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='HTML'
    )


async def forge_go_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理「立即锻造」按钮回调 - 调用 forge.py 的锻造逻辑"""
    from plugins.forge import forge_callback
    # 复用 forge_callback 的逻辑
    await forge_callback(update, context)


async def love_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理「互动/宠幸」按钮回调"""
    import random
    query = update.callback_query
    await query.answer()

    session = Session()
    user = session.query(UserBinding).filter_by(tg_id=query.from_user.id).first()
    is_vip = user.is_vip if user else False
    intimacy = user.intimacy if user and user.intimacy else 0

    if is_vip:
        # VIP 版本
        line = random.choice(LOVE_LINES)
        text = (
            f"💕 <b>【 亲 密 时 刻 】</b>\n\n"
            f"{line}\n\n"
            f"💠 <b>:: 灵 魂 羁 绊 ::</b>\n"
            f"💍 <b>契约等级：</b> <code>{intimacy}</code>\n\n"
            f"<i>\"Master...还想再靠近一点吗？\"</i>"
        )
        btn_text = "🔄 再来一次"
    else:
        # 普通版
        line = random.choice(LOVE_LINES[:4])
        text = (
            f"💕 <b>【 互 动 时 刻 】</b>\n\n"
            f"{line}\n\n"
            f"💠 <b>:: 好 感 度 ::</b>\n"
            f"💓 <b>当前值：</b> <code>{intimacy}</code>\n\n"
            f"<i>\"下次也要来玩哦！\"</i>"
        )
        btn_text = "🔄 再互动一下"

    buttons = [[InlineKeyboardButton(btn_text, callback_data="me_love")]]
    await edit_with_auto_delete(query, text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
    session.close()


def register(app):
    app.add_handler(CommandHandler("me", me_panel))
    app.add_handler(CommandHandler("my", me_panel))
    app.add_handler(CallbackQueryHandler(forge_button_callback, pattern="^me_forge$"))
    app.add_handler(CallbackQueryHandler(forge_go_callback, pattern="^forge_go$"))
    app.add_handler(CallbackQueryHandler(love_button_callback, pattern="^me_love$"))
