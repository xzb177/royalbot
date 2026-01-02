"""
皇家银行系统 - 魔法少女版
- VIP用户：皇家魔法少女金库（0手续费 + 1%/天利息）
- 普通用户：魔法学院储蓄柜台（5%手续费 + 0.5%/天利息）
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete
from datetime import datetime, timedelta


# 利息配置
INTEREST_RATE_VIP = 0.01      # VIP日利率 1%
INTEREST_RATE_NORMAL = 0.005  # 普通用户日利率 0.5%
MAX_INTEREST_VIP = 100        # VIP每日利息上限
MAX_INTEREST_NORMAL = 50      # 普通用户每日利息上限


def calculate_interest(user: UserBinding, days: int = None) -> int:
    """计算利息收益"""
    if user.bank_points <= 0:
        return 0

    if days is None:
        # 计算从上次结算到现在经过的天数
        if user.last_interest_claimed:
            days = (datetime.now() - user.last_interest_claimed.replace(tzinfo=None)).days
        else:
            days = 0

    if days <= 0:
        return 0

    # 计算基础利息
    rate = INTEREST_RATE_VIP if user.is_vip else INTEREST_RATE_NORMAL
    max_daily = MAX_INTEREST_VIP if user.is_vip else MAX_INTEREST_NORMAL

    # 每天利息 = min(存款 × 利率, 上限)
    daily_interest = min(int(user.bank_points * rate), max_daily)
    total_interest = daily_interest * days

    return total_interest


async def bank_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """银行主面板"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    session = Session()
    user = session.query(UserBinding).filter_by(tg_id=user_id).first()

    if not user or not user.emby_account:
        session.close()
        await reply_with_auto_delete(msg, "💔 <b>【 魔 法 契 约 丢 失 】</b>\n请先使用 <code>/bind</code> 缔结契约喵！")
        return

    total = user.points + user.bank_points
    vip_badge = " 👑" if user.is_vip else ""

    # 计算累积利息
    accumulated = user.accumulated_interest or 0
    pending_interest = calculate_interest(user)

    # VIP和普通用户的不同界面
    if user.is_vip:
        text = (
            f"🏰 <b>【 皇 家 · 魔 法 少 女 金 库 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🥂 <b>Welcome, my dear Master~</b>\n"
            f"这是为您专属定制的皇家金库，您的魔力结晶在这里绝对安全喵~\n\n"
            f"💎 <b>资 产 总 览</b>\n"
            f"👑 <b>户主：</b> {user.emby_account}{vip_badge}\n"
            f"🏆 <b>身价：</b> {total} MP\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👛 <b>流动钱包：</b> {user.points} MP\n"
            f"🔐 <b>永恒金库：</b> {user.bank_points} MP\n"
            f"💰 <b>待领取利息：</b> {accumulated + pending_interest} MP\n"
            f"📈 <b>日利率：</b> 1% (上限100/天)\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>💡 VIP 特权：存取/转账 <b>0 手续费</b> + <b>银行利息</b> 喵~</i>\n"
            f"<i>\"取款时会自动结算利息哦，Master~(｡•̀ᴗ-)✧\"</i>"
        )
    else:
        text = (
            f"🏦 <b>【 魔 法 学 院 · 储 蓄 柜 台 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ <b>你好呀，理财小魔法少女！</b>\n"
            f"把魔力存进金库是好习惯喵~这样就不怕决斗输光光啦！\n\n"
            f"💰 <b>账 户 详 情</b>\n"
            f"👤 <b>户主：</b> {user.emby_account}{vip_badge}\n"
            f"💵 <b>资产：</b> {total} MP\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👛 <b>口袋零钱：</b> {user.points} MP\n"
            f"🏦 <b>学院存款：</b> {user.bank_points} MP\n"
            f"💰 <b>待领取利息：</b> {accumulated + pending_interest} MP\n"
            f"📈 <b>日利率：</b> 0.5% (上限50/天)\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>⚠️ 提现/转账需收 <b>5%</b> 手续费哦!</i>\n"
            f"<i>\"取款时会自动结算利息。想免除手续费吗？觉醒成为 <b>VIP</b> 吧！(≧◡≦)\"</i>"
        )

    buttons = [
        [InlineKeyboardButton("📥 存入全部", callback_data="bank_dep_all"),
         InlineKeyboardButton("📤 取出全部", callback_data="bank_with_all")],
        [InlineKeyboardButton("💝 转账给小伙伴", switch_inline_query="gift ")]
    ]
    await reply_with_auto_delete(msg, text, reply_markup=InlineKeyboardMarkup(buttons))
    session.close()


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """存入魔力"""
    msg = update.effective_message
    if not msg:
        return

    user = update.effective_user
    try:
        amount = int(context.args[0]) if context.args else 0
        if amount <= 0:
            raise ValueError
    except:
        await reply_with_auto_delete(msg, "⚠️ <b>魔法咒语念错啦喵！</b>\n示例：<code>/deposit 100</code>")
        return

    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()

    if not u or u.points < amount:
        await reply_with_auto_delete(msg, f"💸 <b>魔力不足喵！</b>\n\n钱包里只有 {u.points if u else 0} MP~")
        session.close()
        return

    u.points -= amount
    u.bank_points += amount
    session.commit()

    await reply_with_auto_delete(
        msg,
        f"📥 <b>存入成功喵~</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 存入：{amount} MP\n"
        f"🏦 当前金库：{u.bank_points} MP"
    )
    session.close()


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取出魔力（自动结算利息）"""
    msg = update.effective_message
    if not msg:
        return

    user = update.effective_user
    try:
        amount = int(context.args[0]) if context.args else 0
        if amount <= 0:
            raise ValueError
    except:
        await reply_with_auto_delete(msg, "⚠️ <b>魔法咒语念错啦喵！</b>\n示例：<code>/withdraw 100</code>")
        return

    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()

    if not u or u.bank_points < amount:
        await reply_with_auto_delete(msg, f"🏦 <b>金库魔力不足喵！</b>\n\n金库里只有 {u.bank_points if u else 0} MP~")
        session.close()
        return

    # 计算并结算利息
    interest = calculate_interest(u)
    accumulated = u.accumulated_interest or 0
    total_interest = interest + accumulated

    # 更新利息结算时间
    u.last_interest_claimed = datetime.now()
    u.accumulated_interest = 0

    fee = 0 if u.is_vip else int(amount * 0.05)
    actual = amount - fee
    u.bank_points -= amount
    u.points += actual + total_interest  # 取款金额 + 利息
    session.commit()

    interest_text = f"\n💰 <b>利息收入：</b> +{total_interest} MP" if total_interest > 0 else ""

    if u.is_vip:
        await reply_with_auto_delete(
            msg,
            f"📤 <b>取款成功喵~</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 取出：{amount} MP\n"
            f"👑 <b>VIP免手续费</b>\n"
            f"{interest_text}"
            f"💵 实际到账：<b>{actual + total_interest} MP</b>"
        )
    else:
        await reply_with_auto_delete(
            msg,
            f"📤 <b>取款成功喵~</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 取出：{amount} MP\n"
            f"💸 手续费：{fee} MP (5%)\n"
            f"{interest_text}"
            f"💵 实际到账：<b>{actual + total_interest} MP</b>"
        )
    session.close()


async def bank_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理银行按钮回调"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user_id).first()

    if not u:
        await query.edit_message_text("💔 <b>请先绑定账号喵！</b>")
        session.close()
        return

    if query.data == "bank_dep_all":
        amount = u.points
        if amount > 0:
            u.points = 0
            u.bank_points += amount
            session.commit()
            await query.edit_message_text(
                f"📥 <b>存入成功喵~</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 已存入：{amount} MP\n"
                f"🏦 当前金库：{u.bank_points} MP"
            )
        else:
            await query.edit_message_text("💸 <b>钱包空空如也喵！</b>")

    elif query.data == "bank_with_all":
        amount = u.bank_points
        if amount <= 0:
            await query.edit_message_text("🏦 <b>金库空空如也喵！</b>")
            session.close()
            return

        # 计算并结算利息
        interest = calculate_interest(u)
        accumulated = u.accumulated_interest or 0
        total_interest = interest + accumulated

        # 更新利息结算时间
        u.last_interest_claimed = datetime.now()
        u.accumulated_interest = 0

        fee = 0 if u.is_vip else int(amount * 0.05)
        actual = amount - fee
        u.bank_points = 0
        u.points += actual + total_interest
        session.commit()

        interest_text = f"\n💰 <b>利息收入：</b> +{total_interest} MP" if total_interest > 0 else ""

        if u.is_vip:
            await query.edit_message_text(
                f"📤 <b>取出成功喵~</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 已取出：{amount} MP\n"
                f"👑 <b>VIP免手续费</b>\n"
                f"{interest_text}"
                f"💵 实际到账：<b>{actual + total_interest} MP</b>"
            )
        else:
            await query.edit_message_text(
                f"📤 <b>取出成功喵~</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 已取出：{amount} MP\n"
                f"💸 手续费：{fee} MP (5%)\n"
                f"{interest_text}"
                f"💵 实际到账：<b>{actual + total_interest} MP</b>"
            )

    session.close()


def register(app):
    app.add_handler(CommandHandler("bank", bank_panel))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CallbackQueryHandler(bank_callback, pattern=r"^bank_"))
