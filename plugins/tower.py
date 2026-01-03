"""
通天塔系统 - 无限爬塔打怪
- 无限层数挑战
- 难度递增系统
- 每层奖励
- 历史最高记录
- 任务系统集成
- 成就系统集成
"""
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding
from utils import reply_with_auto_delete

logger = logging.getLogger(__name__)


# 导入活动追踪和成就检查函数
async def track_activity_wrapper(user_id: int, activity_type: str):
    """包装函数，延迟导入避免循环依赖"""
    from plugins.unified_mission import track_and_check_task
    await track_and_check_task(user_id, activity_type)


async def check_achievements_wrapper(user: UserBinding, session=None, context=None, chat_id=None):
    """包装函数，检查成就并支持广播"""
    from plugins.achievement import check_all_achievements
    return check_all_achievements(user, session, context, chat_id)

# ==========================================
# 🗼 通天塔配置
# ==========================================

# 怪物名称库
MONSTER_NAMES = [
    "史莱姆", "哥布林", "骷髅兵", "僵尸", "蝙蝠",
    "狼人", "半兽人", "兽人战士", "食人魔", "巨魔",
    "石像鬼", "地狱犬", "牛头怪", "暗影刺客", "血骑士",
    "骨龙", "恶魔领主", "炎魔", "巫妖", "塔灵",
    "深渊巨口", "虚空行者", "末日使者", "灭世魔", "塔之主"
]

# 怪物前缀（增加多样性）
MONSTER_PREFIX = [
    "狂暴的", "变异的", "被诅咒的", "古老的", "强大的",
    "凶残的", "狂乱的", "暗影", "血腥", "恐怖的"
]

# Boss名称（每10层）
BOSS_NAMES = [
    "👹 守塔魔像", "🐉 地狱炎龙", "💀 死亡骑士", "👿 深渊领主",
    "🌑 虚空大君", "🔥 灭世魔神", "⚡ 雷霆之主", "🌊 冰霜女皇",
    "🌪 混沌之眼", "💫 塔之主宰"
]


def get_monster(floor: int) -> dict:
    """
    获取指定层级的怪物信息

    怪物战力 = 玩家基准战力 × (1 + 层数 × 0.15)
    怪物血量 = 基础血量 × (1 + 层数 × 0.1)
    """
    # 每10层是Boss
    is_boss = floor % 10 == 0
    boss_level = floor // 10

    if is_boss:
        boss_idx = min(boss_level - 1, len(BOSS_NAMES) - 1)
        name = BOSS_NAMES[boss_idx]
        # Boss 更强
        power_multiplier = 1.2 + (floor * 0.18)
        hp_multiplier = 1.5 + (floor * 0.15)
        is_boss = True
    else:
        prefix = random.choice(MONSTER_PREFIX)
        base_name = random.choice(MONSTER_NAMES[:min(10 + floor // 5, len(MONSTER_NAMES))])
        name = f"{prefix}{base_name}"
        power_multiplier = 0.8 + (floor * 0.12)
        hp_multiplier = 1.0 + (floor * 0.1)
        is_boss = False

    return {
        "name": name,
        "floor": floor,
        "is_boss": is_boss,
        "power_multiplier": power_multiplier,
        "hp_multiplier": hp_multiplier,
    }


def calculate_battle_result(user, monster: dict) -> dict:
    """
    计算战斗结果

    基于玩家战力、武器、随机因素计算胜率
    返回：(是否胜利, 战斗详情, 获得的奖励)
    """
    user_attack = user.attack or 10
    user_weapon = user.weapon or "练习木杖"
    user_intimacy = user.intimacy or 0

    # 计算玩家综合战力
    total_power = user_attack + (user_intimacy // 10)

    # 怪物战力（基于玩家战力计算）
    base_monster_power = total_power * monster["power_multiplier"]
    monster_power = max(10, int(base_monster_power))

    # 计算胜率（有随机性）
    # 如果玩家战力远高于怪物，胜率接近100%
    # 如果玩家战力远低于怪物，胜率接近0%
    power_ratio = total_power / monster_power if monster_power > 0 else 1.0

    # 随机因素 ±20%
    random_factor = random.uniform(0.8, 1.2)
    win_rate = min(0.95, max(0.05, power_ratio * random_factor))

    # 判定胜负
    is_win = random.random() < win_rate

    # 计算奖励
    floor = monster["floor"]
    if is_win:
        # 基础奖励
        base_reward = 10 + (floor * 2)
        mp_reward = int(base_reward * (1.5 if user.is_vip else 1))
        attack_bonus = random.randint(1, 3) if random.random() < 0.3 else 0

        # Boss奖励
        if monster["is_boss"]:
            mp_reward *= 3
            attack_bonus += random.randint(3, 10)
            if random.random() < 0.3:
                # 掉落锻造券
                forge_ticket = random.choice(["普通", "高级"])
            else:
                forge_ticket = None
        else:
            forge_ticket = None

        # 特殊层数奖励
        special_reward = ""
        if floor % 50 == 0:
            special_reward = f"\n🎁 <b>里程碑奖励：</b>锻造券(高级) ×1！"
            forge_ticket = "高级"
        elif floor % 25 == 0:
            special_reward = f"\n🎁 <b>里程碑奖励：</b>锻造券(普通) ×1！"
            if not forge_ticket:
                forge_ticket = "普通"
        elif floor % 10 == 0:
            if random.random() < 0.5:
                special_reward = f"\n🎁 <b>惊喜掉落：</b>锻造券！"
                forge_ticket = random.choice(["普通", "高级"])

    else:
        mp_reward = 0
        attack_bonus = 0
        forge_ticket = None
        special_reward = ""

    # 战斗详情
    if is_win:
        damage_dealt = random.randint(int(monster_power * 0.5), int(monster_power * 1.5))
        damage_taken = random.randint(0, int(total_power * 0.3))
        detail = f"⚔️ 你对怪物造成了 <b>{damage_dealt}</b> 点伤害"
        if damage_taken > 0:
            detail += f"\n🛡️ 受到了 <b>{damage_taken}</b> 点伤害"
    else:
        damage_dealt = random.randint(int(total_power * 0.3), int(total_power * 0.8))
        damage_taken = random.randint(int(monster_power * 0.5), int(monster_power * 1.2))
        detail = f"💔 你对怪物造成了 <b>{damage_dealt}</b> 点伤害（不够！）"
        detail += f"\n🩸 受到了 <b>{damage_taken}</b> 点伤害"

    return {
        "is_win": is_win,
        "mp_reward": mp_reward,
        "attack_bonus": attack_bonus,
        "forge_ticket": forge_ticket,
        "special_reward": special_reward,
        "detail": detail,
        "monster_power": monster_power,
    }


async def tower_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = getattr(update, "callback_query", None)
    msg = update.effective_message
    if not msg:
        return
    """通天塔主界面"""
    msg = update.effective_message
    query = update.callback_query if hasattr(update, 'callback_query') and update.callback_query else None

    if not msg and not query:
        return

    user_id = update.effective_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user or not user.emby_account:
            target = query.edit_message_text if query else msg.reply_html
            await target("💔 <b>请先绑定账号喵！</b>\n使用 <code>/bind</code> 缔结契约后再来挑战通天塔！")
            return

        # 获取通天塔数据
        current_floor = user.tower_current_floor or 0
        max_floor = user.tower_max_floor or 0
        total_wins = user.tower_total_wins or 0

        vip_badge = " 👑" if user.is_vip else ""
        attack = user.attack or 0

        # 构建界面
        if current_floor == 0:
            text = (
                f"🗼 <b>【 通 天 塔 · 入 口 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>挑战者：</b> {user.emby_account}{vip_badge}\n"
                f"⚔️ <b>战力：</b> {attack}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🏛️ <b>通天塔</b> 屹出不穷的魔物盘踞在塔中\n"
                f"   每10层遭遇强大的 <b>Boss</b>！\n\n"
                f"📊 <b>你的记录：</b>\n"
                f"   最高层数：{max_floor} 层\n"
                f"   击败怪物：{total_wins} 只\n\n"
                f"<i>\"准备好开始挑战了吗？\"</i>\n"
            )
            buttons = [
                [InlineKeyboardButton("⚔️ 开始挑战", callback_data="tower_enter")]
            ]
        else:
            # 继续挑战或查看当前进度
            monster = get_monster(current_floor)
            boss_mark = "👹 " if monster["is_boss"] else ""
            text = (
                f"🗼 <b>【 通 天 塔 · 第 {current_floor} 层 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>挑战者：</b> {user.emby_account}{vip_badge}\n"
                f"⚔️ <b>战力：</b> {attack}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{boss_mark}<b>怪物：</b> {monster['name']}\n"
                f"📊 <b>预估强度：</b> {int(monster['power_multiplier'] * 100)}% 基准\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>你的记录：</b>\n"
                f"   最高层数：{max_floor} 层\n"
                f"   击败怪物：{total_wins} 只\n\n"
            )
            buttons = [
                [InlineKeyboardButton("⚔️ 战斗！", callback_data="tower_fight"),
                 InlineKeyboardButton("🏠 返回入口", callback_data="tower_home")]
            ]

    # 发送/编辑消息
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
    else:
        await msg.reply_html(text, reply_markup=InlineKeyboardMarkup(buttons))


async def tower_enter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """进入通天塔"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user:
            await query.edit_message_text("💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        # 初始化通天塔进度
        if not user.tower_current_floor:
            user.tower_current_floor = 1
            user.tower_max_floor = 0
            user.tower_total_wins = 0
            session.commit()

        await tower_panel(update, context)


async def tower_fight_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """战斗回调"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user:
            await query.edit_message_text("💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        current_floor = user.tower_current_floor or 1
        monster = get_monster(current_floor)
        result = calculate_battle_result(user, monster)

        # 构建战斗结果
        if result["is_win"]:
            # 胜利
            user.points = (user.points or 0) + result["mp_reward"]
            user.attack = (user.attack or 0) + result["attack_bonus"]
            user.tower_current_floor = current_floor + 1
            user.tower_max_floor = max(user.tower_max_floor or 0, current_floor)
            user.tower_total_wins = (user.tower_total_wins or 0) + 1

            # 处理锻造券
            forge_msg = ""
            if result["forge_ticket"]:
                if result["forge_ticket"] == "高级":
                    user.free_forges_big = (user.free_forges_big or 0) + 1
                    forge_msg = f"\n🎁 <b>获得：</b>高级锻造券 ×1"
                else:
                    user.free_forges = (user.free_forges or 0) + 1
                    forge_msg = f"\n🎁 <b>获得：</b>锻造券 ×1"

            session.commit()

            # 追踪任务进度
            await track_activity_wrapper(user_id, "tower")
            # 检查成就（传入context和chat_id用于广播）
            from telegram import Chat
            chat_id = query.message.chat_id if query.message.chat.type != Chat.PRIVATE else None
            new_achievements = await check_achievements_wrapper(user, session, context, chat_id)
            if new_achievements:
                session.commit()
                # 在显示文本中加入成就提示
                ach_text = f"\n\n🎉 <b>新成就解锁！</b>\n"
                for ach in new_achievements:
                    ach_text += f"   {ach['emoji']} {ach['name']}\n"
                # 将成就信息添加到 special_reward
                result["special_reward"] = result.get("special_reward", "") + ach_text

            next_floor = current_floor + 1
            next_monster = get_monster(next_floor)
            next_boss = "👹 " if next_monster["is_boss"] else ""

            text = (
                f"🗼 <b>【 战 斗 胜 利 ！】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✨ 你击败了 <b>{monster['name']}</b>！\n"
                f"{result['detail']}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>获得奖励：</b>\n"
                f"   MP: +{result['mp_reward']}\n"
                f"   战力: +{result['attack_bonus']}"
                f"{forge_msg}"
                f"{result['special_reward']}"
                f"\n━━━━━━━━━━━━━━━━━━\n"
                f"🚀 <b>下一层：</b>第 {next_floor} 层\n"
                f"{next_boss}<b>怪物：</b> {next_monster['name']}\n"
            )
            buttons = [
                [InlineKeyboardButton("⚔️ 继续挑战", callback_data="tower_fight"),
                 InlineKeyboardButton("🏠 返回入口", callback_data="tower_home")]
            ]
        else:
            # 失败
            text = (
                f"💔 <b>【 战 斗 失 败 ！】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"☠️ 你被 <b>{monster['name']}</b> 击败了...\n"
                f"{result['detail']}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>\"不要放弃，再试一次！\"</i>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>当前层数：</b>第 {current_floor} 层\n"
                f"📊 <b>历史最高：</b>第 {user.tower_max_floor or 0} 层\n"
            )
            buttons = [
                [InlineKeyboardButton("🔄 再来一次", callback_data="tower_fight"),
                 InlineKeyboardButton("🏠 返回入口", callback_data="tower_home")]
            ]

        # 添加战力提升显示
        if result["attack_bonus"] > 0:
            text = (
                f"\n⬆️ <b>战力提升：</b>+{result['attack_bonus']}！\n"
                f"当前战力：<b>{user.attack}</b>\n\n"
            ) + text

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')


async def tower_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """返回入口"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if user:
            # 重置到入口状态
            user.tower_current_floor = 0
            session.commit()

    await tower_panel(update, context)


def register(app):
    app.add_handler(CommandHandler("tower", tower_panel))
    app.add_handler(CallbackQueryHandler(lambda u, c: tower_panel(u, c), pattern="^tower$"))  # 从菜单进入
    app.add_handler(CallbackQueryHandler(lambda u, c: tower_enter_callback(u, c), pattern="^tower_enter$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: tower_fight_callback(u, c), pattern="^tower_fight$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: tower_home_callback(u, c), pattern="^tower_home$"))
