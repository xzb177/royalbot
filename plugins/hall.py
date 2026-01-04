"""
荣耀殿堂排行榜 - 魔法少女版
- 显示战力 TOP 10
- VIP/普通双界面风格
- 动态称号系统
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes
from database import get_session, UserBinding
from utils import reply_with_auto_delete

# 排行榜每页显示数量
PAGE_SIZE = 10


def get_rank_title(attack):
    """根据战力获取称号"""
    if attack >= 10000:
        return "👑 星辰主宰"
    elif attack >= 5000:
        return "🌟 传奇大魔导"
    elif attack >= 2000:
        return "💫 星之大魔导师"
    elif attack >= 1000:
        return "⭐ 大魔导师"
    elif attack >= 500:
        return "🔥 魔导师"
    elif attack >= 200:
        return "⚔️ 高级魔法师"
    elif attack >= 100:
        return "🛡️ 见习魔法师"
    elif attack >= 50:
        return "🌱 初级魔法师"
    else:
        return "👶 冒险者学徒"


def format_rank_list(users, current_user_id, start_rank=1):
    """格式化排行榜列表"""
    lines = []
    for i, user in enumerate(users):
        rank = start_rank + i
        is_current = user.tg_id == current_user_id

        # 排名图标
        if rank == 1:
            rank_icon = "🥇"
        elif rank == 2:
            rank_icon = "🥈"
        elif rank == 3:
            rank_icon = "🥉"
        else:
            rank_icon = f"{rank:2d}"

        # VIP 标记
        vip_mark = "👑" if user.is_vip else ""

        # 称号
        title = get_rank_title(user.attack)

        # 高亮当前用户
        if is_current:
            lines.append(f"━━━━━━━━━━━━━━━━━━")
            lines.append(f"{rank_icon} │ <b>{vip_mark} {user.emby_account}</b>")
            lines.append(f"    │ 战力: <b>{user.attack}</b> │ {title}")
            lines.append(f"━━━━━━━━━━━━━━━━━━")
        else:
            lines.append(f"{rank_icon} │ {vip_mark} {user.emby_account}")
            lines.append(f"    │ 战力: {user.attack} │ {title}")

    return "\n".join(lines)


async def hall_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """荣耀殿堂 - 战力排行榜（支持命令和回调两种方式）"""
    query = getattr(update, "callback_query", None)
    msg = update.effective_message
    if not msg and not query:
        return

    user_id = update.effective_user.id

    with get_session() as session:
        current_user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not current_user or not current_user.emby_account:
            error_txt = "💔 <b>【 魔 法 契 约 丢 失 】</b>\n请先使用 <code>/bind</code> 缔结魔法契约喵！"
            if query:
                await query.edit_message_text(error_txt, parse_mode='HTML')
            else:
                await reply_with_auto_delete(msg, error_txt)
            return

        # 获取所有有战力的用户
        all_users = session.query(UserBinding).filter(
            UserBinding.emby_account != None,
            UserBinding.attack > 0
        ).order_by(UserBinding.attack.desc()).all()

        if not all_users:
            empty_txt = (
                f"🏆 <b>【 荣 耀 殿 堂 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"暂无战力记录喵！\n\n"
                f"<i>\"快去锻造魔法武器提升战力吧！(｡•̀ᴗ-)✧\"</i>"
            )
            if query:
                await query.edit_message_text(empty_txt, parse_mode='HTML')
            else:
                await reply_with_auto_delete(msg, empty_txt)
            return

        # 获取当前用户排名
        current_rank = None
        for i, u in enumerate(all_users):
            if u.tg_id == user_id:
                current_rank = i + 1
                break

        # 获取 TOP 10
        top_users = all_users[:PAGE_SIZE]

        # 在session关闭前保存需要的数据
        is_vip = current_user.is_vip
        attack = current_user.attack
        weapon = current_user.weapon

    # 构建消息（在session关闭后）
    if is_vip:
        text = (
            f"🏆 <b>【 皇 家 · 荣 耀 殿 堂 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🥂 <b>Welcome, my dear Master~</b>\n"
            f"这是全服魔法少女的实力榜单，您的名字也在其中闪耀喵~\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏅 <b>:: TOP {PAGE_SIZE} 星 之 魔导士 ::</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{format_rank_list(top_users, user_id)}\n\n"
        )
        if current_rank and current_rank > PAGE_SIZE:
            text += (
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>您的排名：</b> 第 {current_rank} 位\n"
                f"⚔️ <b>您的战力：</b> <b>{attack}</b>\n"
                f"🎖️ <b>您的称号：</b> {get_rank_title(attack)}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>\"继续努力，看板娘相信您能登顶喵~(*/ω＼*)\"</i>"
            )
    else:
        text = (
            f"🏆 <b>【 魔 法 学 院 · 荣 耀 榜 单 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ <b>欢迎来到实力榜单喵！</b>\n"
            f"这里记录了所有魔法少女的荣耀战绩喵~\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏅 <b>:: TOP {PAGE_SIZE} 排 行 榜 ::</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{format_rank_list(top_users, user_id)}\n\n"
        )
        if current_rank and current_rank > PAGE_SIZE:
            text += (
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>您的排名：</b> 第 {current_rank} 位\n"
                f"⚔️ <b>您的战力：</b> {attack}\n"
                f"🎖️ <b>您的称号：</b> {get_rank_title(attack)}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>💡 想获得专属称号和双倍奖励吗？觉醒 VIP 解锁更多皇家特权喵！</i>"
            )

    buttons = []
    if weapon:
        buttons.append([InlineKeyboardButton("⚔️ 我的装备", callback_data="my_weapon"),
                       InlineKeyboardButton("⚒️ 去炼金", callback_data="forge")])
    else:
        buttons.append([InlineKeyboardButton("⚒️ 去炼金", callback_data="forge")])

    # 根据调用方式选择编辑或回复
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None, parse_mode='HTML')
    else:
        await reply_with_auto_delete(msg, text, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)


def register(app):
    app.add_handler(CommandHandler("hall", hall_leaderboard))
