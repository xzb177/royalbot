from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete

async def bank_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = Session()
    user = session.query(UserBinding).filter_by(tg_id=user_id).first()

    if not user or not user.emby_account:
        session.close()
        await reply_with_auto_delete(update.message, "💔 <b>【 魔 法 契 约 丢 失 】</b>\n请先使用 <code>/bind</code> 缔结契约喵！")
        return

    total = user.points + user.bank_points
    if user.is_vip:
        text = (
            f"🌌 <b>【 皇 家 · 魔 法 少 女 金 库 】</b>\n\n"
            f"🥂 <b>Welcome, my dear Master~</b>\n"
            f"这是为您专属定制的皇家金库，您的魔力结晶在这里绝对安全喵~\n\n"
            f"💎 <b>:: 资 产 总 览 ::</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👑 <b>户主真名：</b> <code>{user.emby_account}</code> (VIP)\n"
            f"🏆 <b>身价估值：</b> <b>{total}</b> MP\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"🏰 <b>:: 皇 家 储 蓄 ::</b>\n"
            f"👛 <b>流动钱包：</b> <code>{user.points}</code> MP\n"
            f"🔐 <b>永恒金库：</b> <b>{user.bank_points}</b> MP\n"
            f"<i>(VIP 特权：存取/转账 <b>0 手续费</b>喵~)</i>\n\n"
            f"💡 <b>:: 资 金 调 度 ::</b>\n"
            f"<i>\"要取一点魔力去买魔法道具吗？还是把战利品存起来？\n无论Master做什么决定，看板娘都支持你哦~(*/ω＼*)\"</i>"
        )
    else:
        text = (
            f"🏰 <b>【 魔 法 学 院 · 储 蓄 柜 台 】</b>\n\n"
            f"✨ <b>你好呀，理财小魔法少女！</b>\n"
            f"把魔力存进金库是好习惯喵~这样就不怕决斗输光光啦！\n\n"
            f"🛡️ <b>:: 账 户 详 情 ::</b>\n"
            f"----------------------------------\n"
            f"👤 <b>户主账号：</b> <code>{user.emby_account}</code>\n"
            f"💰 <b>资产总额：</b> <b>{total}</b> MP\n"
            f"----------------------------------\n\n"
            f"🎒 <b>:: 存 储 状 态 ::</b>\n"
            f"👛 <b>口袋零钱：</b> <code>{user.points}</code> MP\n"
            f"🏦 <b>学院存款：</b> <b>{user.bank_points}</b> MP\n"
            f"<i>(注意：见习魔法少女提现/转账需收 <b>5%</b> 手续费哦!)</i>\n\n"
            f"💡 <b>:: 操 作 指 南 ::</b>\n"
            f"<i>\"想免除手续费吗？觉醒成为 <b>VIP</b> 就可以享受皇家待遇啦！加油喵~！(≧◡≦)\"</i>"
        )

    buttons = [
        [InlineKeyboardButton("📥 存入全部", callback_data="dep_all"), InlineKeyboardButton("📤 取出全部", callback_data="with_all")],
        [InlineKeyboardButton("🎁 转账给小伙伴", switch_inline_query="gift ")]
    ]
    await reply_with_auto_delete(update.message, text, reply_markup=InlineKeyboardMarkup(buttons))
    session.close()

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        amount = int(context.args[0])
        if amount <= 0: raise ValueError
    except:
        await reply_with_auto_delete(update.message, "⚠️ <b>魔法咒语念错啦喵！</b>\n示例：<code>/deposit 100</code>")
        return
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()
    if not u or u.points < amount:
        await reply_with_auto_delete(update.message, f"💸 <b>魔力不足喵！</b>\n钱包里只有 {u.points if u else 0} MP~")
        session.close()
        return
    u.points -= amount
    u.bank_points += amount
    session.commit()
    await reply_with_auto_delete(update.message, f"📥 <b>存入成功喵~</b>\n已存入 {amount} MP，当前金库：{u.bank_points} MP")
    session.close()

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        amount = int(context.args[0])
        if amount <= 0: raise ValueError
    except:
        await reply_with_auto_delete(update.message, "⚠️ <b>魔法咒语念错啦喵！</b>\n示例：<code>/withdraw 100</code>")
        return
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()
    if not u or u.bank_points < amount:
        await reply_with_auto_delete(update.message, f"🏦 <b>金库魔力不足喵！</b>\n金库里只有 {u.bank_points if u else 0} MP~")
        session.close()
        return
    fee = 0 if u.is_vip else int(amount * 0.05)
    actual = amount - fee
    u.bank_points -= amount
    u.points += actual
    session.commit()
    await reply_with_auto_delete(update.message, f"📤 <b>取款成功喵~</b>\n取出：{amount}\n手续费：{fee}\n实际到账：<b>{actual} MP</b>")
    session.close()

def register(app):
    app.add_handler(CommandHandler("bank", bank_panel))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("withdraw", withdraw))
