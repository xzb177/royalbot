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
        await reply_with_auto_delete(update.message, "💔 <b>【 契 约 丢 失 】</b>\n请先使用 <code>/bind</code> 缔结契约！")
        return

    total = user.points + user.bank_points
    if user.is_vip:
        text = (
            f"🌌 <b>【 皇 家 · 星 灵 金 库 】</b>\n\n"
            f"🥂 <b>Welcome, My Lord.</b>\n"
            f"这是为您专属定制的私有金库，哪怕世界毁灭，您的财宝也安然无恙。\n\n"
            f"💎 <b>:: 资 产 总 览 ::</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👑 <b>户主真名：</b> <code>{user.emby_account}</code> (VIP)\n"
            f"🏆 <b>身价估值：</b> <b>{total}</b> MP\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"🏰 <b>:: 皇 家 储 蓄 ::</b>\n"
            f"👛 <b>流动钱包：</b> <code>{user.points}</code> MP\n"
            f"🔐 <b>永恒金库：</b> <b>{user.bank_points}</b> MP\n"
            f"<i>(VIP 特权：存取/转账 <b>0 手续费</b>，即刻到账)</i>\n\n"
            f"💡 <b>:: 资 金 调 度 ::</b>\n"
            f"<i>\"要取一点零花钱去玩吗？还是把战利品存起来？\n无论您做什么决定，看板娘都支持您！(*/ω＼*)\"</i>"
        )
    else:
        text = (
            f"📜 <b>【 冒 险 者 · 储 蓄 公 会 】</b>\n\n"
            f"✨ <b>你好呀，理财小能手！</b>\n"
            f"把魔力存进银行是好习惯哦！这样就不怕决斗输光光啦！\n\n"
            f"🛡️ <b>:: 账 户 详 情 ::</b>\n"
            f"----------------------------------\n"
            f"👤 <b>户主账号：</b> <code>{user.emby_account}</code>\n"
            f"💰 <b>资产总额：</b> <b>{total}</b> MP\n"
            f"----------------------------------\n\n"
            f"🎒 <b>:: 存 储 状 态 ::</b>\n"
            f"👛 <b>口袋零钱：</b> <code>{user.points}</code> MP\n"
            f"🏦 <b>公会存款：</b> <b>{user.bank_points}</b> MP\n"
            f"<i>(注意：普通会员提现/转账需收 <b>5%</b> 磨损费哦!)</i>\n\n"
            f"💡 <b>:: 操 作 指 南 ::</b>\n"
            f"<i>\"想免除手续费吗？努力升级 <b>VIP</b> 就可以享受皇家待遇啦！加油哦！(ง •_•)ง\"</i>"
        )

    buttons = [
        [InlineKeyboardButton("📥 存入全部", callback_data="dep_all"), InlineKeyboardButton("📤 取出全部", callback_data="with_all")],
        [InlineKeyboardButton("🎁 转账给好友", switch_inline_query="gift ")]
    ]
    await reply_with_auto_delete(update.message, text, reply_markup=InlineKeyboardMarkup(buttons))
    session.close()

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        amount = int(context.args[0])
        if amount <= 0: raise ValueError
    except:
        await reply_with_auto_delete(update.message, "⚠️ <b>咒语念错啦！</b>\n示例：<code>/deposit 100</code>")
        return
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()
    if not u or u.points < amount:
        await reply_with_auto_delete(update.message, f"💸 <b>余额不足！</b>\n钱包里只有 {u.points if u else 0} MP。")
        session.close()
        return
    u.points -= amount
    u.bank_points += amount
    session.commit()
    await reply_with_auto_delete(update.message, f"📥 <b>入账成功！</b>\n已存入 {amount} MP，当前金库：{u.bank_points} MP")
    session.close()

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        amount = int(context.args[0])
        if amount <= 0: raise ValueError
    except:
        await reply_with_auto_delete(update.message, "⚠️ <b>咒语念错啦！</b>\n示例：<code>/withdraw 100</code>")
        return
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()
    if not u or u.bank_points < amount:
        await reply_with_auto_delete(update.message, f"🏦 <b>存款不足！</b>\n金库里只有 {u.bank_points if u else 0} MP。")
        session.close()
        return
    fee = 0 if u.is_vip else int(amount * 0.05)
    actual = amount - fee
    u.bank_points -= amount
    u.points += actual
    session.commit()
    await reply_with_auto_delete(update.message, f"📤 <b>取款成功！</b>\n取出：{amount}\n手续费：{fee}\n实际到账：<b>{actual} MP</b>")
    session.close()

def register(app):
    app.add_handler(CommandHandler("bank", bank_panel))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("withdraw", withdraw))
