"""
进度预告模块
显示用户距离下一个里程碑、奖励还有多远
[修复记录] - 2026-01-03
- 修复 activity_level 字段不存在，改用 total_presence_points 计算
- 修复 duel_streak 字段不存在，改用 win_streak
- 修复 total_checkin 字段不存在，改用 total_checkin_days
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding
from plugins.feedback_utils import progress_bar
from utils import edit_with_auto_delete


def get_checkin_progress(user: UserBinding) -> dict:
    """获取签到进度预告"""
    consecutive = user.consecutive_checkin or 0
    # 每10天一个大奖励
    cycle_day = (consecutive - 1) % 10 + 1 if consecutive > 0 else 1
    days_to_bonus = 10 - cycle_day + 1

    return {
        "type": "checkin",
        "title": "🍬 签到奖励进度",
        "current": consecutive,
        "cycle_day": cycle_day,
        "days_to_bonus": days_to_bonus if days_to_bonus <= 10 else 0,
        "next_bonus": f"{days_to_bonus}天后大礼包" if days_to_bonus > 0 else "今日领取！",
        "progress_bar": progress_bar(cycle_day, 10),
        "description": f"已连续签到 {consecutive} 天",
    }


def get_activity_progress(user: UserBinding) -> dict:
    """获取活跃度进度预告 - [修复] 使用 total_presence_points"""
    total_points = user.total_presence_points or 0
    # 活跃度等级：每100点1级
    activity_level = total_points // 100
    next_level = activity_level + 1
    exp_needed = next_level * 100 - total_points
    current_level_progress = total_points % 100

    return {
        "type": "activity",
        "title": "📊 活跃度进度",
        "current_level": activity_level,
        "next_level": next_level,
        "exp_needed": exp_needed,
        "current_level_progress": current_level_progress,
        "progress_bar": progress_bar(current_level_progress, 100),
        "description": f"当前 Lv.{activity_level} ({current_level_progress}/100)，距离 Lv.{next_level} 还需 {exp_needed} 点",
    }


def get_duel_streak_progress(user: UserBinding) -> dict:
    """获取决斗连胜进度预告 - [修复] 使用 win_streak"""
    streak = user.win_streak or 0

    # 连胜里程碑
    milestones = [3, 5, 10, 20, 50, 100]
    next_milestone = None
    for m in milestones:
        if streak < m:
            next_milestone = m
            break

    if next_milestone:
        wins_needed = next_milestone - streak
        return {
            "type": "duel_streak",
            "title": "⚔️ 决斗连胜进度",
            "current_streak": streak,
            "next_milestone": next_milestone,
            "wins_needed": wins_needed,
            "progress_bar": progress_bar(streak, next_milestone, length=10),
            "description": f"当前 {streak} 连胜，距离 {next_milestone} 连胜成就还差 {wins_needed} 场",
        }
    else:
        return {
            "type": "duel_streak",
            "title": "⚔️ 决斗连胜进度",
            "current_streak": streak,
            "description": f"已达成 {streak} 连胜，太厉害了喵！",
        }


def get_total_checkin_progress(user: UserBinding) -> dict:
    """获取总签到数进度预告 - [修复] 使用 total_checkin_days"""
    total = user.total_checkin_days or 0

    # 总签到里程碑
    milestones = [7, 30, 100, 365, 1000]
    next_milestone = None
    for m in milestones:
        if total < m:
            next_milestone = m
            break

    if next_milestone:
        days_needed = next_milestone - total
        return {
            "type": "total_checkin",
            "title": "📅 总签到数进度",
            "current": total,
            "next_milestone": next_milestone,
            "days_needed": days_needed,
            "description": f"累计签到 {total} 天，距离 {next_milestone} 天成就还差 {days_needed} 天",
        }
    else:
        return {
            "type": "total_checkin",
            "title": "📅 总签到数进度",
            "current": total,
            "description": f"累计签到 {total} 天，传奇魔法少女！",
        }


async def progress_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示进度预告"""
    msg = update.effective_message
    query = update.callback_query if hasattr(update, 'callback_query') else None

    if not msg and not query:
        return

    user_obj = query.from_user if query else update.effective_user

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_obj.id).first()

        if not u or not u.emby_account:
            txt = "👻 <b>请先 /bind 缔结魔法契约喵！</b>"
            if query:
                await query.answer(txt, show_alert=True)
            else:
                await msg.reply_html(txt)
            return

        is_vip = u.is_vip
        emby_account = u.emby_account
        vip_badge = " 👑" if is_vip else ""

        # 获取各项进度
        checkin_p = get_checkin_progress(u)
        activity_p = get_activity_progress(u)
        duel_p = get_duel_streak_progress(u)
        total_p = get_total_checkin_progress(u)

        txt = (
            f"📈 <b>【 进 度 预 告 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>{emby_account}</b>{vip_badge}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
        )

        # 签到进度
        txt += (
            f"🍬 <b>{checkin_p['title']}</b>\n"
            f"{checkin_p['progress_bar']}\n"
            f"{checkin_p['description']}\n"
            f"🎁 <b>下一奖励：</b>{checkin_p['next_bonus']}\n\n"
        )

        # 活跃度进度
        txt += (
            f"📊 <b>{activity_p['title']}</b>\n"
            f"{activity_p['progress_bar']}\n"
            f"{activity_p['description']}\n\n"
        )

        # 决斗连胜进度
        if 'progress_bar' in duel_p:
            txt += (
                f"⚔️ <b>{duel_p['title']}</b>\n"
                f"{duel_p['progress_bar']}\n"
                f"{duel_p['description']}\n\n"
            )
        else:
            txt += (
                f"⚔️ <b>{duel_p['title']}</b>\n"
                f"{duel_p['description']}\n\n"
            )

        # 总签到进度
        txt += (
            f"📅 <b>{total_p['title']}</b>\n"
            f"{total_p['description']}\n"
        )

        txt += (
            "\n━━━━━━━━━━━━━━━━━━\n"
            f"<i>\"继续加油，更多奖励在等你喵！(｡•̀ᴗ-)✧\"</i>"
        )

        buttons = [
            [InlineKeyboardButton("🔄 刷新进度", callback_data="progress_refresh"),
             InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")]
        ]

        if query:
            await edit_with_auto_delete(query, txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        else:
            await msg.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))


async def progress_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理进度预告按钮回调"""
    await progress_preview(update, context)


def register(app):
    """注册插件处理器"""
    app.add_handler(CommandHandler("progress", progress_preview))
    app.add_handler(CallbackQueryHandler(progress_callback, pattern="^progress_refresh$"))
