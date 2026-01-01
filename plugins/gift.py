"""
魔力转赠系统 - 魔法少女版
- 用户间互相转赠 MP
- VIP 免手续费，普通用户 5%
- 支持回复和 @ 两种方式
"""
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete

# 转账手续费率（非 VIP）
GIFT_FEE_RATE = 0.05


async def track_activity_wrapper(user_id: int, activity_type: str):
    """包装函数，延迟导入避免循环依赖"""
    from plugins.mission import track_activity
    await track_activity(user_id, activity_type)


async def gift_mp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """魔力转赠功能"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    session = Session()
    sender = session.query(UserBinding).filter_by(tg_id=user_id).first()

    if not sender or not sender.emby_account:
        session.close()
        await reply_with_auto_delete(msg, "💔 <b>【 魔 法 契 约 丢 失 】</b>\n请先使用 <code>/bind</code> 缔结魔法契约喵！")
        return

    # 解析参数
    target_user = None
    amount = 0

    # 方法1：回复某人并输入 /gift 数量
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
        if context.args:
            try:
                amount = int(context.args[0])
                if amount <= 0:
                    raise ValueError
            except ValueError:
                await reply_with_auto_delete(msg, "⚠️ <b>魔力数值无效喵！</b>\n请输入正整数，如：<code>/gift 100</code>")
                session.close()
                return
    # 方法2：直接 /gift @username 数量
    elif len(context.args) >= 2:
        username_input = context.args[0]
        if username_input.startswith("@"):
            username_input = username_input[1:]
        try:
            amount = int(context.args[1])
            if amount <= 0:
                raise ValueError
        except ValueError:
            await reply_with_auto_delete(msg, "⚠️ <b>魔力数值无效喵！</b>\n请输入正整数，如：<code>/gift @username 100</code>")
            session.close()
            return

        # 查找目标用户（先尝试 username 匹配）
        all_users = session.query(UserBinding).filter(UserBinding.emby_account != None).all()

        for u in all_users:
            try:
                chat_member = await context.bot.get_chat_member(update.effective_chat.id, u.tg_id)
                if chat_member.user.username and chat_member.user.username.lower() == username_input.lower():
                    target_user = chat_member.user
                    break
            except:
                continue

        if not target_user:
            await reply_with_auto_delete(
                msg,
                f"🔍 <b>【 找 不 到 目 标 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"无法找到用户 <b>@{username_input}</b>\n\n"
                f"<i>\"请确保对方也在本群并已绑定账号喵~(｡•́︿•̀｡)\"</i>"
            )
            session.close()
            return
    else:
        session.close()
        await reply_with_auto_delete(
            msg,
            f"💝 <b>【 魔 力 转 赠 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>用法1：</b> 回复某人 <code>/gift 数量</code>\n"
            f"<b>用法2：</b> <code>/gift @username 数量</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>💡 见习魔法少女转赠需扣除 {int(GIFT_FEE_RATE*100)}% 手续费，VIP 免费喵~</i>"
        )
        return

    # 检查是否转给自己
    if target_user.id == user_id:
        session.close()
        await reply_with_auto_delete(
            msg,
            f"🚫 <b>【 不 能 转 给 自 己 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>\"想变富还是去签到吧喵！(｡•̀ᴗ-)✧\"</i>"
        )
        return

    # 检查余额
    if sender.points < amount:
        session.close()
        await reply_with_auto_delete(
            msg,
            f"💸 <b>【 魔 力 不 足 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"钱包里只有 <b>{sender.points} MP</b>\n"
            f"无法转赠 <b>{amount} MP</b> 喵~"
        )
        return

    # 计算手续费
    fee = 0 if sender.is_vip else int(amount * GIFT_FEE_RATE)
    actual_received = amount - fee

    # 查找接收者
    receiver = session.query(UserBinding).filter_by(tg_id=target_user.id).first()

    if not receiver or not receiver.emby_account:
        session.close()
        await reply_with_auto_delete(
            msg,
            f"💔 <b>【 对 方 未 契 约 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{target_user.first_name} 还没有绑定账号\n"
            f"无法接收魔力转赠喵~"
        )
        return

    # 执行转账
    sender.points -= amount
    receiver.points += actual_received
    await track_activity_wrapper(user_id, "gift")
    session.commit()

    # 构建成功消息
    target_name = target_user.first_name or target_user.username or receiver.emby_account
    if sender.is_vip:
        text = (
            f"💝 <b>【 魔 力 转 赠 成 功 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎁 <b>转赠对象：</b> {target_name}\n"
            f"💎 <b>转赠数量：</b> {amount} MP\n"
            f"👑 <b>VIP 特权：</b> 免手续费\n"
            f"✅ <b>对方到账：</b> <b>{actual_received} MP</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>\"您的慷慨将温暖小伙伴的心喵~(*/ω＼*)\"</i>"
        )
    else:
        text = (
            f"💝 <b>【 魔 力 转 赠 成 功 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎁 <b>转赠对象：</b> {target_name}\n"
            f"💎 <b>转赠数量：</b> {amount} MP\n"
            f"📉 <b>手续费：</b> {fee} MP ({int(GIFT_FEE_RATE*100)}%)\n"
            f"✅ <b>对方到账：</b> <b>{actual_received} MP</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>💡 VIP 可免手续费哦~</i>"
        )

    # 同时通知接收者（如果能获取到）
    try:
        await context.bot.send_message(
            chat_id=target_user.id,
            text=f"🎉 <b>【 收 到 魔 力 转 赠 】</b>\n\n{sender.emby_account} 向您转赠了 <b>{actual_received} MP</b>！",
            parse_mode='HTML'
        )
    except:
        pass  # 接收者可能没有私聊机器人

    await reply_with_auto_delete(msg, text)
    session.close()


def register(app):
    app.add_handler(CommandHandler("gift", gift_mp))
