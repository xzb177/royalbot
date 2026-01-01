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
            "👑 <b>【 皇 家 · 星 辰 殿 堂 · 特 权 展 示 】</b>\n\n"
            "✨ <b>欢迎回来，尊贵的皇家魔法少女大人！</b> ✨\n\n"
            "💠 <b>:: 已 觉 醒 之 力 ::</b>\n\n"
            "🚀 <b>4K 极速通道</b>\n"
            "   └─ 流畅观影，画质飞升~\n\n"
            "🏰 <b>皇家金库特权</b>\n"
            "   └─ 存取/转账 0 手续费\n\n"
            "💰 <b>双倍魔力加成</b>\n"
            "   └─ 每日签到 2x 收益\n\n"
            "⚒️ <b>炼金工坊优惠</b>\n"
            "   └─ 武器锻造 5 折尊享\n\n"
            "🔮 <b>命运眷顾</b>\n"
            "   └─ 塔罗占卜 5 折优惠\n\n"
            "🎁 <b>魔力转赠特权</b>\n"
            "   └─ 转账免手续费（普通 5%）\n\n"
            "📜 <b>悬赏加成</b>\n"
            "   └─ 任务奖励暴击提升\n\n"
            "⚔️ <b>决斗祝福</b>\n"
            "   └─ 挑战时 +8% 胜率加成\n\n"
            "🏆 <b>星辰称号体系</b>\n"
            "   └─ 三段式尊贵头衔\n"
            "   └─ 苍穹·大魔导师·神格\n\n"
            "<i>「感谢您的支持，愿星光永远照耀您的魔法之旅 ~(｡•̀ᴗ-)✧」</i>"
        )
        buttons = [[InlineKeyboardButton("🔄 刷新状态", callback_data="vip")]]
    else:
        txt = (
            "🗝️ <b>【 觉 醒 之 门 · V I P 晋 升 仪 式 】</b>\n\n"
            "✨ <b>准备好觉醒成为真正的皇家魔法少女了吗？</b> ✨\n\n"
            "💠 <b>:: 觉 醒 后 获 得 的 力 量 ::</b>\n\n"
            "🚀 <b>4K 极速通道</b>\n"
            "   └─ 画质飞跃，观影体验升级\n\n"
            "🏰 <b>皇家金库特权</b>\n"
            "   └─ 存取/转账 0 手续费\n\n"
            "💰 <b>双倍魔力加成</b>\n"
            "   └─ 每日签到 2x 收益\n\n"
            "⚒️ <b>炼金工坊优惠</b>\n"
            "   └─ 武器锻造 5 折尊享\n\n"
            "🔮 <b>命运眷顾</b>\n"
            "   └─ 塔罗占卜 5 折优惠\n\n"
            "🎁 <b>魔力转赠特权</b>\n"
            "   └─ 转账免手续费（普通 5%）\n\n"
            "📜 <b>悬赏加成</b>\n"
            "   └─ 任务奖励暴击提升\n\n"
            "⚔️ <b>决斗祝福</b>\n"
            "   └─ 挑战时 +8% 胜率加成\n\n"
            "🏆 <b>星辰称号体系</b>\n"
            "   └─ 三段式尊贵头衔\n"
            "   └─ 苍穹·大魔导师·神格\n\n"
            "<i>「仅需一次证明材料，即可永久觉醒皇家力量喵~(｡･ω･｡)ﾉ♡」</i>"
        )
        buttons = [[InlineKeyboardButton("📝 申请觉醒", callback_data="apply_vip")]]

    await reply_with_auto_delete(update.message, txt, reply_markup=InlineKeyboardMarkup(buttons))

def register(app):
    app.add_handler(CommandHandler("vip", vip_center))
    app.add_handler(CommandHandler("shop", vip_center))
