from telegram import Update, BotCommand, BotCommandScopeChat, BotCommandScopeDefault, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from config import Config
from utils import reply_with_auto_delete
from database import Session, UserBinding, VIPApplication

MY_ADMIN_ID = Config.OWNER_ID  # 从配置加载管理员ID

PUBLIC_COMMANDS = [
    ("start", "✨ 唤醒看板娘"),
    ("menu", "💠 展开魔法阵"),
    ("me", "📜 冒险者档案"),
    ("daily", "🍬 每日补给"),
    ("bind", "🔗 缔结契约"),
    ("vip", "👑 贵族中心"),
    ("bank", "🏦 皇家银行"),
    ("bag", "🎒 次源背包"),
    ("forge", "⚒️ 灵装炼金"),
    ("myweapon", "⚔️ 我的装备"),
    ("mission", "📜 悬赏公会"),
    ("duel", "⚔️ 魔法决斗"),
    ("poster", "🎰 命运盲盒"),
    ("tarot", "🔮 塔罗占卜"),
    ("shop", "🎁 魔法商店"),
    ("gift", "💝 魔力转赠"),
    ("hall", "🏆 荣耀殿堂"),
    ("libs", "🎬 视界观测"),
    ("help", "📖 魔法指南")
]

ADMIN_COMMANDS = [
    ("admin", "🛡️ 控制台"), ("say", "🗣️ 全员广播"),
    ("sync", "🔄 刷新菜单配置")
]

async def sync_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ADMIN_ID:
        return
    bot = context.bot
    await bot.set_my_commands(commands=[BotCommand(c, d) for c, d in PUBLIC_COMMANDS], scope=BotCommandScopeDefault())
    full_cmds = PUBLIC_COMMANDS + ADMIN_COMMANDS
    await bot.set_my_commands(commands=[BotCommand(c, d) for c, d in full_cmds], scope=BotCommandScopeChat(chat_id=MY_ADMIN_ID))
    await reply_with_auto_delete(update.message, "✅ <b>管理员隐形菜单已激活！</b>")


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员控制台主面板"""
    if update.effective_user.id != MY_ADMIN_ID:
        await reply_with_auto_delete(update.message, "⛔ <b>权限不足</b>\n此命令仅限管理员使用。")
        return

    session = Session()

    # 统计数据
    total_users = session.query(UserBinding).count()
    vip_users = session.query(UserBinding).filter_by(is_vip=True).count()
    total_points = session.query(UserBinding).count()
    pending_apps = session.query(VIPApplication).filter_by(status='pending').count()

    # 计算总流通积分
    users = session.query(UserBinding).all()
    wallet_points = sum(u.points for u in users)
    bank_points = sum(u.bank_points for u in users)
    total_points = wallet_points + bank_points

    text = (
        f"🛡️ <b>【 管理员控制台 】</b>\n\n"
        f"📊 <b>:: 数据统计 ::</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>总用户数：</b> {total_users}\n"
        f"👑 <b>VIP 用户：</b> {vip_users}\n"
        f"📋 <b>待审核申请：</b> {pending_apps}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>:: 积分流通 ::</b>\n"
        f"👛 <b>钱包总额：</b> {wallet_points} MP\n"
        f"🏦 <b>金库总额：</b> {bank_points} MP\n"
        f"💎 <b>总流通量：</b> <b>{total_points}</b> MP\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

    buttons = [
        [InlineKeyboardButton("👤 查询用户", callback_data="admin_query")],
        [InlineKeyboardButton("💰 积分管理", callback_data="admin_points")],
        [InlineKeyboardButton("👑 VIP 管理", callback_data="admin_vip")],
        [InlineKeyboardButton("📋 VIP 申请列表", callback_data="admin_apps")],
        [InlineKeyboardButton("🗣️ 全员广播", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔄 刷新菜单", callback_data="admin_sync")],
    ]

    session.close()
    await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(buttons))


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理管理面板回调"""
    query = update.callback_query
    if query.from_user.id != MY_ADMIN_ID:
        await query.answer("⛔ 权限不足", show_alert=True)
        return

    await query.answer()

    data = query.data
    session = Session()

    if data == "admin_sync":
        # 刷新命令菜单
        bot = context.bot
        await bot.set_my_commands(commands=[BotCommand(c, d) for c, d in PUBLIC_COMMANDS], scope=BotCommandScopeDefault())
        full_cmds = PUBLIC_COMMANDS + ADMIN_COMMANDS
        await bot.set_my_commands(commands=[BotCommand(c, d) for c, d in full_cmds], scope=BotCommandScopeChat(chat_id=MY_ADMIN_ID))
        await query.edit_message_text("✅ <b>菜单已刷新！</b>", parse_mode='HTML')
        await query.message.reply_html(
            f"🛡️ <b>【 管理员控制台 】</b>\n\n✅ 菜单刷新成功！",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 返回", callback_data="admin_back")]])
        )

    elif data == "admin_back":
        # 返回主面板
        total_users = session.query(UserBinding).count()
        vip_users = session.query(UserBinding).filter_by(is_vip=True).count()
        pending_apps = session.query(VIPApplication).filter_by(status='pending').count()
        users = session.query(UserBinding).all()
        wallet_points = sum(u.points for u in users)
        bank_points = sum(u.bank_points for u in users)

        text = (
            f"🛡️ <b>【 管理员控制台 】</b>\n\n"
            f"📊 <b>:: 数据统计 ::</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👥 <b>总用户数：</b> {total_users}\n"
            f"👑 <b>VIP 用户：</b> {vip_users}\n"
            f"📋 <b>待审核申请：</b> {pending_apps}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>:: 积分流通 ::</b>\n"
            f"👛 <b>钱包总额：</b> {wallet_points} MP\n"
            f"🏦 <b>金库总额：</b> {bank_points} MP\n"
            f"💎 <b>总流通量：</b> <b>{wallet_points + bank_points}</b> MP\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        buttons = [
            [InlineKeyboardButton("👤 查询用户", callback_data="admin_query")],
            [InlineKeyboardButton("💰 积分管理", callback_data="admin_points")],
            [InlineKeyboardButton("👑 VIP 管理", callback_data="admin_vip")],
            [InlineKeyboardButton("📋 VIP 申请列表", callback_data="admin_apps")],
            [InlineKeyboardButton("🗣️ 全员广播", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔄 刷新菜单", callback_data="admin_sync")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')

    elif data == "admin_query":
        await query.edit_message_text(
            "🔍 <b>【 用户查询 】</b>\n\n"
            "请输入用户操作指令：\n"
            "<code>/query &lt;用户ID或用户名&gt;</code>\n\n"
            "示例：\n"
            "<code>/query 123456789</code>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 返回", callback_data="admin_back")]])
        )

    elif data == "admin_points":
        await query.edit_message_text(
            "💰 <b>【 积分管理 】</b>\n\n"
            "请输入积分操作指令：\n"
            "<code>/addpoints &lt;用户ID&gt; &lt;数量&gt;</code> - 添加积分\n"
            "<code>/delpoints &lt;用户ID&gt; &lt;数量&gt;</code> - 扣除积分\n\n"
            "示例：\n"
            "<code>/addpoints 123456789 1000</code>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 返回", callback_data="admin_back")]])
        )

    elif data == "admin_vip":
        await query.edit_message_text(
            "👑 <b>【 VIP 管理 】</b>\n\n"
            "请输入 VIP 操作指令：\n"
            "<code>/setvip &lt;用户ID&gt;</code> - 设置为 VIP\n"
            "<code>/unvip &lt;用户ID&gt;</code> - 取消 VIP\n\n"
            "示例：\n"
            "<code>/setvip 123456789</code>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 返回", callback_data="admin_back")]])
        )

    elif data == "admin_apps":
        pending = session.query(VIPApplication).filter_by(status='pending').all()
        if not pending:
            text = "📋 <b>【 VIP 申请列表 】</b>\n\n✨ 暂无待审核申请"
        else:
            text = f"📋 <b>【 VIP 申请列表 】</b>\n\n共有 {len(pending)} 条待审核申请：\n\n"
            for app in pending[:10]:  # 最多显示10条
                user = session.query(UserBinding).filter_by(tg_id=app.tg_id).first()
                text += f"📌 <code>{app.tg_id}</code> - {app.username or '未知'}\n"
                text += f"   Emby: {app.emby_account}\n"
                text += f"   状态: {app.status}\n\n"
            if len(pending) > 10:
                text += f"... 还有 {len(pending) - 10} 条申请"

        buttons = [[InlineKeyboardButton("🔙 返回", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')

    elif data == "admin_broadcast":
        await query.edit_message_text(
            "🗣️ <b>【 全员广播 】</b>\n\n"
            "请使用以下命令发送广播：\n"
            "<code>/say &lt;消息内容&gt;</code>\n\n"
            "示例：\n"
            "<code>/say 系统维护通知...</code>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 返回", callback_data="admin_back")]])
        )

    session.close()


async def cmd_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查询用户信息"""
    if update.effective_user.id != MY_ADMIN_ID:
        return

    if not context.args:
        await reply_with_auto_delete(update.message, "⚠️ <b>用法错误</b>\n<code>/query &lt;用户ID&gt;</code>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await reply_with_auto_delete(update.message, "⚠️ <b>用户ID必须是数字</b>")
        return

    session = Session()
    user = session.query(UserBinding).filter_by(tg_id=target_id).first()

    if not user:
        await reply_with_auto_delete(update.message, f"❌ 用户 <code>{target_id}</code> 不存在")
    else:
        text = (
            f"👤 <b>【 用户信息 】</b>\n\n"
            f"🆔 <b>Telegram ID：</b> <code>{user.tg_id}</code>\n"
            f"🎬 <b>Emby 账号：</b> <code>{user.emby_account or '未绑定'}</code>\n"
            f"👑 <b>VIP 状态：</b> {'✅ 是' if user.is_vip else '❌ 否'}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>积分信息：</b>\n"
            f"👛 <b>钱包：</b> {user.points} MP\n"
            f"🏦 <b>金库：</b> {user.bank_points} MP\n"
            f"💎 <b>总资产：</b> {user.points + user.bank_points} MP\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚔️ <b>战斗记录：</b> {user.win}胜 / {user.lost}负\n"
            f"🗡️ <b>当前装备：</b> {user.weapon or '无'}\n"
            f"⚡ <b>战力数值：</b> {user.attack}"
        )
        await reply_with_auto_delete(update.message, text)

    session.close()


async def cmd_addpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """给用户添加积分"""
    if update.effective_user.id != MY_ADMIN_ID:
        return

    if len(context.args) < 2:
        await reply_with_auto_delete(update.message, "⚠️ <b>用法错误</b>\n<code>/addpoints &lt;用户ID&gt; &lt;数量&gt;</code>")
        return

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await reply_with_auto_delete(update.message, "⚠️ <b>参数错误</b>\n用户ID和数量必须是数字")
        return

    session = Session()
    user = session.query(UserBinding).filter_by(tg_id=target_id).first()

    if not user:
        await reply_with_auto_delete(update.message, f"❌ 用户 <code>{target_id}</code> 不存在")
    else:
        user.points += amount
        session.commit()
        await reply_with_auto_delete(update.message, f"✅ <b>操作成功</b>\n已给用户 <code>{target_id}</code> 添加 <b>{amount}</b> MP")

    session.close()


async def cmd_delpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """扣除用户积分"""
    if update.effective_user.id != MY_ADMIN_ID:
        return

    if len(context.args) < 2:
        await reply_with_auto_delete(update.message, "⚠️ <b>用法错误</b>\n<code>/delpoints &lt;用户ID&gt; &lt;数量&gt;</code>")
        return

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await reply_with_auto_delete(update.message, "⚠️ <b>参数错误</b>\n用户ID和数量必须是数字")
        return

    session = Session()
    user = session.query(UserBinding).filter_by(tg_id=target_id).first()

    if not user:
        await reply_with_auto_delete(update.message, f"❌ 用户 <code>{target_id}</code> 不存在")
    else:
        user.points = max(0, user.points - amount)
        session.commit()
        await reply_with_auto_delete(update.message, f"✅ <b>操作成功</b>\n已扣除用户 <code>{target_id}</code> 的 <b>{amount}</b> MP")

    session.close()


async def cmd_setvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置用户为VIP"""
    if update.effective_user.id != MY_ADMIN_ID:
        return

    if not context.args:
        await reply_with_auto_delete(update.message, "⚠️ <b>用法错误</b>\n<code>/setvip &lt;用户ID&gt;</code>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await reply_with_auto_delete(update.message, "⚠️ <b>用户ID必须是数字</b>")
        return

    session = Session()
    user = session.query(UserBinding).filter_by(tg_id=target_id).first()

    if not user:
        await reply_with_auto_delete(update.message, f"❌ 用户 <code>{target_id}</code> 不存在")
    else:
        user.is_vip = True
        session.commit()
        await reply_with_auto_delete(update.message, f"👑 <b>操作成功</b>\n用户 <code>{target_id}</code> 已设置为 VIP")

    session.close()


async def cmd_unvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取消用户VIP"""
    if update.effective_user.id != MY_ADMIN_ID:
        return

    if not context.args:
        await reply_with_auto_delete(update.message, "⚠️ <b>用法错误</b>\n<code>/unvip &lt;用户ID&gt;</code>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await reply_with_auto_delete(update.message, "⚠️ <b>用户ID必须是数字</b>")
        return

    session = Session()
    user = session.query(UserBinding).filter_by(tg_id=target_id).first()

    if not user:
        await reply_with_auto_delete(update.message, f"❌ 用户 <code>{target_id}</code> 不存在")
    else:
        user.is_vip = False
        session.commit()
        await reply_with_auto_delete(update.message, f"👑 <b>操作成功</b>\n用户 <code>{target_id}</code> 已取消 VIP")

    session.close()


async def cmd_say(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发送全员广播"""
    if update.effective_user.id != MY_ADMIN_ID:
        return

    if not context.args:
        await reply_with_auto_delete(update.message, "⚠️ <b>用法错误</b>\n<code>/say &lt;消息内容&gt;</code>")
        return

    message = " ".join(context.args)
    session = Session()
    users = session.query(UserBinding).all()
    success = 0
    failed = 0

    for user in users:
        try:
            await context.bot.send_message(chat_id=user.tg_id, text=f"🗣️ <b>【 管理员广播 】</b>\n\n{message}", parse_mode='HTML')
            success += 1
        except Exception:
            failed += 1

    session.close()
    await reply_with_auto_delete(update.message, f"✅ <b>广播发送完成</b>\n成功：{success}\n失败：{failed}")


def register(app):
    app.add_handler(CommandHandler("sync", sync_commands))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("query", cmd_query))
    app.add_handler(CommandHandler("addpoints", cmd_addpoints))
    app.add_handler(CommandHandler("delpoints", cmd_delpoints))
    app.add_handler(CommandHandler("setvip", cmd_setvip))
    app.add_handler(CommandHandler("unvip", cmd_unvip))
    app.add_handler(CommandHandler("say", cmd_say))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
