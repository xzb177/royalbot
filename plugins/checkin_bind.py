from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database import Session, UserBinding, create_or_update_user
from datetime import datetime, timedelta
from utils import reply_with_auto_delete
import random

async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = Session()
    user = session.query(UserBinding).filter_by(tg_id=user_id).first()
    if not user or not user.emby_account:
        await reply_with_auto_delete(update.message, "💔 <b>请先绑定账号！</b>\n使用 <code>/bind</code>")
        session.close()
        return

    # 检查是否今天已经签到过
    now = datetime.now()
    if user.last_checkin:
        # 判断上次签到是否是今天
        last_checkin_date = user.last_checkin.date()
        today_date = now.date()
        if last_checkin_date >= today_date:
            # 计算距离下次签到的剩余时间 - 修复：先归零再+1天
            next_available = user.last_checkin.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            remaining = next_available - now
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)

            session.close()
            await reply_with_auto_delete(
                update.message,
                f"⏰ <b>今日已签到</b>\n\n"
                f"您今天已经签过到了！\n"
                f"距离下次签到还有：<b>{hours}小时{minutes}分钟</b>\n\n"
                f"<i>\"明天再来哦！(｡•̀ᴗ-)✧\"</i>"
            )
            return

    base_points = random.randint(10, 30)
    user.last_checkin = now
    if user.is_vip:
        base_points *= 2
        user.points += base_points
        msg = f"💖 <b>VIP 尊贵暴击！</b>\n您获得了双倍魔力：<b>{base_points} MP</b>！\n当前余额：{user.points}"
    else:
        user.points += base_points
        msg = f"✨ <b>签到成功！</b>\n获得魔力：<b>{base_points} MP</b>\n当前余额：{user.points}\n<i>(升级 VIP 可享双倍哦!)</i>"

    session.commit()
    session.close()
    await reply_with_auto_delete(update.message, msg)

async def bind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        name = context.args[0]
        user = update.effective_user
        create_or_update_user(user.id, name)
        await reply_with_auto_delete(update.message, f"🌸 <b>契约已缔结！</b>\n\n欢迎加入云海，<b>{name}</b>！\n您现在可以签到领取魔力啦！")
    except:
        await reply_with_auto_delete(update.message, "⚠️ <b>用法错误</b>\n请发送：<code>/bind 您的Emby账号</code>")

def register(app):
    app.add_handler(CommandHandler("checkin", checkin))
    app.add_handler(CommandHandler("daily", checkin))
    app.add_handler(CommandHandler("bind", bind))
