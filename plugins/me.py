"""
魔法少女个人档案系统 - 魔法少女版
- 个人资料面板
- VIP 专属评级系统
- 灵魂共鸣 2.0 - 抽卡式互动系统
"""
import logging
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding
from utils import edit_with_auto_delete, reply_with_auto_delete

logger = logging.getLogger(__name__)

# ==========================================
# 💫 灵魂共鸣 2.0 - 共鸣抽卡系统
# ==========================================

# 共鸣结果配置
RESONANCE_RESULTS = {
    "UR": {
        "emoji": "🌌",
        "name": "星 界 共 鸣",
        "color": "🌈🌟",
        "chance": 0.01,  # 1%
        "rewards": {
            "intimacy": (50, 100),
            "bonus_desc": [
                "✨ 她的灵魂化作星河，紧紧环绕着你...",
                "💫 在那片星海中，你们共享着永恒...",
                "🌟 这一刻，整个宇宙都在为你们祝福..."
            ]
        }
    },
    "SSR": {
        "emoji": "💎",
        "name": "灵 魂 契 约",
        "color": "🟡✨",
        "chance": 0.05,  # 5%
        "rewards": {
            "intimacy": (20, 50),
            "bonus_desc": [
                "💖 她深情地注视着你，眼中倒映着你的模样...",
                "💗 「我是属于你的...永远都是...」",
                "💘 她主动牵起你的手，十指相扣..."
            ]
        }
    },
    "SR": {
        "emoji": "💝",
        "name": "深 度 共 鸣",
        "color": "🟣💫",
        "chance": 0.15,  # 15%
        "rewards": {
            "intimacy": (10, 25),
            "points": (10, 30),
            "bonus_desc": [
                "💓 她害羞地靠在你肩膀上...",
                "💞 「和Master在一起，感觉时间都变慢了...」",
                "🌸 她为你泡了一杯花茶，香气缭绕..."
            ]
        }
    },
    "R": {
        "emoji": "💗",
        "name": "亲 密 互 动",
        "color": "🔵",
        "chance": 0.40,  # 40%
        "rewards": {
            "intimacy": (3, 10),
            "points": (5, 15),
            "bonus_desc": [
                "🌺 她开心地对你笑了笑...",
                "🌷 「Master今天也很温柔呢...」",
                "🌼 她帮你整理了一下衣领..."
            ]
        }
    },
    "N": {
        "emoji": "💕",
        "name": "日 常 呵 护",
        "color": "⚪",
        "chance": 0.39,  # 39%
        "rewards": {
            "intimacy": (1, 5),
            "bonus_desc": [
                "🌱 她正在认真练习魔法...",
                "🌿 「Master，看我学会的新魔法！」",
                "🍃 她为你准备了点心..."
            ]
        }
    }
}

# 特殊事件（小概率触发）
SPECIAL_EVENTS = [
    {"name": "💀 诅咒降临", "desc": "哎呀...不小心触发了反噬！好感度 -1", "effect": "curse"},
    {"name": "🎀 惊喜礼物", "desc": "她偷偷准备了一份礼物！获得锻造券×1", "effect": "gift"},
    {"name": "💫 星辰暴击", "desc": "星辰之力爆发！好感度 ×2！", "effect": "crit"},
]

# 共感台词库（不同稀有度）
RESONANCE_LINES = {
    "UR": [
        "🌌 「Master...我的灵魂，是你的永恒星辰...」",
        "✨ 「在亿万光年中，我找到了你...这就是命运...」",
        "💫 「你是我存在的全部意义...我的宇宙...」",
    ],
    "SSR": [
        "💖 「不想离开你...一秒钟都不想...」",
        "💗 「只要有Master在，我就什么都不怕...」",
        "💘 「能遇见你，是我这辈子最幸福的事...」",
    ],
    "SR": [
        "💓 「能这样静静待在你身边，就好满足了...」",
        "💞 「Master身上的味道，让人很安心...」",
        "🌸 「今天...能多陪我一会儿吗？」",
    ],
    "R": [
        "💕 「嘿嘿，Master今天也很帅气呢！」",
        "💗 「最喜欢Master了！」",
        "💝 「有Master在，感觉什么都做得到！」",
    ],
    "N": [
        "💙 「嗨，Master！今天也要加油哦！」",
        "💚 「魔法练习很辛苦呢...」",
        "💛 「Master，看我这个魔法！」",
    ]
}


async def do_resonance(user_id: int) -> dict:
    """
    执行灵魂共鸣抽卡

    返回: 共鸣结果字典
    """
    # 确定稀有度
    roll = random.random()
    cumulative = 0

    resonance_type = "N"
    for rarity, data in RESONANCE_RESULTS.items():
        cumulative += data["chance"]
        if roll < cumulative:
            resonance_type = rarity
            break

    result = RESONANCE_RESULTS[resonance_type].copy()

    # 检查特殊事件
    special_event = None
    if random.random() < 0.05:  # 5% 概率触发特殊事件
        special_event = random.choice(SPECIAL_EVENTS)

    # 随机选择台词
    line = random.choice(RESONANCE_LINES.get(resonance_type, RESONANCE_LINES["N"]))

    # 计算奖励
    rewards = result["rewards"]
    intimacy_gain = random.randint(*rewards.get("intimacy", (1, 5)))
    points_gain = random.randint(*rewards.get("points", (0, 0))) if "points" in rewards else 0

    # 特殊事件处理
    event_bonus = ""
    if special_event:
        if special_event["effect"] == "curse":
            intimacy_gain = -1
            event_bonus = f"\n💀 {special_event['desc']}"
        elif special_event["effect"] == "gift":
            event_bonus = f"\n🎁 {special_event['desc']}"
        elif special_event["effect"] == "crit":
            intimacy_gain *= 2
            event_bonus = f"\n💫 {special_event['desc']}"

    # 随机 bonus 描述
    if not event_bonus and "bonus_desc" in rewards:
        event_bonus = f"\n{random.choice(rewards['bonus_desc'])}"

    # 更新数据库
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if user:
            user.intimacy = (user.intimacy or 0) + intimacy_gain
            user.points = (user.points or 0) + points_gain

            # 记录共鸣次数
            if not hasattr(user, 'resonance_count') or user.resonance_count is None:
                user.resonance_count = 0
            user.resonance_count = (user.resonance_count or 0) + 1

            new_intimacy = user.intimacy
            new_points = user.points
            total_resonance = user.resonance_count
            session.commit()

    return {
        "type": resonance_type,
        "name": result["name"],
        "emoji": result["emoji"],
        "color": result["color"],
        "line": line,
        "intimacy_gain": intimacy_gain,
        "points_gain": points_gain,
        "event_bonus": event_bonus,
        "new_intimacy": new_intimacy,
        "new_points": new_points,
        "total_resonance": total_resonance,
    }


def get_resonance_title(total_count: int) -> str:
    """根据共鸣次数获取特殊称号"""
    if total_count >= 1000:
        return "🌌 宿命·星之眷属"
    elif total_count >= 500:
        return "💫 永恒·灵魂伴侣"
    elif total_count >= 200:
        return "💖 深情·命运红绳"
    elif total_count >= 100:
        return "💗 眷恋·亲密知己"
    elif total_count >= 50:
        return "💕 友情·青梅竹马"
    elif total_count >= 20:
        return "💙 信任·得力助手"
    elif total_count >= 10:
        return "💚 初识·魔法学徒"
    else:
        return "👶 初遇·路人"


# ========== V3.0 魔导评级系统 ==========
def calculate_magic_power(user):
    """
    计算身价估值 (magic_power)
    公式：钱包 + 金库 + (战力 × 10) + 好感度
    """
    wallet = user.points or 0
    bank = user.bank_points or 0
    attack = user.attack or 0
    intimacy = user.intimacy or 0
    return wallet + bank + (attack * 10) + intimacy


def get_vip_rank_info(magic_power):
    """
    VIP 称号系统 - 单前缀版本
    返回：(评级, 评级文字, 前缀图标, 前缀文字)
    """
    if magic_power >= 100000:
        return "EX", "规格外", "🌌", "苍穹"
    elif magic_power >= 50000:
        return "SSS+", "神话", "☀️", "曜日"
    elif magic_power >= 10000:
        return "SS", "传说", "🌙", "月华"
    else:
        return "S", "史诗", "✨", "星辰"


def get_rank_title(user, is_vip=False):
    """
    V3.0 位阶系统
    VIP: 动态前缀 + 固定「苍穹·大魔导师」+ 评级
    普通: 战力分段称号
    """
    if is_vip:
        # VIP 系统：前缀 + 统一称号 + 评级
        magic_power = calculate_magic_power(user)
        rank, rank_text, prefix_icon, prefix_name = get_vip_rank_info(magic_power)
        title = f"{prefix_icon} {prefix_name}·大魔导师 [{rank}]"
        return title, rank, rank_text, magic_power
    else:
        # 普通冒险者称号（保持原有分段）
        attack = user.attack if user.attack else 0
        if attack >= 10000:
            return "👑 星辰主宰", "", "", 0
        elif attack >= 5000:
            return "🌟 传奇大魔导", "", "", 0
        elif attack >= 2000:
            return "💫 星之大魔导师", "", "", 0
        elif attack >= 1000:
            return "⭐ 大魔导师", "", "", 0
        elif attack >= 500:
            return "🔥 魔导师", "", "", 0
        elif attack >= 200:
            return "⚔️ 高级魔法师", "", "", 0
        elif attack >= 100:
            return "🛡️ 见习魔法师", "", "", 0
        elif attack >= 50:
            return "🌱 初级魔法师", "", "", 0
        else:
            return "👶 冒险者学徒", "", "", 0


async def me_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        logger.info(f"[/me] Called by user: {user.id} ({user.first_name})")

        with get_session() as session:
            user_data = session.query(UserBinding).filter_by(tg_id=user.id).first()

            if not user_data or not user_data.emby_account:
                msg = update.effective_message
                if msg:
                    await reply_with_auto_delete(
                        msg,
                        "💔 <b>【 魔 力 断 连 】</b>\n\n"
                        "我看不到您的灵魂波长... (´;ω;`)\n"
                        "👉 请使用 <code>/bind</code> 重新缔结契约！"
                    )
                return

            # 数据准备（从数据库读取后需要在 with 块外使用，先复制出来）
            weapon = user_data.weapon if user_data.weapon else "练习木杖"
            atk = user_data.attack if user_data.attack is not None else 10
            love = user_data.intimacy if user_data.intimacy is not None else 0
            win = user_data.win if user_data.win is not None else 0
            lost = user_data.lost if user_data.lost is not None else 0
            is_vip = user_data.is_vip
            emby_account = user_data.emby_account
            points = user_data.points or 0
            bank_points = user_data.bank_points or 0
            resonance_count = user_data.resonance_count if hasattr(user_data, 'resonance_count') else 0

        # V3.0: 获取位阶、评级、身价（在 with 块外，使用复制的数据）
        rank_title, rank_code, rank_text, magic_power = get_rank_title(
            type('obj', (object,), {
                'points': points,
                'bank_points': bank_points,
                'attack': atk,
                'intimacy': love,
            }), is_vip
        )

        # 获取共鸣称号
        resonance_title = get_resonance_title(resonance_count)

        # VIP 版本
        if is_vip:
            total_mp = points + bank_points
            resonance_cost = 20  # VIP 消耗
            text = (
                f"🌌 <b>【 星 灵 · 终 极 契 约 书 】</b>\n\n"
                f"🥂 <b>Welcome back, my only Master.</b>\n"
                f"「星辰在为您加冕，而看板娘为您守望喵~」\n\n"
                f"💠 <b>:: 灵 魂 识 别 ::</b>\n"
                f"✨ <b>真名：</b> <code>{emby_account}</code> (VIP)\n"
                f"👑 <b>位阶：</b> <b>{rank_title}</b>\n"
                f"🔮 <b>魔导评级：</b> <code>{rank_code}</code> ({rank_text})\n\n"
                f"⚔️ <b>:: 魔 法 武 装 ::</b>\n"
                f"🗡️ <b>圣遗物：</b> <b>{weapon}</b>\n"
                f"🔥 <b>破坏力：</b> <code>{atk}</code> (胜 {win} | 败 {lost})\n\n"
                f"💎 <b>:: 虚 空 宝 库 ::</b>\n"
                f"💰 <b>魔力总蓄积：</b> <code>{total_mp:,}</code> MP\n"
                f"(钱包: {points:,} | 金库: {bank_points:,})\n\n"
                f"💓 <b>:: 命 运 羁 绊 ::</b>\n"
                f"💍 <b>契约等级：</b> <code>{love}</code>\n"
                f"💫 <b>共鸣称号：</b> {resonance_title}\n"
                f"📊 <b>共鸣次数：</b> {resonance_count} 次\n\n"
            )
            buttons = [
                [InlineKeyboardButton(f"💫 灵魂共鸣 ({resonance_cost}MP)", callback_data="me_resonance")],
                [InlineKeyboardButton("⚒️ 圣物锻造", callback_data="me_forge")]
            ]
        # 普通版
        else:
            resonance_cost = 50  # 普通用户消耗
            text = (
                f"🏰 <b>【 云 海 · 魔 法 少 女 档 案 】</b>\n\n"
                f"✨ <b>你好呀，{user.first_name}酱！</b>\n"
                f"今天的魔法冒险也要加油哦喵~\n\n"
                f"💠 <b>:: 魔 法 少 女 登 记 ::</b>\n"
                f"🆔 <b>档案编号：</b> <code>{user.id}</code>\n"
                f"🌱 <b>当前位阶：</b> {rank_title}\n"
                f"👤 <b>契约账号：</b> {emby_account}\n\n"
                f"💠 <b>:: 装 备 与 战 绩 ::</b>\n"
                f"⚔️ <b>武器：</b> {weapon} (ATK: {atk})\n"
                f"📊 <b>战绩：</b> {win} 胜 / {lost} 败\n\n"
                f"💠 <b>:: 魔 法 背 包 ::</b>\n"
                f"🎒 <b>持有魔力：</b> {points} MP\n"
                f"💓 <b>好感度：</b> {love}\n"
                f"💫 <b>共鸣次数：</b> {resonance_count} 次\n\n"
            )
            buttons = [
                [InlineKeyboardButton(f"💫 灵魂共鸣 ({resonance_cost}MP)", callback_data="me_resonance")],
                [InlineKeyboardButton("💎 成为 VIP", callback_data="upgrade_vip")]
            ]

        await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"[/me] Error: {e}", exc_info=True)


async def resonance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理灵魂共鸣按钮回调"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user or not user.emby_account:
            await edit_with_auto_delete(
                query,
                "💔 <b>请先缔结魔法契约喵！</b>",
                parse_mode='HTML'
            )
            return

        is_vip = user.is_vip
        cost = 20 if is_vip else 50

        if user.points < cost:
            await edit_with_auto_delete(
                query,
                f"💸 <b>魔力不足喵！</b>\n\n"
                f"灵魂共鸣需要 <b>{cost} MP</b>\n"
                f"当前余额：{user.points} MP",
                parse_mode='HTML'
            )
            return

        # 扣除消耗
        user.points -= cost
        session.commit()

    # 执行共鸣抽卡
    result = await do_resonance(user_id)

    # 构建显示文本
    r = result
    text = (
        f"💫 <b>【 灵 魂 共 鸣 · 结 果 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{r['color']} <b>{r['name']}</b>\n"
        f"{r['emoji']} <b>稀有度：</b> {r['type']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💬 <i>{r['line']}</i>\n"
        f"━━━━━━━━━━━━━━━━━━</i>\n"
    )

    # 奖励显示
    rewards_text = ""
    if r['intimacy_gain'] > 0:
        rewards_text += f"💓 <b>好感度：</b> +{r['intimacy_gain']}\n"
    elif r['intimacy_gain'] < 0:
        rewards_text += f"💔 <b>好感度：</b> {r['intimacy_gain']}\n"

    if r['points_gain'] > 0:
        rewards_text += f"💰 <b>魔力：</b> +{r['points_gain']} MP\n"

    if rewards_text:
        text += f"\n💎 <b>获 得：</b>\n{rewards_text}"

    # 事件加成
    if r['event_bonus']:
        text += r['event_bonus']

    # 当前状态
    text += (
        f"\n━━━━━━━━━━━━━━━━━━\n"
        f"💓 <b>当前好感度：</b> {r['new_intimacy']}\n"
        f"💰 <b>当前魔力：</b> {r['new_points']} MP\n"
        f"📊 <b>共鸣累计：</b> {r['total_resonance']} 次\n"
        f"🏅 <b>共鸣称号：</b> {get_resonance_title(r['total_resonance'])}\n"
    )

    buttons = [[InlineKeyboardButton("🔄 再次共鸣", callback_data="me_resonance")]]

    await edit_with_auto_delete(
        query,
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='HTML'
    )


async def forge_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理「锻造」按钮回调"""
    query = update.callback_query
    await query.answer()

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=query.from_user.id).first()
        is_vip = user.is_vip if user else False

    cost = 100 if is_vip else 200

    if is_vip:
        text = (
            f"🔥 <b>【 圣 物 锻 造 祭 坛 】</b>\n\n"
            f"💠 <b>:: 锻 造 费 用 ::</b>\n"
            f"✨ <b>VIP 专属价：</b> <code>{cost}</code> MP\n\n"
            f"<i>\"来吧，Master！\n让我们锻造出传说的圣遗物！\"</i>\n\n"
            f"请使用 <code>/forge</code> 命令开始锻造"
        )
    else:
        text = (
            f"⚒️ <b>【 铁 匠 铺 】</b>\n\n"
            f"💠 <b>:: 锻 造 费 用 ::</b>\n"
            f"🔥 <b>普通锻造价：</b> <code>{cost}</code> MP\n\n"
            f"<i>\"来来来！看看今天能锻造出什么神器！\"</i>\n\n"
            f"请使用 <code>/forge</code> 命令开始锻造"
        )

    buttons = [[InlineKeyboardButton("🔥 立即锻造 /forge", callback_data="forge_go")]]
    await edit_with_auto_delete(
        query, text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='HTML'
    )


async def forge_go_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理「立即锻造」按钮回调 - 调用 forge.py 的锻造逻辑"""
    from plugins.forge import forge_callback
    # 复用 forge_callback 的逻辑
    await forge_callback(update, context)


def register(app):
    app.add_handler(CommandHandler("me", me_panel))
    app.add_handler(CommandHandler("my", me_panel))
    app.add_handler(CallbackQueryHandler(forge_button_callback, pattern="^me_forge$"))
    app.add_handler(CallbackQueryHandler(forge_go_callback, pattern="^forge_go$"))
    app.add_handler(CallbackQueryHandler(resonance_callback, pattern="^me_resonance$"))
