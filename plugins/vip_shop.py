from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete

async def vip_center(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user_id).first()
    is_vip = u.is_vip if u else False
    session.close()

    if is_vip:
        txt = (
            "👑 <b>【 皇 家 · 贵 宾 席 】</b>\n\n"
            "您的尊贵特权正在生效中！\n\n"
            "✅ 4K 极速通道\n"
            "✅ 皇家银行（免手续费）\n"
            "✅ 双倍签到魔力\n\n"
            "<i>\"感谢您的支持，尽情享受吧！(｡•̀ᴗ-)✧\"</i>"
        )
        buttons = [[InlineKeyboardButton("🔄 刷新状态", callback_data="vip")]]
    else:
        txt = (
            "🗝️ <b>【 贵 族 · 晋 升 中 心 】</b>\n\n"
            "升级 VIP 解锁更多特权：\n\n"
            "💠 <b>VIP 专属权益：</b>\n"
            "✨ 4K 极速画质\n"
            "🏦 银行免手续费\n"
            "🍬 双倍签到奖励\n"
            "👑 尊贵身份标识\n\n"
            "<i>\"准备好成为尊贵的VIP了吗？(ง •_•)ง\"</i>"
        )
        buttons = [[InlineKeyboardButton("📝 申请 VIP", callback_data="apply_vip")]]

    await reply_with_auto_delete(update.message, txt, reply_markup=InlineKeyboardMarkup(buttons))

def register(app):
    app.add_handler(CommandHandler("vip", vip_center))
    app.add_handler(CommandHandler("shop", vip_center))
