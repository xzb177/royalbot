"""
战力突破系统 - Breakthrough System
- 消耗 MP 进行战力突破，获得永久属性加成
- 10 个突破等级，每个等级需要不同数量的 MP
- 突破成功后获得战力加成和特殊称号
- VIP 用户享受突破优惠
"""
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding
from utils import reply_with_auto_delete, edit_with_auto_delete

logger = logging.getLogger(__name__)


# ==========================================
# 战力突破配置
# ==========================================

# 突破等级配置 (0-10级)
BREAKTHROUGH_LEVELS = {
    1: {
        "name": "初窥门径",
        "cost": 500,
        "power_bonus": 50,
        "emoji": "🌱",
        "desc": "迈出魔法修炼的第一步",
        "title": "见习魔法师"
    },
    2: {
        "name": "渐入佳境",
        "cost": 1000,
        "power_bonus": 100,
        "emoji": "🌿",
        "desc": "开始掌握魔法的基本要领",
        "title": "正式魔法师"
    },
    3: {
        "name": "炉火纯青",
        "cost": 2000,
        "power_bonus": 200,
        "emoji": "🔥",
        "desc": "魔法运用自如，威力大增",
        "title": "高级魔法师"
    },
    4: {
        "name": "登堂入室",
        "cost": 4000,
        "power_bonus": 350,
        "emoji": "⚡",
        "desc": "进入高阶魔法的殿堂",
        "title": "魔导士"
    },
    5: {
        "name": "出神入化",
        "cost": 8000,
        "power_bonus": 500,
        "emoji": "💫",
        "desc": "魔法已臻化境",
        "title": "大魔导士"
    },
    6: {
        "name": "融会贯通",
        "cost": 15000,
        "power_bonus": 750,
        "emoji": "🌟",
        "desc": "融通各类魔法精髓",
        "title": "魔法宗师"
    },
    7: {
        "name": "超凡入圣",
        "cost": 30000,
        "power_bonus": 1000,
        "emoji": "✨",
        "desc": "超越凡人，踏入圣境",
        "title": "魔道圣者"
    },
    8: {
        "name": "法相天地",
        "cost": 50000,
        "power_bonus": 1500,
        "emoji": "🌌",
        "desc": "魔法与天地同辉",
        "title": "法相天尊"
    },
    9: {
        "name": "万法归一",
        "cost": 100000,
        "power_bonus": 2000,
        "emoji": "🌠",
        "desc": "万般魔法，归于本源",
        "title": "万法之主"
    },
    10: {
        "name": "破碎虚空",
        "cost": 200000,
        "power_bonus": 3000,
        "emoji": "🌈",
        "desc": "突破虚空，达到终极境界",
        "title": "虚空主宰"
    }
}

# 突破概率配置
BREAKTHROUGH_CHANCE = {
    "normal": 0.5,      # 普通突破成功率 50%
    "vip": 0.1,         # VIP 每级额外 +10%
    "max": 0.95         # 最大成功率 95%
}

# 失败补偿（返还消耗的百分比）
FAILURE_REFUND = 0.3  # 失败返还 30%


# ==========================================
# 工具函数
# ==========================================

def get_breakthrough_cost(level: int, is_vip: bool = False) -> int:
    """获取突破所需 MP"""
    if level >= 10:
        return 0  # 已满级
    base_cost = BREAKTHROUGH_LEVELS[level + 1]["cost"]
    return int(base_cost * 0.7) if is_vip else base_cost


def get_breakthrough_success_rate(level: int, is_vip: bool = False) -> float:
    """获取突破成功率"""
    base_chance = BREAKTHROUGH_CHANCE["normal"]
    # 等级越高，成功率越低
    level_penalty = level * 0.03  # 每级 -3%
    final_chance = base_chance - level_penalty
    if is_vip:
        final_chance += BREAKTHROUGH_CHANCE["vip"]
    return max(0.1, min(final_chance, BREAKTHROUGH_CHANCE["max"]))


def get_breakthrough_progress_bar(current: int, total: int) -> str:
    """获取突破进度条"""
    if total == 0:
        return "⚪" * 10
    filled = int((current / total) * 10)
    return "🔥" * filled + "⚪" * (10 - filled)


def get_total_power_bonus(user: UserBinding) -> int:
    """获取突破带来的总战力加成"""
    level = user.breakthrough_level or 0
    total_bonus = 0
    for i in range(1, level + 1):
        if i in BREAKTHROUGH_LEVELS:
            total_bonus += BREAKTHROUGH_LEVELS[i]["power_bonus"]
    return total_bonus


def get_next_level_info(level: int) -> dict:
    """获取下一级突破信息"""
    if level >= 10:
        return None
    return BREAKTHROUGH_LEVELS[level + 1]


# ==========================================
# 突破命令
# ==========================================

async def breakthrough_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """战力突破主界面"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user or not user.emby_account:
            await reply_with_auto_delete(msg, "💔 <b>请先绑定账号喵！</b>\n\n使用 <code>/bind 账号</code> 绑定后再来突破。")
            return

        level = user.breakthrough_level or 0
        exp = user.breakthrough_exp or 0
        total_spent = user.total_mp_spent_breakthrough or 0
        is_vip = user.is_vip or False
        points = user.points or 0

        # 计算总战力加成
        power_bonus = get_total_power_bonus(user)
        current_attack = user.attack or 0

        # 获取下一级信息
        next_level = get_next_level_info(level)
        success_rate = get_breakthrough_success_rate(level, is_vip) * 100
        next_cost = get_breakthrough_cost(level, is_vip) if next_level else 0

        # 构建显示文本
        lines = [
            "⚔️ <b>【 战 力 突 破 系 统 】</b>",
            "━━━━━━━━━━━━━━━━━━",
            f"👤 <b>魔法师：</b> {update.effective_user.first_name or '神秘人'}",
            f"🏆 <b>当前突破：</b> {level}/10 {BREAKTHROUGH_LEVELS.get(level, {}).get('emoji', '⚪')}",
        ]

        if level > 0:
            current_info = BREAKTHROUGH_LEVELS.get(level, {})
            lines.extend([
                f"📜 <b>当前境界：</b> {current_info.get('emoji', '')} <b>{current_info.get('name', '未知')}</b>",
                f"🎖️ <b>获得称号：</b> {current_info.get('title', '无')}",
            ])

        lines.extend([
            f"",
            f"⚡ <b>突破战力：</b> +{power_bonus}",
            f"🗡️ <b>总战力：</b> {current_attack + power_bonus} (基础{current_attack} + 突破{power_bonus})",
            f"",
            f"💰 <b>当前余额：</b> {points} MP",
            f"💸 <b>累计消耗：</b> {total_spent} MP",
        ])

        if next_level:
            lines.extend([
                "",
                "━━━━━━━━━━━━━━━━━━",
                f"🎯 <b>下一突破：</b> {next_level['emoji']} <b>{next_level['name']}</b>",
                f"📖 <b>境界描述：</b> {next_level['desc']}",
                f"🎖️ <b>获得称号：</b> {next_level['title']}",
                f"⚡ <b>战力加成：</b> +{next_level['power_bonus']}",
                f"💰 <b>突破消耗：</b> {next_cost} MP {'👑VIP专享7折' if is_vip else ''}",
                f"🎲 <b>成功概率：</b> <code>{success_rate:.1f}%</code>",
            ])
        else:
            lines.extend([
                "",
                "━━━━━━━━━━━━━━━━━━",
                "🌈 <b>已达最高境界！</b>",
                "您是传说中的虚空主宰！"
            ])

        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━",
            "<i>\"突破自我，超越极限！\"</i>"
        ])

        # 构建按钮
        buttons = []
        if next_level:
            if points >= next_cost:
                buttons.append([
                    InlineKeyboardButton(f"⚔️ 开始突破 ({next_cost} MP)", callback_data="bt_start")
                ])
            else:
                buttons.append([
                    InlineKeyboardButton(f"💸 魔力不足 (需 {next_cost} MP)", callback_data="bt_no_funds")
                ])

        buttons.append([
            InlineKeyboardButton("📊 突破说明", callback_data="bt_help"),
            InlineKeyboardButton("🔙 返回", callback_data="bt_back")
        ])

        await msg.reply_html(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def breakthrough_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """执行战力突破"""
    query = update.callback_query
    if not query:
        return

    await query.answer("⚔️ 突破中...")

    user_id = query.from_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user or not user.emby_account:
            await query.edit_message_text("💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        level = user.breakthrough_level or 0
        is_vip = user.is_vip or False

        # 检查是否已满级
        if level >= 10:
            await query.edit_message_text("🌈 <b>您已达最高境界！</b>\n\n无需再突破喵~", parse_mode='HTML')
            return

        # 获取突破信息
        next_level = get_next_level_info(level)
        cost = get_breakthrough_cost(level, is_vip)
        success_rate = get_breakthrough_success_rate(level, is_vip)

        # 检查余额
        if user.points < cost:
            await query.edit_message_text(
                f"💸 <b>魔力不足喵！</b>\n\n"
                f"突破需要 <b>{cost}</b> MP\n"
                f"当前余额：<b>{user.points}</b> MP",
                parse_mode='HTML'
            )
            return

        # 扣除消耗
        user.points -= cost
        user.total_mp_spent_breakthrough = (user.total_mp_spent_breakthrough or 0) + cost

        # 判断是否成功
        is_success = random.random() < success_rate
        user.breakthrough_exp = (user.breakthrough_exp or 0) + 1

        if is_success:
            # 突破成功
            level_info = next_level
            user.breakthrough_level = level + 1
            user.attack = (user.attack or 0) + level_info["power_bonus"]

            result_text = (
                f"🎉 <b>突 破 成 功 ！</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✨ <b>突破特效</b> ✨\n"
                f"{level_info['emoji']} {level_info['emoji']} {level_info['emoji']}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🎖️ <b>获得称号：</b> {level_info['title']}\n"
                f"🌟 <b>当前境界：</b> {level_info['name']}\n"
                f"⚡ <b>战力提升：</b> +{level_info['power_bonus']}\n"
                f"🗡️ <b>当前战力：</b> {user.attack}\n"
                f"💰 <b>剩余魔力：</b> {user.points} MP\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>\"{level_info['desc']}\"</i>"
            )

            # 检查成就
            from plugins.achievement import check_and_award_achievement
            ach_result = check_and_award_achievement(user, f"breakthrough_{level + 1}", session)
            if ach_result["new"]:
                result_text += f"\n\n🏆 {ach_result['emoji']} {ach_result['name']} (+{ach_result['reward']}MP)"
                user.points += ach_result["reward"]

            session.commit()

            # 追踪任务
            from plugins.unified_mission import track_and_check_task
            await track_and_check_task(user_id, "breakthrough")

        else:
            # 突破失败，返还部分消耗
            refund = int(cost * FAILURE_REFUND)
            user.points += refund

            result_text = (
                f"💔 <b>突 破 失 败 ...</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🌫️ 魔法能量消散了...\n"
                f"💰 <b>返还魔力：</b> +{refund} MP (30%)\n"
                f"📊 <b>累计尝试：</b> {user.breakthrough_exp} 次\n"
                f"🎲 <b>当前成功率：</b> <code>{success_rate * 100:.1f}%</code>\n"
                f"💵 <b>剩余魔力：</b> {user.points} MP\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>\"不要气馁！再试一次吧！\"</i>"
            )

            session.commit()

        # 构建按钮
        buttons = []
        if level < 10:
            new_cost = get_breakthrough_cost(user.breakthrough_level or 0, is_vip)
            if user.points >= new_cost:
                buttons.append([
                    InlineKeyboardButton(f"🔄 继续突破 ({new_cost} MP)", callback_data="bt_start")
                ])
            else:
                buttons.append([
                    InlineKeyboardButton(f"💸 魔力不足", callback_data="bt_no_funds")
                ])

        buttons.append([
            InlineKeyboardButton("🔙 返回", callback_data="bt_back")
        ])

        await query.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )


async def breakthrough_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """突破说明"""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    help_text = (
        "📖 <b>【 战 力 突 破 说 明 】</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⚔️ <b>系统介绍：</b>\n"
        "   消耗 MP 进行战力突破，获得永久属性加成！\n\n"
        "📊 <b>突破等级：</b>\n"
        "   共 10 个突破等级，每个等级提供不同的战力加成\n\n"
        "🎲 <b>成功概率：</b>\n"
        "   • 基础成功率 50%\n"
        "   • 每级成功率降低 3%\n"
        "   • VIP 用户额外 +10% 成功率\n"
        "   • 最低成功率 10%，最高 95%\n\n"
        "💰 <b>失败返还：</b>\n"
        "   突破失败返还 30% 消耗的 MP\n\n"
        "👑 <b>VIP 优惠：</b>\n"
        "   VIP 用户突破消耗享受 7 折优惠！\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "<i>\"突破自我，超越极限！\"</i>"
    )

    await query.edit_message_text(
        help_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 返回", callback_data="bt_back")]
        ]),
        parse_mode='HTML'
    )


async def breakthrough_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """返回突破主界面"""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    # 创建伪造的 update 调用 breakthrough_main
    fake_update = type('Update', (), {
        'effective_message': query.message,
        'effective_user': query.from_user,
    })()
    await breakthrough_main(fake_update, context)


async def breakthrough_no_funds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """魔力不足提示"""
    query = update.callback_query
    if not query:
        return

    await query.answer("💸 魔力不足！", show_alert=True)


# ==========================================
# 注册模块
# ==========================================

def register(app):
    app.add_handler(CommandHandler("breakthrough", breakthrough_main))
    app.add_handler(CallbackQueryHandler(breakthrough_start, pattern="^bt_start$"))
    app.add_handler(CallbackQueryHandler(breakthrough_help, pattern="^bt_help$"))
    app.add_handler(CallbackQueryHandler(breakthrough_back, pattern="^bt_back$"))
    app.add_handler(CallbackQueryHandler(breakthrough_no_funds, pattern="^bt_no_funds$"))
