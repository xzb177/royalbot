"""
魔法少女炼金系统 (Forge)
- 消耗 MP 锻造魔法武器，获得战力加成
- VIP 用户享受 5 折优惠
- 支持再来一次按钮
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete
import random


# 导入活动追踪函数
async def track_activity_wrapper(user_id: int, activity_type: str):
    """包装函数，延迟导入避免循环依赖"""
    from plugins.mission import track_activity
    await track_activity(user_id, activity_type)


# 词缀库：决定魔法武器的稀有度和名字
PREFIXES = [
    "破碎的", "生锈的", "练习用的", "普通的", "精良的",
    "稀有的", "史诗的", "传说的", "神话的", "被诅咒的",
    "真·", "极·", "终焉之", "创世的"
]
ELEMENTS = ["火焰", "冰霜", "雷霆", "暗影", "神圣", "虚空", "可爱", "用来做蛋糕的"]
TYPES = ["魔法杖", "魔导书", "法杖", "魔剑", "平底锅", "咸鱼", "魔法棒", "加特林", "圣剑"]


def _generate_weapon(boost_rarity=False):
    """生成随机魔法武器名称和战力

    Args:
        boost_rarity: 是否提升稀有度概率（大锻造锤）
    """
    # 高稀有度模式：提升好词缀概率
    if boost_rarity:
        # SSR/神器概率提升
        roll = random.random()
        if roll < 0.15:  # 15% 神器
            p = random.choice(["神话的", "终焉之", "创世的", "真·"])
        elif roll < 0.40:  # 25% 传说
            p = random.choice(["传说的", "极·"])
        elif roll < 0.60:  # 20% 史诗
            p = random.choice(["史诗的", "稀有的"])
        elif roll < 0.95:  # 35% 普通
            p = random.choice(["精良的", "普通的", "练习用的"])
        else:  # 5% 咸鱼
            p = "普通的"
    else:
        p = random.choice(PREFIXES)

    e = random.choice(ELEMENTS)
    t = random.choice(TYPES)
    name = f"{p}{e}{t}"

    # 战力计算
    base_atk = random.randint(10, 100)

    # 稀有度加成
    if "神话" in p or "终焉" in p or "创世" in p:
        base_atk += random.randint(500, 1000)
        rank = "🌈 <b>SSR (神器)</b>"
    elif "传说" in p or "真·" in p:
        base_atk += random.randint(200, 500)
        rank = "🟡 <b>SR (史诗)</b>"
    elif "咸鱼" in t:
        base_atk = 1
        rank = "🐟 <b>咸鱼</b>"
    else:
        rank = "⚪ <b>R (普通)</b>"

    return name, base_atk, rank


async def forge_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """锻造新的魔法武器"""
    msg = update.effective_message
    if not msg:
        return

    user = update.effective_user
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()

    if not u or not u.emby_account:
        await reply_with_auto_delete(msg, "👻 <b>请先 /bind 缔结魔法契约喵！</b>")
        session.close()
        return

    # 检查锻造券
    has_big_ticket = u.free_forges_big and u.free_forges_big > 0
    has_small_ticket = (not has_big_ticket) and u.free_forges and u.free_forges > 0

    base_cost = 200
    if has_big_ticket:
        cost = 0  # 大锻造锤免费
        boost_rarity = True
        used_ticket = "大锻造锤"
    elif has_small_ticket:
        cost = 0  # 小锻造锤免费
        boost_rarity = False
        used_ticket = "小锻造锤"
    else:
        cost = int(base_cost * 0.5) if u.is_vip else base_cost
        boost_rarity = False
        used_ticket = None

    if not used_ticket and u.points < cost:
        if u.is_vip:
            text = (
                f"⚒️ <b>【 皇 家 · 炼 金 工 坊 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔥 <b>魔法炉火熄灭了...</b>\n\n"
                f"魔力不足喵！锻造需要 <b>{cost} MP</b>~\n"
                f"当前余额：{u.points} MP\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>\"去签到攒点魔力再来吧 Master...(｡•́︿•̀｡)\"</i>"
            )
        else:
            text = (
                f"⚒️ <b>【 魔 法 学 院 · 炼 金 工 坊 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔥 <b>魔法炉火熄灭了...</b>\n\n"
                f"魔力不足喵！锻造需要 <b>{cost} MP</b>~\n"
                f"当前余额：{u.points} MP\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>💡 提示：VIP 锻造享受 <b>5 折</b> 优惠哦！</i>"
            )
        await reply_with_auto_delete(msg, text)
        session.close()
        return

    # 扣除费用或券
    if used_ticket == "大锻造锤":
        u.free_forges_big -= 1
    elif used_ticket == "小锻造锤":
        u.free_forges -= 1
    else:
        u.points -= cost

    # 生成魔法武器（如果使用大锻造锤则提升稀有度）
    new_name, base_atk, rank = _generate_weapon(boost_rarity=boost_rarity)

    # 旧装备信息
    old_weapon = u.weapon if u.weapon else "无"
    old_atk = u.attack if u.attack else 0

    # 更新装备
    u.weapon = new_name
    u.attack = base_atk
    await track_activity_wrapper(user.id, "forge")
    session.commit()

    vip_badge = " 👑" if u.is_vip else ""

    # 构建消耗文本
    if used_ticket:
        if used_ticket == "大锻造锤":
            cost_text = f"🎟️ 消耗：<b>{used_ticket}</b> (稀有度UP!)\n"
            remaining = u.free_forges_big
        else:
            cost_text = f"🎟️ 消耗：<b>{used_ticket}</b>\n"
            remaining = u.free_forges
        if remaining > 0:
            cost_text += f"📋 剩余券数：{remaining} 张\n"
    else:
        cost_text = f"🔥 消耗魔力：<b>-{cost} MP</b>\n"

    txt = (
        f"⚒️ <b>【 炼 金 成 功 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{cost_text}"
        f"👤 锻造者：{u.emby_account}{vip_badge}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🗑️ <b>替换旧物：</b> {old_weapon} (ATK: {old_atk})\n"
        f"✨ <b>获得新武器：</b> <b>{new_name}</b>\n"
        f"📊 <b>武器评级：</b> {rank}\n"
        f"⚔️ <b>战力评估：</b> <b>{base_atk}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"感受到了吗？这股涌动的魔法力量... Master 喜欢吗？(｡•̀ᴗ-)✧\"</i>"
    )

    buttons = [[InlineKeyboardButton("🔄 再来一次", callback_data="forge_again")]]
    await reply_with_auto_delete(msg, txt, reply_markup=InlineKeyboardMarkup(buttons))
    session.close()


async def forge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理锻造按钮回调"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()

    if not u or not u.emby_account:
        await query.edit_message_text("👻 <b>请先 /bind 缔结魔法契约喵！</b>", parse_mode='HTML')
        session.close()
        return

    # 检查锻造券
    has_big_ticket = u.free_forges_big and u.free_forges_big > 0
    has_small_ticket = (not has_big_ticket) and u.free_forges and u.free_forges > 0

    base_cost = 200
    if has_big_ticket:
        cost = 0  # 大锻造锤免费
        boost_rarity = True
        used_ticket = "大锻造锤"
    elif has_small_ticket:
        cost = 0  # 小锻造锤免费
        boost_rarity = False
        used_ticket = "小锻造锤"
    else:
        cost = int(base_cost * 0.5) if u.is_vip else base_cost
        boost_rarity = False
        used_ticket = None

    if not used_ticket and u.points < cost:
        await query.edit_message_text(
            f"🔥 <b>魔力不足喵！</b>\n\n"
            f"锻造需要 <b>{cost} MP</b>~\n"
            f"当前余额：{u.points} MP",
            parse_mode='HTML'
        )
        session.close()
        return

    # 扣除费用或券
    if used_ticket == "大锻造锤":
        u.free_forges_big -= 1
    elif used_ticket == "小锻造锤":
        u.free_forges -= 1
    else:
        u.points -= cost

    new_name, base_atk, rank = _generate_weapon(boost_rarity=boost_rarity)

    old_weapon = u.weapon if u.weapon else "无"
    old_atk = u.attack if u.attack else 0

    u.weapon = new_name
    u.attack = base_atk
    await track_activity_wrapper(user.id, "forge")
    session.commit()

    vip_badge = " 👑" if u.is_vip else ""

    # 构建消耗文本
    if used_ticket:
        if used_ticket == "大锻造锤":
            cost_text = f"🎟️ 消耗：<b>{used_ticket}</b> (稀有度UP!)\n"
            remaining = u.free_forges_big
        else:
            cost_text = f"🎟️ 消耗：<b>{used_ticket}</b>\n"
            remaining = u.free_forges
        if remaining > 0:
            cost_text += f"📋 剩余券数：{remaining} 张\n"
    else:
        cost_text = f"🔥 消耗魔力：<b>-{cost} MP</b>\n"

    txt = (
        f"⚒️ <b>【 炼 金 成 功 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{cost_text}"
        f"👤 锻造者：{u.emby_account}{vip_badge}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🗑️ <b>替换旧物：</b> {old_weapon} (ATK: {old_atk})\n"
        f"✨ <b>获得新武器：</b> <b>{new_name}</b>\n"
        f"📊 <b>武器评级：</b> {rank}\n"
        f"⚔️ <b>战力评估：</b> <b>{base_atk}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"感受到了吗？这股涌动的魔法力量... Master 喜欢吗？(｡•̀ᴗ-)✧\"</i>"
    )

    buttons = [[InlineKeyboardButton("🔄 再来一次", callback_data="forge_again")]]
    await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
    session.close()


async def my_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看当前装备"""
    msg = update.effective_message
    if not msg:
        return

    user = update.effective_user
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()

    if not u or not u.emby_account:
        await reply_with_auto_delete(msg, "👻 <b>请先 /bind 缔结魔法契约喵！</b>")
        session.close()
        return

    weapon = u.weapon if u.weapon else "赤手空拳"
    attack = u.attack if u.attack else 10
    vip_badge = " 👑" if u.is_vip else ""

    txt = (
        f"⚔️ <b>【 魔 法 武 器 栏 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>持有者：</b> {u.emby_account}{vip_badge}\n"
        f"🗡️ <b>当前武器：</b> <b>{weapon}</b>\n"
        f"💪 <b>战力评估：</b> <b>{attack}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"使用 /forge 可以锻造新武器哦喵~(｡•̀ᴗ-)✧\"</i>"
    )

    await reply_with_auto_delete(msg, txt)
    session.close()


def register(app):
    """注册插件处理器"""
    app.add_handler(CommandHandler("forge", forge_weapon))
    app.add_handler(CommandHandler("weapon", forge_weapon))
    app.add_handler(CommandHandler("myweapon", my_weapon))
    app.add_handler(CallbackQueryHandler(forge_callback, pattern="^forge_again$"))
