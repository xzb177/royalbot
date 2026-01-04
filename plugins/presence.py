"""
在线活跃度系统 - 累积在线奖励
- 累积活跃值
- 达到阈值自动发放奖励
- 增加用户粘性
"""

from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
from database import get_session, UserBinding
from utils import reply_with_auto_delete
from datetime import datetime, timedelta
import random

# 活跃度阈值配置
PRESENCE_LEVELS = [
    {"level": 1, "points": 50, "name": "活跃新星", "emoji": "⭐"},
    {"level": 2, "points": 150, "name": "常驻居民", "emoji": "🌟"},
    {"level": 3, "points": 350, "name": "社区骨干", "emoji": "💫"},
    {"level": 4, "points": 700, "name": "魔法达人", "emoji": "✨"},
    {"level": 5, "points": 1200, "name": "传说级", "emoji": "🌠"},
]

# 每条消息获得的活跃度
POINTS_PER_MESSAGE = 1

# 时间窗口（分钟）- 只有在窗口内发言才算活跃
TIME_WINDOW = 60


async def track_presence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """追踪用户活跃度"""
    user = update.effective_user
    if user.is_bot:
        return

    chat = update.effective_chat
    if chat.type == "private":
        return

    text = update.message.text.lower() if update.message.text else ""

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user.id).first()

        if not u:
            return

        now = datetime.now()

        # 检查上次活跃时间
        if u.last_active_time:
            time_diff = (now - u.last_active_time).total_seconds()
            if time_diff > TIME_WINDOW * 60:
                # 超过时间窗口，重置今日累积
                u.daily_presence_points = 0

        # 增加活跃度
        gain = POINTS_PER_MESSAGE
        if u.is_vip:
            gain = 2  # VIP双倍

        u.daily_presence_points = (u.daily_presence_points or 0) + gain
        u.total_presence_points = (u.total_presence_points or 0) + gain
        u.last_active_time = now

        # 检查是否达到奖励阈值
        reward_given = False
        reward_msg = None

        for level_info in PRESENCE_LEVELS:
            level = level_info["level"]
            threshold = level_info["points"]

            # 获取用户当前已领取的最高等级
            claimed_levels = u.presence_levels_claimed or "0"
            claimed_list = [int(x) for x in claimed_levels.split(",") if x.isdigit()]

            if level not in claimed_list and u.daily_presence_points >= threshold:
                # 发放奖励
                base_reward = threshold // 2  # 奖励是阈值的一半
                if u.is_vip:
                    base_reward = int(base_reward * 1.5)

                u.points += base_reward
                u.presence_levels_claimed = f"{claimed_levels},{level}" if claimed_levels else str(level)

                reward_given = True
                reward_msg = (
                    f"🎉 <b>【 活 跃 度 · 达 成 ！】</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{level_info['emoji']} <b>称号：</b> {level_info['name']}\n"
                    f"📊 <b>今日活跃：</b> {u.daily_presence_points} 点\n"
                    f"💰 <b>奖励：</b> +{base_reward} MP\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                )
                break

        session.commit()

        # 如果获得了奖励，发送通知
        if reward_given and reward_msg:
            # 只有小概率发送通知，避免刷屏
            if random.random() < 0.3:
                await reply_with_auto_delete(update.message, reward_msg, disable_notification=True)


async def presence_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看活跃度（支持命令和回调两种方式）"""
    query = getattr(update, "callback_query", None)
    msg = update.effective_message
    if not msg and not query:
        return

    user_id = update.effective_user.id

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not u or not u.emby_account:
            error_txt = "💔 <b>请先绑定账号喵！</b>"
            if query:
                await query.edit_message_text(error_txt, parse_mode='HTML')
            else:
                await reply_with_auto_delete(msg, error_txt)
            return

        # 计算当前等级和下一级
        current_points = u.daily_presence_points or 0
        total_points = u.total_presence_points or 0

        # 检查是否需要重置（跨天）
        today = datetime.now().date()
        if u.last_active_time:
            last_date = u.last_active_time.date() if isinstance(u.last_active_time, datetime) else u.last_active_time
            if last_date < today:
                current_points = 0
                u.daily_presence_points = 0

        current_level = 0
        next_level = None
        progress_percent = 0

        for i, level_info in enumerate(PRESENCE_LEVELS):
            if current_points >= level_info["points"]:
                current_level = level_info["level"]
            elif next_level is None:
                next_level = level_info
                prev_points = PRESENCE_LEVELS[i - 1]["points"] if i > 0 else 0
                progress_percent = int((current_points - prev_points) / (level_info["points"] - prev_points) * 100)
                break

        vip_badge = " 👑" if u.is_vip else ""

        txt = (
            f"📊 <b>【 活 跃 度 统 计 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>魔法少女：</b> {u.emby_account}{vip_badge}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>今日活跃：</b> {current_points} 点\n"
            f"📈 <b>累计活跃：</b> {total_points} 点\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )

        if next_level:
            bar_length = 10
            filled = int(bar_length * progress_percent / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            txt += (
                f"🎯 <b>下一等级：</b> {next_level['name']}\n"
                f"📊 <b>进度：</b> [{bar}] {progress_percent}%\n"
                f"🎁 <b>奖励：</b> {next_level['points'] // 2} MP\n\n"
            )
        else:
            txt += f"🏆 <b>已达最高等级！</b>\n\n"

        txt += (
            f"💡 <b>提示：</b>\n"
            f"• 在群聊发言即可累积活跃度\n"
            f"• 达到阈值自动获得MP奖励\n"
            f"• VIP用户活跃度获取+100%\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>\"保持活跃，奖励不断！\"</i>"
        )

        session.commit()

    # 根据调用方式选择编辑或回复
    if query:
        await query.edit_message_text(txt, parse_mode='HTML')
    else:
        await reply_with_auto_delete(msg, txt)


async def presence_rank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """活跃度排行榜"""
    msg = update.effective_message
    if not msg:
        return

    with get_session() as session:
        # 获取今日活跃度排行榜
        users = session.query(UserBinding).filter(
            UserBinding.emby_account != None,
            UserBinding.daily_presence_points > 0
        ).order_by(UserBinding.daily_presence_points.desc()).limit(10).all()

        txt = "🏆 <b>【 今 日 活 跃 排 行 榜 】</b>\n"
        txt += "━━━━━━━━━━━━━━━━━━\n"

        for i, u in enumerate(users, 1):
            medal = ""
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i:2d}."

            vip_badge = "👑" if u.is_vip else ""
            points = u.daily_presence_points or 0

            # 检查是否需要重置
            today = datetime.now().date()
            if u.last_active_time:
                last_date = u.last_active_time.date() if isinstance(u.last_active_time, datetime) else u.last_active_time
                if last_date < today:
                    points = 0

            if points > 0:
                txt += f"{medal} {u.emby_account[:12]:12s} {vip_badge}  {points:4d} 点\n"

        txt += "━━━━━━━━━━━━━━━━━━\n"
        txt += "<i>\"每天保持活跃，奖励拿不停！\"</i>"

    await reply_with_auto_delete(msg, txt)


def register(app):
    app.add_handler(CommandHandler("presence", presence_cmd))
    app.add_handler(CommandHandler("active", presence_cmd))
    app.add_handler(CommandHandler("rank", presence_rank_cmd))

    # 监听所有消息追踪活跃度
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_presence))
