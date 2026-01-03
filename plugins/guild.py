"""
公会系统 - Guild System
- 创建/加入公会
- 公会等级和经验
- 公会成员管理
- 公会贡献系统
- 公会战力排行
"""
import random
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding, Guild
from utils import reply_with_auto_delete

logger = logging.getLogger(__name__)


# ==========================================
# 公会配置
# ==========================================

# 公会等级配置
GUILD_LEVELS = {
    1: {"name": "初级公会", "exp": 0, "max_members": 20, "benefit": "无"},
    2: {"name": "中级公会", "exp": 1000, "max_members": 30, "benefit": "签到+5 MP"},
    3: {"name": "高级公会", "exp": 5000, "max_members": 40, "benefit": "签到+10 MP, 锻造9折"},
    4: {"name": "精英公会", "exp": 15000, "max_members": 50, "benefit": "签到+15 MP, 锻造8折"},
    5: {"name": "传奇公会", "exp": 50000, "max_members": 60, "benefit": "签到+20 MP, 锻造7折, 每日礼包"},
    6: {"name": "史诗公会", "exp": 100000, "max_members": 70, "benefit": "签到+30 MP, 抽卡9折"},
    7: {"name": "神话公会", "exp": 200000, "max_members": 80, "benefit": "签到+40 MP, 抽卡8折"},
    8: {"name": "圣域公会", "exp": 500000, "max_members": 90, "benefit": "签到+50 MP, 全场8折"},
    9: {"name": "神域公会", "exp": 1000000, "max_members": 100, "benefit": "签到+75 MP, 全场7折"},
    10: {"name": "终极公会", "exp": 2000000, "max_members": 120, "benefit": "签到+100 MP, 全场5折"},
}

# 创建公会费用
CREATE_GUILD_COST = 5000

# 公会名称长度限制
GUILD_NAME_MIN_LEN = 2
GUILD_NAME_MAX_LEN = 12


# ==========================================
# 工具函数
# ==========================================

def get_guild_level_info(level: int) -> dict:
    """获取公会等级信息"""
    return GUILD_LEVELS.get(min(level, 10), GUILD_LEVELS[10])


def get_guild_next_level_exp(level: int) -> int:
    """获取升级所需经验"""
    if level >= 10:
        return 0
    return GUILD_LEVELS[level + 1]["exp"]


def add_guild_member(guild: Guild, user_id: int) -> None:
    """添加公会成员"""
    members = guild.members or ""
    member_list = members.split(",") if members else []
    if str(user_id) not in member_list:
        member_list.append(str(user_id))
        guild.members = ",".join(member_list)
        guild.member_count = len(member_list)


def remove_guild_member(guild: Guild, user_id: int) -> None:
    """移除公会成员"""
    members = guild.members or ""
    member_list = members.split(",") if members else []
    if str(user_id) in member_list:
        member_list.remove(str(user_id))
        guild.members = ",".join(member_list)
        guild.member_count = len(member_list)


def calculate_guild_power(guild: Guild) -> int:
    """计算公会总战力"""
    if not guild.members:
        return 0
    from database import get_session
    total = 0
    with get_session() as session:
        member_ids = [int(uid) for uid in guild.members.split(",") if uid]
        for uid in member_ids:
            user = session.query(UserBinding).filter_by(tg_id=uid).first()
            if user:
                total += (user.attack or 0)
    return total


def get_guild_benefit(guild: Guild) -> dict:
    """获取公会福利"""
    level_info = get_guild_level_info(guild.level or 1)
    benefits = {
        "checkin_bonus": 0,
        "forge_discount": 1.0,
        "gacha_discount": 1.0,
        "daily_gift": False
    }

    level = guild.level or 1
    if level >= 2:
        benefits["checkin_bonus"] = min(5 * (level - 1), 100)
    if level >= 3:
        benefits["forge_discount"] = max(0.9 - (level - 3) * 0.1, 0.5)
    if level >= 6:
        benefits["gacha_discount"] = max(0.9 - (level - 6) * 0.1, 0.5)
    if level >= 5:
        benefits["daily_gift"] = True

    return benefits


# ==========================================
# 公会主界面
# ==========================================

async def guild_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """公会主界面"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user or not user.emby_account:
            await reply_with_auto_delete(msg, "💔 <b>请先绑定账号喵！</b>\n\n使用 <code>/bind �账号</code> 绑定后再加入公会。")
            return

        # 检查用户是否已加入公会
        if user.guild_id:
            guild = session.query(Guild).filter_by(id=user.guild_id).first()
            if guild:
                await show_guild_info(msg, guild, user, session)
                return

        # 未加入公会，显示公会列表
        await show_guild_list(msg, user, session)


async def show_guild_info(msg, guild: Guild, user: UserBinding, session):
    """显示公会信息"""
    level_info = get_guild_level_info(guild.level or 1)
    benefits = get_guild_benefit(guild)
    guild_power = calculate_guild_power(guild)
    is_leader = (guild.leader_id == user.tg_id)

    # 获取公会成员信息
    member_list = []
    if guild.members:
        member_ids = [int(uid) for uid in guild.members.split(",") if uid]
        for uid in member_ids[:10]:  # 只显示前10个
            m = session.query(UserBinding).filter_by(tg_id=uid).first()
            if m:
                role = "👑会长" if uid == guild.leader_id else "👤成员"
                member_list.append(f"{role} {m.first_name or '神秘人'} (⚡{m.attack or 0})")

    members_text = "\n".join(member_list) if member_list else "暂无成员"
    if len(member_ids) > 10:
        members_text += f"\n... 还有 {len(member_ids) - 10} 位成员"

    lines = [
        "🏰 <b>【 公 会 信 息 】</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"🏛️ <b>公会名称：</b> {guild.name}",
        f"👑 <b>公会会长：</b> {guild.leader_name or '未知'}",
        f"📊 <b>公会等级：</b> Lv.{guild.level or 1} {level_info['name']}",
        f"⭐ <b>公会经验：</b> {guild.exp or 0}/{get_guild_next_level_exp(guild.level or 1)}",
        f"👥 <b>成员数量：</b> {guild.member_count or 0}/{guild.max_members or 20}",
        f"⚡ <b>公会战力：</b> {guild_power}",
        f"💰 <b>公会金库：</b> {guild.treasury or 0} MP",
        f"📅 <b>创建时间：</b> {(guild.created_at or datetime.now()).strftime('%Y-%m-%d')}",
        "",
        "🎁 <b>公会福利：</b>",
    ]

    if benefits["checkin_bonus"] > 0:
        lines.append(f"   ✨ 签到奖励 +{benefits['checkin_bonus']} MP")
    if benefits["forge_discount"] < 1.0:
        lines.append(f"   ⚒️ 锻造 {int(benefits['forge_discount'] * 10)} 折")
    if benefits["gacha_discount"] < 1.0:
        lines.append(f"   🎰 抽卡 {int(benefits['gacha_discount'] * 10)} 折")
    if benefits["daily_gift"]:
        lines.append(f"   🎁 每日礼包可领取")

    if guild.announcement:
        lines.extend([
            "",
            f"📢 <b>公会公告：</b>",
            f"   {guild.announcement}"
        ])

    lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━",
        "👥 <b>公会成员：</b>",
        members_text
    ])

    # 构建按钮
    buttons = []

    if is_leader:
        buttons.append([
            InlineKeyboardButton("📝 编辑公告", callback_data=f"guild_edit_announce_{guild.id}"),
            InlineKeyboardButton("👥 审批申请", callback_data=f"guild_apps_{guild.id}")
        ])
        buttons.append([
            InlineKeyboardButton("💰 捐赠金库", callback_data=f"guild_donate_{guild.id}"),
            InlineKeyboardButton("🚪 解散公会", callback_data=f"guild_disband_{guild.id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton("💰 捐赠金库", callback_data=f"guild_donate_{guild.id}"),
            InlineKeyboardButton("🚪 退出公会", callback_data=f"guild_leave_{guild.id}")
        ])

    buttons.append([
        InlineKeyboardButton("🏆 公会排行", callback_data="guild_rank"),
        InlineKeyboardButton("🔙 返回", callback_data="guild_back")
    ])

    await msg.reply_html(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_guild_list(msg, user: UserBinding, session):
    """显示公会列表"""
    guilds = session.query(Guild).order_by(Guild.total_power.desc()).limit(10).all()

    lines = [
        "🏰 <b>【 公 会 列 表 】</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"👤 <b>您的状态：</b> 未加入公会",
        "",
        "🏆 <b>公会排行榜 (Top 10)：</b>",
        ""
    ]

    for idx, guild in enumerate(guilds, 1):
        level_info = get_guild_level_info(guild.level or 1)
        medal = ["🥇", "🥈", "🥉"][idx - 1] if idx <= 3 else f"{idx}."
        can_join = (guild.member_count or 0) < (guild.max_members or 20)

        lines.append(
            f"{medal} <b>{guild.name}</b>"
        )
        lines.append(
            f"    Lv.{guild.level or 1} | ⚡{guild.total_power or 0} | 👥{guild.member_count or 0}/{guild.max_members or 20}"
        )
        if can_join:
            lines.append(f"    [📮 可申请]")
        else:
            lines.append(f"    [🚫 已满员]")
        lines.append("")

    lines.extend([
        "━━━━━━━━━━━━━━━━━━",
        "<i>\"加入公会，与其他魔法师一起战斗！\"</i>"
    ])

    # 按钮
    buttons = [
        [InlineKeyboardButton("➕ 创建公会", callback_data="guild_create")],
        [InlineKeyboardButton("🔙 返回", callback_data="guild_back")]
    ]

    await msg.reply_html(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ==========================================
# 创建公会
# ==========================================

async def guild_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始创建公会流程"""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    user_id = query.from_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user:
            await query.edit_message_text("💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        # 检查是否已加入公会
        if user.guild_id:
            await query.edit_message_text("⚠️ <b>您已加入公会喵！</b>\n\n请先退出当前公会再创建新公会。", parse_mode='HTML')
            return

        # 检查余额
        cost = CREATE_GUILD_COST
        if user.is_vip:
            cost = int(cost * 0.7)

        if user.points < cost:
            await query.edit_message_text(
                f"💸 <b>魔力不足喵！</b>\n\n"
                f"创建公会需要 <b>{cost}</b> MP\n"
                f"当前余额：<b>{user.points}</b> MP",
                parse_mode='HTML'
            )
            return

        text = (
            f"➕ <b>【 创 建 公 会 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>创建费用：</b> {cost} MP {'👑VIP专享7折' if user.is_vip else ''}\n"
            f"📏 <b>名称长度：</b> {GUILD_NAME_MIN_LEN}-{GUILD_NAME_MAX_LEN} 字符\n\n"
            f"请输入公会名称：\n"
            f"<i>（输入 /cancel 取消）</i>"
        )

        await query.edit_message_text(text, parse_mode='HTML')

        # 标记用户正在创建公会
        context.bot_data[f"creating_guild_{user_id}"] = True


async def guild_create_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理公会名称输入"""
    msg = update.effective_message
    if not msg or not msg.text:
        return

    user_id = update.effective_user.id
    guild_name = msg.text.strip()

    # 检查是否在创建流程中
    if not context.bot_data.get(f"creating_guild_{user_id}"):
        return

    # 取消命令
    if guild_name.lower() == "/cancel":
        del context.bot_data[f"creating_guild_{user_id}"]
        await msg.reply_html("❌ <b>已取消创建公会</b>")
        return

    # 验证名称
    if len(guild_name) < GUILD_NAME_MIN_LEN or len(guild_name) > GUILD_NAME_MAX_LEN:
        await msg.reply_html(
            f"⚠️ <b>名称长度不符合要求喵！</b>\n\n"
            f"名称长度需要 {GUILD_NAME_MIN_LEN}-{GUILD_NAME_MAX_LEN} 字符"
        )
        return

    # 检查名称是否已存在
    with get_session() as session:
        existing = session.query(Guild).filter_by(name=guild_name).first()
        if existing:
            await msg.reply_html(f"⚠️ <b>公会名称「{guild_name}」已被使用喵！</b>\n\n请换一个名称试试。")
            return

        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user:
            await msg.reply_html("💔 <b>请先绑定账号喵！</b>")
            del context.bot_data[f"creating_guild_{user_id}"]
            return

        # 检查余额
        cost = CREATE_GUILD_COST
        if user.is_vip:
            cost = int(cost * 0.7)

        if user.points < cost:
            await msg.reply_html(f"💸 <b>魔力不足！</b>\n\n需要 {cost} MP")
            del context.bot_data[f"creating_guild_{user_id}"]
            return

        # 创建公会
        guild = Guild(
            name=guild_name,
            leader_id=user_id,
            leader_name=user.first_name or "神秘人",
            members=str(user_id),
            member_count=1,
            max_members=20,
            total_power=(user.attack or 0)
        )

        user.points -= cost
        user.guild_id = guild.id
        user.guild_join_date = datetime.now()
        user.guild_contribution = cost

        session.add(guild)
        session.commit()

        del context.bot_data[f"creating_guild_{user_id}"]

        await msg.reply_html(
            f"🎉 <b>公 会 创 建 成 功 ！</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏛️ <b>公会名称：</b> {guild_name}\n"
            f"👑 <b>公会会长：</b> {user.first_name or '神秘人'}\n"
            f"⚡ <b>初始战力：</b> {user.attack or 0}\n"
            f"💰 <b>剩余魔力：</b> {user.points} MP\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>\"恭喜！您的公会诞生了！\"</i>"
        )


# ==========================================
# 公会排行
# ==========================================

async def guild_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示公会排行榜"""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    with get_session() as session:
        guilds = session.query(Guild).order_by(Guild.total_power.desc()).limit(20).all()

        lines = [
            "🏆 <b>【 公 会 排 行 榜 】</b>",
            "━━━━━━━━━━━━━━━━━━",
            ""
        ]

        for idx, guild in enumerate(guilds, 1):
            level_info = get_guild_level_info(guild.level or 1)
            if idx == 1:
                medal = "🥇"
            elif idx == 2:
                medal = "🥈"
            elif idx == 3:
                medal = "🥉"
            else:
                medal = f"{idx:2d}."

            lines.append(
                f"{medal} <b>{guild.name}</b> - Lv.{guild.level or 1}"
            )
            lines.append(
                f"    ⚡ {guild.total_power or 0} | 👥 {guild.member_count or 0} | 💰 {guild.treasury or 0}"
            )
            lines.append("")

        lines.extend([
            "━━━━━━━━━━━━━━━━━━",
            "<i>\"努力提升公会战力，登顶排行榜！\"</i>"
        ])

        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 返回", callback_data="guild_back")]
            ]),
            parse_mode='HTML'
        )


# ==========================================
# 退出/解散公会
# ==========================================

async def guild_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """退出公会"""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    user_id = query.from_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user or not user.guild_id:
            await query.edit_message_text("⚠️ <b>您未加入公会喵！</b>", parse_mode='HTML')
            return

        guild = session.query(Guild).filter_by(id=user.guild_id).first()
        if not guild:
            user.guild_id = None
            session.commit()
            await query.edit_message_text("⚠️ <b>公会不存在喵！</b>", parse_mode='HTML')
            return

        # 会长不能直接退出
        if guild.leader_id == user_id:
            await query.edit_message_text(
                "⚠️ <b>会长不能退出公会喵！</b>\n\n"
                "请先转让会长或解散公会。",
                parse_mode='HTML'
            )
            return

        # 移除成员
        remove_guild_member(guild, user_id)
        user.guild_id = None
        user.guild_join_date = None
        user.guild_contribution = 0

        # 重新计算公会战力
        guild.total_power = calculate_guild_power(guild)

        session.commit()

        await query.edit_message_text(
            f"🚪 <b>已退出公会</b>\n\n"
            f"您已离开 <b>{guild.name}</b>\n"
            f"<i>\"江湖路远，后会有期！\"</i>",
            parse_mode='HTML'
        )


async def guild_disband(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """解散公会"""
    query = update.callback_query
    if not query:
        return

    await query.answer("⚠️ 解散后无法恢复！", show_alert=True)

    # 这里应该有一个确认步骤，简化处理直接返回提示
    await query.edit_message_text(
        "⚠️ <b>解散公会功能</b>\n\n"
        "请联系管理员执行此操作。\n"
        "<i>\"解散后无法恢复，请谨慎操作喵！\"</i>",
        parse_mode='HTML'
    )


# ==========================================
# 返回主界面
# ==========================================

async def guild_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """返回公会主界面"""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    fake_update = type('Update', (), {
        'effective_message': query.message,
        'effective_user': query.from_user,
    })()
    await guild_main(fake_update, context)


# ==========================================
# 注册模块
# ==========================================

def register(app):
    app.add_handler(CommandHandler("guild", guild_main))
    app.add_handler(CommandHandler("guilds", guild_main))

    # 回调处理
    app.add_handler(CallbackQueryHandler(guild_create_start, pattern="^guild_create$"))
    app.add_handler(CallbackQueryHandler(guild_rank, pattern="^guild_rank$"))
    app.add_handler(CallbackQueryHandler(guild_leave, pattern=r"^guild_leave_\d+$"))
    app.add_handler(CallbackQueryHandler(guild_disband, pattern=r"^guild_disband_\d+$"))
    app.add_handler(CallbackQueryHandler(guild_back, pattern="^guild_back$"))
