"""
MP红包系统
- 发送红包：/redpacket 或 /hongbao 金额 数量
- 抢红包：点击红包按钮
- VIP权益：更高红包上限
"""
import random
import json
import logging
import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding, RedPacket
from utils import reply_with_auto_delete

logger = logging.getLogger(__name__)


# 红包配置
MAX_PACKET_NORMAL = 1000      # 普通用户单次最大金额
MAX_PACKET_VIP = 5000         # VIP单次最大金额
MIN_PACKET_AMOUNT = 10        # 最小红包金额
MIN_PACKET_COUNT = 1          # 最小红包个数
MAX_PACKET_COUNT = 100        # 最大红包个数


def generate_greeting():
    """随机祝福语"""
    greetings = [
        "恭喜发财，大吉大利",
        "魔力满满，快乐加倍",
        "愿你今天欧气爆棚",
        "来迟了就没有啦~",
        "手快有手慢无哦",
        "一点点心意，请笑纳",
        "祝Master今天也很幸运",
        "看板娘的小礼物~",
    ]
    return random.choice(greetings)


async def send_redpacket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发送红包命令"""
    msg = update.effective_message
    if not msg or not msg.chat:
        return

    # 只在群组中可用
    if msg.chat.type == 'private':
        await reply_with_auto_delete(
            msg,
            "💔 <b>红包只能在群组中发送喵！</b>"
        )
        return

    user_id = update.effective_user.id

    # 检查参数
    if not context.args:
        await reply_with_auto_delete(
            msg,
            "🧧 <b>【 M P 红 包 】</b>\n\n"
            "用法: <code>/redpacket 金额</code> (默认10个)\n"
            "或: <code>/redpacket 金额 数量</code>\n\n"
            f"• 普通用户: 单次最多 {MAX_PACKET_NORMAL} MP\n"
            f"• VIP用户: 单次最多 {MAX_PACKET_VIP} MP\n\n"
            "<i>\"发红包交朋友喵~(｡•̀ᴗ-)✧\"</i>"
        )
        return

    # 解析金额
    try:
        amount = int(context.args[0])
        # 如果没有指定数量，默认10个
        count = int(context.args[1]) if len(context.args) > 1 else 10
    except ValueError:
        await reply_with_auto_delete(
            msg,
            "💔 <b>参数格式错误喵！</b>\n\n"
            "请使用: <code>/redpacket 金额</code>\n"
            "例如: <code>/redpacket 100</code> (发100MP分10个红包)"
        )
        return

    # 先获取用户信息（一次性获取所有需要的数据）
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user or not user.emby_account:
            await reply_with_auto_delete(
                msg,
                "💔 <b>请先缔结魔法契约喵！</b>\n\n"
                "使用 <code>/bind 账号</code> 绑定后再来~"
            )
            return

        # 检查余额
        if user.points < amount:
            await reply_with_auto_delete(
                msg,
                f"💸 <b>魔力不足喵！</b>\n\n"
                f"你的余额: {user.points} MP\n"
                f"红包金额: {amount} MP"
            )
            return

        # 检查金额限制
        is_vip = user.is_vip
        max_amount = MAX_PACKET_VIP if is_vip else MAX_PACKET_NORMAL

        if amount > max_amount:
            await reply_with_auto_delete(
                msg,
                f"💔 <b>红包金额超限喵！</b>\n\n"
                f"{'VIP' if is_vip else '普通用户'}单次最多 {max_amount} MP"
            )
            return

        if amount < MIN_PACKET_AMOUNT:
            await reply_with_auto_delete(
                msg,
                f"💔 <b>红包金额太小啦喵！</b>\n\n"
                f"最少 {MIN_PACKET_AMOUNT} MP"
            )
            return

        if count < MIN_PACKET_COUNT or count > MAX_PACKET_COUNT:
            await reply_with_auto_delete(
                msg,
                f"💔 <b>红包数量超出范围喵！</b>\n\n"
                f"数量范围: {MIN_PACKET_COUNT}-{MAX_PACKET_COUNT} 个"
            )
            return

        if amount < count:
            await reply_with_auto_delete(
                msg,
                f"💔 <b>每个红包至少1MP喵！</b>\n\n"
                f"金额({amount}) < 数量({count})"
            )
            return

        # 扣除金额
        user.points -= amount
        user.total_spent = (user.total_spent or 0) + amount
        session.commit()

    # 保存VIP状态供后面使用
    sender_is_vip = is_vip

    # 创建红包
    packet_id = str(uuid.uuid4())[:8]
    greeting = generate_greeting()

    with get_session() as session:
        packet = RedPacket(
            id=packet_id,
            sender_id=user_id,
            chat_id=msg.chat_id,
            message_id=0,  # 稍后更新
            total_amount=amount,
            total_count=count,
            remaining_amount=amount,
            remaining_count=count,
            packet_type='random',
            greeting=greeting,
            claimed_by=""
        )
        session.add(packet)
        session.commit()

    # 发送红包消息
    sender_name = update.effective_user.first_name or "神秘人"
    sender_title = "VIP" if sender_is_vip else "Master"

    text = (
        f"🧧 <b>【 M P 红 包 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✨ {sender_title} <b>{sender_name}</b> 发了一个红包！\n"
        f"💰 <b>金额：</b>{amount} MP\n"
        f"🎯 <b>数量：</b>{count} 个\n\n"
        f"💌 <i>\"{greeting}\"</i>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>手快有手慢无，点击开抢喵~</i>"
    )

    keyboard = [[InlineKeyboardButton(f"🧧 开红包 ({count})", callback_data=f"rp_open_{packet_id}")]]

    sent_msg = await msg.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

    # 更新红包的message_id
    with get_session() as session:
        packet = session.query(RedPacket).filter_by(id=packet_id).first()
        if packet:
            packet.message_id = sent_msg.message_id
            session.commit()

    logger.info(f"[红包] 用户{user_id}发送红包: {amount}MPx{count}, ID={packet_id}")


async def open_redpacket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """抢红包回调"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    packet_id = query.data.replace("rp_open_", "")

    with get_session() as session:
        packet = session.query(RedPacket).filter_by(id=packet_id).first()

        if not packet:
            await query.edit_message_text(
                "💔 <b>红包不存在或已过期</b>",
                parse_mode='HTML'
            )
            return

        # 检查是否是发送者
        if packet.sender_id == user_id:
            # 发送者查看自己的红包，保留按钮
            keyboard = [[InlineKeyboardButton(f"🧧 开红包 ({packet.remaining_count})", callback_data=f"rp_open_{packet_id}")]] if packet.remaining_count > 0 else []
            await query.edit_message_text(
                f"🧧 <b>【 M P 红 包 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>总金额：</b>{packet.total_amount} MP\n"
                f"🎯 <b>总数量：</b>{packet.total_count} 个\n"
                f"📊 <b>已抢：</b>{packet.total_count - packet.remaining_count}/{packet.total_count}\n\n"
                f"<i>\"不能抢自己的红包喵~\"</i>",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )
            return

        # 检查红包是否已抢完
        if packet.remaining_count <= 0:
            # 显示已抢完的红包
            claimed_by = json.loads(packet.claimed_by) if packet.claimed_by else {}
            claimed_list = []
            for uid, amt in list(claimed_by.items())[:5]:  # 只显示前5个
                claimed_list.append(f"✨ 用户{uid[-4:]}: +{amt} MP")

            await query.edit_message_text(
                f"🧧 <b>【 红包已抢完 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>总金额：</b>{packet.total_amount} MP\n"
                f"🎯 <b>数量：</b>{packet.total_count} 个\n\n"
                f"<b>领取记录：</b>\n"
                + "\n".join(claimed_list) +
                (f"\n... 还有 {len(claimed_by) - 5} 人" if len(claimed_by) > 5 else ""),
                parse_mode='HTML'
            )
            return

        # 检查是否已经抢过
        claimed_by = json.loads(packet.claimed_by) if packet.claimed_by else {}
        if str(user_id) in claimed_by:
            already_got = claimed_by[str(user_id)]
            # 已抢过，使用 alert 提示而不是修改消息
            await query.answer(
                f"💰 你已抢过此红包，获得 +{already_got} MP\n每个红包只能抢一次喵~",
                show_alert=True
            )
            return

        # 检查用户是否存在
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user:
            # 未绑定用户，使用 alert 提示
            await query.answer(
                "💔 请先缔结魔法契约才能抢红包喵！\n使用 /bind 账号 绑定后再来~",
                show_alert=True
            )
            return

        # 计算抢到的金额
        if packet.remaining_count == 1:
            # 最后一个红包，获得剩余全部金额
            got_amount = packet.remaining_amount
        else:
            # 随机金额：确保每个红包至少1MP
            max_get = packet.remaining_amount - packet.remaining_count + 1
            if max_get <= 1:
                got_amount = 1
            else:
                got_amount = random.randint(1, max_get)

        # 更新红包
        packet.remaining_amount -= got_amount
        packet.remaining_count -= 1
        claimed_by[str(user_id)] = got_amount
        packet.claimed_by = json.dumps(claimed_by)

        # 给用户加钱
        user.points += got_amount
        user.total_earned = (user.total_earned or 0) + got_amount

        session.commit()

        # 获取发送者信息
        sender = session.query(UserBinding).filter_by(tg_id=packet.sender_id).first()

        # 生成结果文本
        if got_amount >= packet.total_amount // 3:
            effect = "💫💫💫 <b>运气爆棚！</b> 💫💫💫"
        elif got_amount >= packet.total_amount // 5:
            effect = "✨ <b>手气不错！</b> ✨"
        else:
            effect = "💰 <b>抢到红包啦！</b> 💰"

        # 判断是否是运气最佳
        all_amounts = list(claimed_by.values())
        is_best = got_amount == max(all_amounts) and len(all_amounts) > 1

        best_tag = "\n🌟 <b>运气最佳！</b> 🌟" if is_best else ""

        result_text = (
            f"🧧 <b>【 抢 到 红 包 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{effect}\n\n"
            f"💰 <b>获得：</b>+{got_amount} MP\n"
            f"🎁 <b>来自：</b>{sender.emby_account if sender else '神秘人'}{best_tag}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>红包进度：</b>{packet.total_count - packet.remaining_count}/{packet.total_count}\n"
            f"💵 <b>剩余金额：</b>{packet.remaining_amount} MP"
        )

        # 更新按钮
        if packet.remaining_count > 0:
            keyboard = [[InlineKeyboardButton(f"🧧 开红包 ({packet.remaining_count})", callback_data=f"rp_open_{packet_id}")]]
        else:
            keyboard = []

        await query.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
            parse_mode='HTML'
        )

        logger.info(f"[红包] 用户{user_id}抢到红包: {got_amount}MP, ID={packet_id}")


async def redpacket_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看红包状态"""
    msg = update.effective_message
    if not msg:
        return

    # 回复最近发送的红包状态
    with get_session() as session:
        recent_packets = session.query(RedPacket).filter_by(
            sender_id=update.effective_user.id
        ).order_by(RedPacket.created_at.desc()).limit(5).all()

        if not recent_packets:
            await reply_with_auto_delete(
                msg,
                "🧧 <b>你还没有发送过红包喵~</b>\n\n"
                "使用 <code>/redpacket 金额 数量</code> 发送红包"
            )
            return

        lines = ["🧧 <b>【 我的红包记录 】</b>\n━━━━━━━━━━━━━━━━━━\n"]
        for p in recent_packets:
            status = "已抢完" if p.remaining_count == 0 else f"剩{p.remaining_count}个"
            lines.append(
                f"💰 {p.total_amount} MP × {p.total_count}个\n"
                f"📊 {status} | {p.created_at.strftime('%m-%d %H:%M')}\n"
            )

        await reply_with_auto_delete(msg, "\n".join(lines))


def register(app):
    app.add_handler(CommandHandler("redpacket", send_redpacket))
    app.add_handler(CommandHandler("hongbao", send_redpacket))
    app.add_handler(CommandHandler("rpstatus", redpacket_status))
    app.add_handler(CallbackQueryHandler(open_redpacket, pattern="^rp_open_"))
