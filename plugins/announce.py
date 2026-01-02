"""
群组公告插件
管理员可向群组发送公告通知
"""
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from config import Config
from utils import reply_with_auto_delete, send_with_auto_delete


async def cmd_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发送群组公告（仅管理员）"""
    msg = update.effective_message
    user_id = msg.from_user.id

    # 检查是否为管理员
    if user_id != Config.OWNER_ID:
        await reply_with_auto_delete(msg, "⛔ <b>权限不足</b>\n此命令仅限管理员使用喵~")
        return

    # 检查群组配置
    if not Config.GROUP_ID:
        await reply_with_auto_delete(msg, "⚠️ <b>配置错误</b>\n未设置群组 ID (GROUP_ID)")
        return

    # 获取公告内容
    if not context.args:
        await reply_with_auto_delete(
            msg,
            "📢 <b>【 群组公告帮助 】</b>\n\n"
            "用法：<code>/announce 公告内容</code>\n\n"
            "示例：\n"
            "<code>/announce 今晚8点维护~</code>\n\n"
            "<i>公告会发送到配置的群组喵~</i>"
        )
        return

    content = ' '.join(context.args)

    announcement = (
        f"📢 <b>【 系 统 公 告 】</b> 📢\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{content}\n\n"
        f"<i>\"魔法永恒，初心不改 (｡•̀ᴗ-)✧\"</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    try:
        await send_with_auto_delete(
            context.bot,
            Config.GROUP_ID,
            announcement,
            parse_mode='HTML'
        )
        await reply_with_auto_delete(msg, "✅ <b>公告已发送</b>\n群组成员将在 30 秒后看到通知喵~")
    except Exception as e:
        await reply_with_auto_delete(msg, f"❌ <b>发送失败</b>\n错误: {str(e)}")


def register(app):
    """注册命令处理器"""
    app.add_handler(CommandHandler("announce", cmd_announce))
