"""
VIP申请审核模块
用户发送申请材料 -> 转发给管理员审核 -> 管理员批准/拒绝
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from database import Session, UserBinding, VIPApplication
from config import Config
from datetime import datetime
from utils import send_with_auto_delete, reply_with_auto_delete

logger = logging.getLogger(__name__)

# 存储正在申请的用户（临时状态）
pending_applications = {}  # {tg_id: {"step": "waiting_material", "application_id": id}}


async def apply_vip_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始VIP申请流程"""
    user = update.effective_user
    msg = update.effective_message
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()

    if not u or not u.emby_account:
        session.close()
        if msg:
            await reply_with_auto_delete(msg, "💔 <b>请先绑定账号喵！</b>\n使用 <code>/bind 账号</code> 绑定后再申请VIP。")
        return

    if u.is_vip:
        session.close()
        if msg:
            await reply_with_auto_delete(msg, "👑 <b>您已经是皇家魔法少女了喵！</b>\n无需重复申请~")
        return

    # 检查是否有待审核的申请
    existing = session.query(VIPApplication).filter_by(
        tg_id=user.id,
        status='pending'
    ).first()
    if existing:
        # 恢复到内存中，允许用户继续发送材料
        pending_applications[user.id] = {
            "step": "waiting_material",
            "application_id": existing.id
        }
        session.close()
        if msg:
            await reply_with_auto_delete(msg,
                f"⏳ <b>您有待审核的申请喵！</b>\n\n"
                f"请直接发送证明材料，或使用 <code>/cancel</code> 取消申请"
            )
        return

    # 创建申请记录
    app = VIPApplication(
        tg_id=user.id,
        username=f"@{user.username}" if user.username else user.first_name,
        emby_account=u.emby_account,
        status='pending'
    )
    session.add(app)
    session.commit()
    app_id = app.id
    session.close()

    # 设置临时状态
    pending_applications[user.id] = {
        "step": "waiting_material",
        "application_id": app_id
    }

    txt = (
        f"📜 <b>【 V I P · 觉 醒 仪 式 】</b>\n\n"
        f"✨ <b>欢迎申请，{user.first_name}酱！</b>\n"
        f"请发送您的证明材料（截图、图片等）喵~\n\n"
        f"💠 <b>:: 申 请 指 南 ::</b>\n"
        f"1️⃣ 发送支付凭证/会员截图\n"
        f"2️⃣ 等待管理员审核\n"
        f"3️⃣ 审核通过后自动觉醒VIP\n\n"
        f"<i>\"请直接发送图片，看板娘会帮您转交给管理员喵~(｡•̀ᴗ-)✧\"</i>\n\n"
        f"🚫 <b>发送 /cancel 取消申请</b>"
    )
    await update.message.reply_html(txt)


async def handle_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理用户发送的证明材料"""
    user = update.effective_user
    logger.info(f"handle_material 被调用: user_id={user.id}, chat_id={update.effective_chat.id}, type={update.effective_chat.type}")

    # 只处理私聊
    if update.effective_chat.type != 'private':
        return

    session = Session()

    # 检查用户是否在申请流程中（内存中）
    if user.id not in pending_applications:
        # 如果不在内存中，检查数据库中是否有待审核的申请
        app = session.query(VIPApplication).filter_by(
            tg_id=user.id,
            status='pending'
        ).first()
        if app:
            # 恢复到内存中
            pending_applications[user.id] = {
                "step": "waiting_material",
                "application_id": app.id
            }
        else:
            session.close()
            # 没有待审核申请，发送提示
            msg = update.effective_message
            if msg:
                await reply_with_auto_delete(msg, "⚠️ 未找到待审核的申请，请先使用 /applyvip 申请")
            return
    else:
        app_info = pending_applications[user.id]
        app = session.query(VIPApplication).filter_by(id=app_info["application_id"]).first()

    if not app or app.status != 'pending':
        session.close()
        pending_applications.pop(user.id, None)
        msg = update.effective_message
        if msg:
            await reply_with_auto_delete(msg, "⚠️ 申请记录不存在或已失效")
        return

    logger.info(f"处理材料: user={user.id}, app_id={app.id}, owner_id={Config.OWNER_ID}")

    # 转发给管理员
    forwarded = None
    material_info = ""
    error_occurred = False

    try:
        if update.message.photo:
            # 处理图片
            photo = update.message.photo[-1]  # 获取最大尺寸的图片
            caption = update.message.caption or ""

            forwarded_txt = (
                f"📋 <b>【 V I P · 审 核 请 求 】</b>\n\n"
                f"👤 <b>申请人：</b> {app.username}\n"
                f"🆔 <b>用户ID：</b> <code>{app.tg_id}</code>\n"
                f"🔑 <b>Emby账号：</b> <code>{app.emby_account}</code>\n"
                f"📅 <b>申请时间：</b> {app.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"📝 <b>备注：</b> {caption}\n\n"
            )
            forwarded = await context.bot.send_photo(
                chat_id=Config.OWNER_ID,
                photo=photo.file_id,
                caption=forwarded_txt,
                parse_mode='HTML'
            )
            material_info = "图片"

        elif update.message.document:
            # 处理文档
            doc = update.message.document
            caption = update.message.caption or ""

            forwarded_txt = (
                f"📋 <b>【 V I P · 审 核 请 求 】</b>\n\n"
                f"👤 <b>申请人：</b> {app.username}\n"
                f"🆔 <b>用户ID：</b> <code>{app.tg_id}</code>\n"
                f"🔑 <b>Emby账号：</b> <code>{app.emby_account}</code>\n"
                f"📅 <b>申请时间：</b> {app.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"📎 <b>文件名：</b> {doc.file_name}\n"
                f"📝 <b>备注：</b> {caption}\n\n"
            )
            forwarded = await context.bot.send_document(
                chat_id=Config.OWNER_ID,
                document=doc.file_id,
                caption=forwarded_txt,
                parse_mode='HTML'
            )
            material_info = "文档"

        elif update.message.text:
            # 处理纯文本说明
            text = update.message.text
            if text.startswith('/'):
                # 是命令，不处理
                session.close()
                return

            forwarded_txt = (
                f"📋 <b>【 V I P · 审 核 请 求 】</b>\n\n"
                f"👤 <b>申请人：</b> {app.username}\n"
                f"🆔 <b>用户ID：</b> <code>{app.tg_id}</code>\n"
                f"🔑 <b>Emby账号：</b> <code>{app.emby_account}</code>\n"
                f"📅 <b>申请时间：</b> {app.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"💬 <b>说明：</b>\n{text}"
            )
            forwarded = await context.bot.send_message(
                chat_id=Config.OWNER_ID,
                text=forwarded_txt,
                parse_mode='HTML'
            )
            material_info = "文字说明"

    except Exception as e:
        # 转发失败，记录错误并通知用户
        logger.error(f"转发材料给管理员失败: {e}", exc_info=True)
        error_occurred = True
        session.close()
        msg = update.effective_message
        if msg:
            await reply_with_auto_delete(msg,
                f"❌ <b>提交失败</b>\n\n"
                f"材料转发给管理员时出错：{str(e)}\n\n"
                f"请联系管理员检查配置。"
            )
        return

    if forwarded:
        # 保存管理员收到的消息ID
        app.message_id = forwarded.message_id
        session.commit()

        # 发送审核按钮给管理员
        buttons = [
            [
                InlineKeyboardButton("✅ 批准", callback_data=f"vip_approve_{app.id}"),
                InlineKeyboardButton("❌ 拒绝", callback_data=f"vip_reject_{app.id}")
            ]
        ]
        await context.bot.edit_message_reply_markup(
            chat_id=Config.OWNER_ID,
            message_id=forwarded.message_id,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        # 通知用户
        msg = update.effective_message
        if msg:
            await reply_with_auto_delete(msg,
                f"✅ <b>材料已提交喵~</b>\n\n"
                f"您的{material_info}已转交给管理员，请耐心等待审核结果喵~\n\n"
                f"<i>\"审核通过后会通知您哦！(ง •_•)ง\"</i>"
            )

        # 清除临时状态
        pending_applications.pop(user.id, None)
    else:
        # 没有可转发的材料（用户发的是不支持的内容）
        session.close()
        msg = update.effective_message
        if msg:
            await reply_with_auto_delete(msg,
                "⚠️ <b>未识别到有效的证明材料</b>\n\n"
                "请发送图片、文档或文字说明作为证明材料。"
            )
        return

    session.close()


async def cancel_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取消申请"""
    user = update.effective_user
    msg = update.effective_message
    session = Session()

    # 清除内存中的状态
    was_in_flow = user.id in pending_applications
    pending_applications.pop(user.id, None)

    # 删除数据库中所有待审核的申请记录
    deleted = session.query(VIPApplication).filter_by(
        tg_id=user.id,
        status='pending'
    ).delete()
    session.commit()
    session.close()

    if was_in_flow or deleted > 0:
        if msg:
            await reply_with_auto_delete(msg, "🚫 <b>申请已取消</b>")
    else:
        if msg:
            await reply_with_auto_delete(msg, "⚠️ <b>没有进行中的申请</b>")


async def admin_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员审核按钮回调"""
    query = update.callback_query
    user = query.from_user

    # 验证是否是管理员
    if user.id != Config.OWNER_ID:
        await query.answer("❌ 只有管理员可以操作", show_alert=True)
        return

    await query.answer()

    data = query.data
    action, app_id = data.split('_')[1], int(data.split('_')[2])

    session = Session()
    app = session.query(VIPApplication).filter_by(id=app_id).first()

    if not app:
        await query.edit_message_text("❌ 申请记录不存在")
        session.close()
        return

    if action == 'approve':
        # 批准申请 - 给用户开通VIP
        user_binding = session.query(UserBinding).filter_by(tg_id=app.tg_id).first()
        if user_binding:
            user_binding.is_vip = True

        app.status = 'approved'
        app.reviewed_at = datetime.now()
        session.commit()

        result_text = (
            f"✅ <b>已批准</b>\n\n"
            f"用户：{app.username}\n"
            f"Emby：{app.emby_account}\n"
            f"已开通VIP权限"
        )

        # ========== 群组通报：尊贵仪式感 ==========
        if Config.GROUP_ID:  # 群组ID通常是负数(-100...)，用真值判断
            try:
                # 获取用户信息用于显示
                user_display = app.username
                # 简化用户名显示
                if user_display.startswith('@'):
                    user_display = user_display[1:]

                announcement = (
                    f"👑 <b>【 皇 家 加 冕 · 觉 醒 V I P 】</b> 👑\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"✨ <a href=\"tg://user?id={app.tg_id}\">{user_display}</a> <b>正式加入星辰议会</b> ✨\n\n"
                    f"<i>\"荣耀加身，魔法永随 (｡•̀ᴗ-)✧\"</i>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                await send_with_auto_delete(
                    context.bot,
                    Config.GROUP_ID,
                    announcement,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"群组通报发送失败: {e}")
        # ========== 群组通报结束 ==========

        # 尝试用 caption 编辑图片消息，失败则用 text 编辑
        try:
            await query.edit_message_caption(caption=result_text, parse_mode='HTML')
        except Exception:
            try:
                await query.edit_message_text(text=result_text, parse_mode='HTML')
            except Exception:
                # 如果都失败，发送新消息
                await context.bot.send_message(
                    chat_id=Config.OWNER_ID,
                    text=result_text,
                    parse_mode='HTML'
                )

        # 通知用户
        try:
            await context.bot.send_message(
                chat_id=app.tg_id,
                text=(
                    f"🎉 <b>【 V I P · 觉 醒 成 功 ！】</b>\n\n"
                    f"🥂 <b>恭喜 {app.username}酱！</b>\n"
                    f"您的VIP申请已通过审核喵~\n\n"
                    f"💠 <b>:: 皇 家 特 权 激 活 ::</b>\n"
                    f"🚀 4K 极速通道 ─ 已开启\n"
                    f"🏰 皇家金库 ─ 0 手续费\n"
                    f"💰 魔力加成 ─ 签到 1.5x 收益\n"
                    f"⚒️ 炼金工坊 ─ 锻造 5 折\n"
                    f"🔮 命运眷顾 ─ 塔罗 5 折\n"
                    f"🎁 魔力转赠 ─ 免手续费\n"
                    f"📜 悬赏加成 ─ 奖励暴击\n"
                    f"⚔️ 决斗祝福 ─ +5% 胜率\n"
                    f"🏆 星辰称号 ─ 尊贵头衔\n"
                    f"🏦 银行利息 ─ 1% 日息\n"
                    f"🛡️ 连败安慰 ─ 额外奖励\n\n"
                    f"<i>「感谢您的支持，尽情享受魔法少女的生活吧~(｡•̀ᴗ-)✧」</i>"
                ),
                parse_mode='HTML'
            )
        except Exception as e:
            # 通知管理员发送失败，并给出提示
            error_msg = (
                f"✅ <b>已批准，但通知用户失败</b>\n\n"
                f"用户：{app.username} (ID: {app.tg_id})\n"
                f"Emby：{app.emby_account}\n\n"
                f"⚠️ <b>错误原因：</b>\n{str(e)}\n\n"
                f"<i>提示：用户需要先用 /start 启动机器人私聊</i>"
            )
            await context.bot.send_message(
                chat_id=Config.OWNER_ID,
                text=error_msg,
                parse_mode='HTML'
            )

    elif action == 'reject':
        # 拒绝申请
        app.status = 'rejected'
        app.reviewed_at = datetime.now()
        session.commit()

        result_text = (
            f"❌ <b>已拒绝</b>\n\n"
            f"用户：{app.username}\n"
            f"Emby：{app.emby_account}"
        )

        # 尝试用 caption 编辑图片消息，失败则用 text 编辑
        try:
            await query.edit_message_caption(caption=result_text, parse_mode='HTML')
        except Exception:
            try:
                await query.edit_message_text(text=result_text, parse_mode='HTML')
            except Exception:
                # 如果都失败，发送新消息
                await context.bot.send_message(
                    chat_id=Config.OWNER_ID,
                    text=result_text,
                    parse_mode='HTML'
                )

        # 通知用户
        try:
            await context.bot.send_message(
                chat_id=app.tg_id,
                text=(
                    f"💔 <b>【 V I P · 觉 醒 未 通 过 】</b>\n\n"
                    f"很遗憾，您的VIP申请未通过审核喵...\n"
                    f"如有疑问请联系管理员。\n\n"
                    f"<i>\"请检查材料后重新申请吧！加油喵~(ง •_•)ง\"</i>"
                ),
                parse_mode='HTML'
            )
        except Exception as e:
            # 通知管理员发送失败，并给出提示
            error_msg = (
                f"❌ <b>已拒绝，但通知用户失败</b>\n\n"
                f"用户：{app.username} (ID: {app.tg_id})\n"
                f"Emby：{app.emby_account}\n\n"
                f"⚠️ <b>错误原因：</b>\n{str(e)}\n\n"
                f"<i>提示：用户需要先用 /start 启动机器人私聊</i>"
            )
            await context.bot.send_message(
                chat_id=Config.OWNER_ID,
                text=error_msg,
                parse_mode='HTML'
            )

    session.close()


def register(app):
    app.add_handler(CommandHandler("applyvip", apply_vip_start))
    app.add_handler(CommandHandler("cancel", cancel_apply))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_material))
    app.add_handler(CallbackQueryHandler(admin_review_callback, pattern=r"^vip_(approve|reject)_\d+$"))
