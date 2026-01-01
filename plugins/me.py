from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete

async def me_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = Session()
    user = session.query(UserBinding).filter_by(tg_id=user_id).first()

    if not user or not user.emby_account:
        session.close()
        await reply_with_auto_delete(update.message, "👻 <b>幽灵状态警告！</b>\n我看不到您的档案！请先使用 <code>/bind 账号</code> 缔结契约！")
        return

    points = user.points
    win = user.win
    lost = user.lost

    if user.is_vip:
        text = (
            f"🌌 <b>【 星 灵 · 灵 魂 契 约 书 】</b>\n\n"
            f"🥂 <b>Welcome back, My Master.</b>\n"
            f"整个云海的星辰都在为您闪烁！今天也是魔力充盈的一天呢~\n\n"
            f"📜 <b>:: 尊 贵 身 份 识 别 ::</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🤴 <b>契约真名：</b> <code>{user.emby_account}</code>\n"
            f"🆔 <b>灵魂刻印：</b> <code>{user_id}</code>\n"
            f"👑 <b>当前位阶：</b> <b>✨月之大魔导师 (VIP)</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"💎 <b>:: 魔 力 资 产 盘 点 ::</b>\n"
            f"💰 <b>魔力结晶：</b> <b>{points}</b> (您可以尽情挥霍!)\n"
            f"⚔️ <b>命运试炼：</b> 胜 <b>{win}</b> | 败 <b>{lost}</b>\n\n"
            f"📝 <b>:: 看 板 娘 的 备 忘 录 ::</b>\n"
            f"<i>\"已为您开启 4K 极速通道，请尽情享受视觉盛宴吧！(*/ω＼*)\"</i>"
        )
        buttons = [[InlineKeyboardButton("👑 续费 / 充值", callback_data="pay_vip"), InlineKeyboardButton("🎁 兑换中心", callback_data="shop")]]
    else:
        text = (
            f"📜 <b>【 见 习 · 冒 险 者 档 案 】</b>\n\n"
            f"✨ <b>你好呀，勤奋的冒险者！</b>\n"
            f"今天有在好好收集魔力吗？加油变强，向着 VIP 的宝座冲刺吧！\n\n"
            f"🛡️ <b>:: 基 础 信 息 核 对 ::</b>\n"
            f"----------------------------------\n"
            f"👤 <b>契约账号：</b> <code>{user.emby_account}</code>\n"
            f"🆔 <b>身份编号：</b> <code>{user_id}</code>\n"
            f"🌱 <b>当前位阶：</b> 见习魔法师 (普通)\n"
            f"----------------------------------\n\n"
            f"🎒 <b>:: 行 囊 物 资 ::</b>\n"
            f"💎 <b>持有魔力：</b> <b>{points}</b>\n"
            f"⚔️ <b>实战记录：</b> 胜 <b>{win}</b> | 败 <b>{lost}</b>\n\n"
            f"💡 <b>:: 进 阶 指 南 ::</b>\n"
            f"<i>想要解锁 <b>4K 极速通道</b> 和 <b>双倍奖励</b> 吗？\n快去点亮属于你的 VIP 勋章吧！(ง •_•)ง</i>"
        )
        buttons = [[InlineKeyboardButton("✨ 升级 VIP", callback_data="buy_vip"), InlineKeyboardButton("🍬 每日签到", callback_data="checkin")]]

    await reply_with_auto_delete(update.message, text, reply_markup=InlineKeyboardMarkup(buttons))
    session.close()

def register(app):
    app.add_handler(CommandHandler("me", me_panel))
    app.add_handler(CommandHandler("my", me_panel))
