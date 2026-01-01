from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete

async def my_bag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user_id).first()
    points = u.points if u else 0
    session.close()

    txt = f"🎒 <b>【 魔 法 少 女 的 背 包 】</b>\n💎 <b>魔力结晶：</b> {points} MP\n📦 <b>魔法道具：</b> 暂无喵~\n\n<i>\"包包空空的...去魔法商店看看吧？(｡･ω･｡)\"</i>"
    await reply_with_auto_delete(update.message, txt)

def register(app):
    app.add_handler(CommandHandler("bag", my_bag))
