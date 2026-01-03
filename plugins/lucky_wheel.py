"""
幸运转盘系统 - 每日免费抽奖
- 每天免费转一次
- VIP额外一次
- 奖池包含MP、道具、神秘大奖
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding
from utils import reply_with_auto_delete, edit_with_auto_delete
from datetime import datetime, date
import random

# 转盘奖励配置
WHEEL_PRIZES = [
    # 奖励类型, 数量/描述, 权重, emoji
    ("points", 5, 25, "💎"),       # 5MP - 最常见
    ("points", 10, 20, "💎"),      # 10MP
    ("points", 20, 15, "💰"),      # 20MP
    ("points", 50, 8, "💰"),       # 50MP
    ("points", 100, 4, "💎"),      # 100MP
    ("points", 200, 2, "🌟"),      # 200MP - 稀有
    ("points", 500, 0.5, "🌠"),    # 500MP - 超稀有
    ("lucky", 1, 5, "🍀"),         # 幸运草
    ("shield", 1, 4, "🛡️"),       # 防御卷轴
    ("tarot", 1, 4, "🔮"),         # 塔罗券
    ("gacha", 1, 4, "🎰"),         # 盲盒券
    ("forge_small", 1, 3, "⚒️"),   # 小锻造锤
    ("forge_big", 1, 1, "⚒️"),     # 大锻造锤
    ("nothing", 0, 5, "💨"),       # 空气 - 稍微安慰一下
]

def get_today():
    return datetime.now().date()


def spin_wheel(user: UserBinding, is_vip_bonus: bool = False) -> dict:
    """转动转盘，返回结果"""
    # 构建权重池
    pool = []
    for prize in WHEEL_PRIZES:
        prize_type, value, weight, emoji = prize
        # VIP权重稍微加成
        if user.is_vip and prize_type in ["points", "lucky", "shield", "tarot", "gacha"]:
            weight *= 1.2
        pool.extend([prize] * int(weight * 10))  # 放大10倍取整

    result = random.choice(pool)
    prize_type, value, _, emoji = result

    # 构建返回结果
    output = {
        "type": prize_type,
        "value": value,
        "emoji": emoji,
        "name": "",
        "is_jackpot": False
    }

    if prize_type == "points":
        output["name"] = f"{value} MP"
        if value >= 200:
            output["is_jackpot"] = True
    elif prize_type == "lucky":
        output["name"] = "幸运草 (下次签到暴击率UP)"
    elif prize_type == "shield":
        output["name"] = "防御卷轴 (下次决斗失败不掉钱)"
    elif prize_type == "tarot":
        output["name"] = "塔罗占卜券"
    elif prize_type == "gacha":
        output["name"] = "盲盒抽取券"
    elif prize_type == "forge_small":
        output["name"] = "免费锻造券(小)"
    elif prize_type == "forge_big":
        output["name"] = "高级锻造券(大)"
    elif prize_type == "nothing":
        output["name"] = "空气...下次一定！"

    return output


async def wheel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """幸运转盘主命令"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not u or not u.emby_account:
            await reply_with_auto_delete(msg, "💔 <b>请先绑定账号喵！</b>")
            return

        today = get_today()
        spin_date = u.last_wheel_date
        if spin_date:
            last_date = spin_date.date() if isinstance(spin_date, datetime) else spin_date
        else:
            last_date = None

        # 检查今日已转次数
        spun_today = last_date and last_date >= today
        free_spins = 0
        if not spun_today:
            free_spins = 1
        if u.is_vip:
            free_spins += 1  # VIP额外一次

        vip_badge = " 👑" if u.is_vip else ""
        spin_emoji = "🎡" if not spun_today else "✅"
        emby_account = u.emby_account
        points = u.points

    txt = (
        f"🎡 <b>【 幸 运 大 转 盘 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>玩家：</b> {emby_account}{vip_badge}\n"
        f"💰 <b>钱包：</b> {points} MP\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )

    if spun_today:
        txt += (
            f"{spin_emoji} <b>今日已免费抽奖</b>\n\n"
            f"明天再来碰碰运气吧！\n"
            f"<i>\"成为VIP可获得每日2次抽奖机会哦！\"</i>"
        )
    else:
        txt += (
            f"{spin_emoji} <b>免费次数：</b> {free_spins} 次\n\n"
            f"💎 <b>奖池包含：</b>\n"
            f"   • 💎 MP奖励 (5~500)\n"
            f"   • 🍀 幸运草\n"
            f"   • 🛡️ 防御卷轴\n"
            f"   • 🔮 各种道具券\n\n"
            f"<i>\"点击下方按钮开始抽奖！\"</i>"
        )

    buttons = []
    if not spun_today:
        buttons.append([InlineKeyboardButton("🎡 开始抽奖", callback_data="wheel_spin")])

    if free_spins > 0:
        buttons.append([InlineKeyboardButton("🎲 抽一次", callback_data="wheel_spin")])

    await msg.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)


async def wheel_spin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理抽奖回调"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not u or not u.emby_account:
            await edit_with_auto_delete(query, "💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        today = get_today()
        spin_date = u.last_wheel_date
        if spin_date:
            last_date = spin_date.date() if isinstance(spin_date, datetime) else spin_date
        else:
            last_date = None

        # 检查是否还能抽
        spun_today = last_date and last_date >= today

        # VIP检查
        can_spin = not spun_today
        if u.is_vip and spun_today and u.wheel_spins_today < 2:
            can_spin = True

        if not can_spin:
            await edit_with_auto_delete(
                query,
                "⏰ <b>今日次数已用完</b>\n\n明天再来吧！",
                parse_mode='HTML'
            )
            return

        # 记录抽奖次数
        if not spun_today:
            u.wheel_spins_today = 1
            u.last_wheel_date = datetime.now()
        else:
            u.wheel_spins_today = (u.wheel_spins_today or 1) + 1

        # 转动转盘
        result = spin_wheel(u)

        # 发放奖励
        reward_msg = ""
        if result["type"] == "points":
            u.points += result["value"]
            reward_msg = f"+{result['value']} MP"
        elif result["type"] == "lucky":
            u.lucky_boost = True
            reward_msg = "幸运草已激活"
        elif result["type"] == "shield":
            u.shield_active = True
            reward_msg = "防御卷轴已激活"
        elif result["type"] == "tarot":
            u.extra_tarot = (u.extra_tarot or 0) + 1
            reward_msg = "塔罗券+1"
        elif result["type"] == "gacha":
            u.extra_gacha = (u.extra_gacha or 0) + 1
            reward_msg = "盲盒券+1"
        elif result["type"] == "forge_small":
            u.free_forges = (u.free_forges or 0) + 1
            reward_msg = "锻造券+1"
        elif result["type"] == "forge_big":
            u.free_forges_big = (u.free_forges_big or 0) + 1
            reward_msg = "高级锻造券+1"
        elif result["type"] == "nothing":
            reward_msg = "再接再厉..."

        session.commit()

        # 保存需要在session关闭后使用的值
        points = u.points
        is_jackpot = result["is_jackpot"]
        result_emoji = result["emoji"]
        result_name = result["name"]

    # 构建结果消息（在with块外）
    title = "🌠 <b>【 大 奖 ！】</b>" if is_jackpot else "🎡 <b>【 抽 奖 结 果 】</b>"

    txt = (
        f"{title}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{result_emoji} <b>获得：</b> {result_name}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )

    if is_jackpot:
        txt += f"🎉 <b>恭喜！欧气满满！</b>\n\n"

    txt += (
        f"💰 <b>当前余额：</b> {points} MP\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"明天再来哦！\"</i>"
    )

    buttons = [[InlineKeyboardButton("🔙 返回", callback_data="wheel_back")]]

    try:
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
    except Exception:
        await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))


async def wheel_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """返回转盘主页"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not u or not u.emby_account:
            await edit_with_auto_delete(query, "💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        today = get_today()
        spin_date = u.last_wheel_date
        if spin_date:
            last_date = spin_date.date() if isinstance(spin_date, datetime) else spin_date
        else:
            last_date = None

        spun_today = last_date and last_date >= today
        free_spins = 0 if spun_today else (2 if u.is_vip else 1)

        vip_badge = " 👑" if u.is_vip else ""
        emby_account = u.emby_account
        points = u.points

    txt = (
        f"🎡 <b>【 幸 运 大 转 盘 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>玩家：</b> {emby_account}{vip_badge}\n"
        f"💰 <b>钱包：</b> {points} MP\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )

    if spun_today:
        txt += f"✅ <b>今日已免费抽奖</b>\n\n明天再来吧！"
    else:
        txt += f"🎲 <b>免费次数：</b> {free_spins} 次\n\n点击下方按钮开始抽奖！"

    buttons = []
    if not spun_today:
        buttons.append([InlineKeyboardButton("🎡 开始抽奖", callback_data="wheel_spin")])


    try:
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None, parse_mode='HTML')
    except Exception:
        pass


def register(app):
    app.add_handler(CommandHandler("wheel", wheel_cmd))
    app.add_handler(CommandHandler("spin", wheel_cmd))
    app.add_handler(CommandHandler("lucky", wheel_cmd))
    app.add_handler(CallbackQueryHandler(wheel_spin_callback, pattern=r"^wheel_spin$"))
    app.add_handler(CallbackQueryHandler(wheel_back_callback, pattern=r"^wheel_back$"))
