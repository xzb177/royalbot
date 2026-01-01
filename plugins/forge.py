"""
魔法少女炼金系统 (Forge)
玩家可以消耗 MP 锻造魔法武器，获得战力加成
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete
import random


# 导入活动追踪函数
async def track_activity_wrapper(user_id: int, activity_type: str):
    """包装函数，延迟导入避免循环依赖"""
    from mission import track_activity
    await track_activity(user_id, activity_type)

# 词缀库：决定魔法武器的稀有度和名字
PREFIXES = [
    "破碎的", "生锈的", "练习用的", "普通的", "精良的",
    "稀有的", "史诗的", "传说的", "神话的", "被诅咒的",
    "真·", "极·", "终焉之", "创世的"
]
ELEMENTS = ["火焰", "冰霜", "雷霆", "暗影", "神圣", "虚空", "可爱", "用来做蛋糕的"]
TYPES = ["魔法杖", "魔导书", "法杖", "魔剑", "平底锅", "咸鱼", "魔法棒", "加特林", "圣剑"]


def _generate_weapon():
    """生成随机魔法武器名称和战力"""
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
    user = update.effective_user
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()

    # 检查是否绑定
    if not u or not u.emby_account:
        await reply_with_auto_delete(update.message, "👻 <b>请先 /bind 缔结魔法契约喵！</b>")
        session.close()
        return

    # 设定价格 (VIP 半价)
    base_cost = 200
    cost = int(base_cost * 0.5) if u.is_vip else base_cost

    if u.points < cost:
        await reply_with_auto_delete(
            update.message,
            f"🔥 <b>魔法炉火熄灭了...</b>\n\n"
            f"魔力不足喵！锻造需要 <b>{cost} MP</b>~\n"
            f"当前余额：{u.points} MP\n"
            f"<i>(提示：VIP 锻造享受 5 折优惠哦！)</i>"
        )
        session.close()
        return

    # 扣除费用
    u.points -= cost

    # 生成魔法武器
    new_name, base_atk, rank = _generate_weapon()

    # 旧装备信息
    old_weapon = u.weapon if u.weapon else "无"
    old_atk = u.attack if u.attack else 0

    # 更新装备
    u.weapon = new_name
    u.attack = base_atk
    # 追踪活动用于悬赏任务
    await track_activity_wrapper(user.id, "forge")
    session.commit()

    # 结果展示
    txt = (
        f"⚒️ <b>【 魔 法 武 器 · 炼 金 完 成 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔥 消耗魔力：-{cost} MP\n\n"
        f"🗑️ <b>替换旧物：</b> {old_weapon} (ATK: {old_atk})\n"
        f"✨ <b>获得新武器：</b> <b>{new_name}</b>\n"
        f"📊 <b>武器评级：</b> {rank}\n"
        f"⚔️ <b>战力评估：</b> <b>{base_atk}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>“感受到了吗？这股涌动的魔法力量... Master 喜欢吗？(｡•̀ᴗ-)✧”</i>"
    )

    buttons = [[InlineKeyboardButton("再来一次 /forge", callback_data="forge_again")]]
    await reply_with_auto_delete(
        update.message, txt,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    session.close()


async def forge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理"再来一次"按钮回调"""
    query = update.callback_query
    await query.answer()

    # 模拟调用 forge_weapon，但是用 callback_query 发送
    user = query.from_user
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()

    if not u or not u.emby_account:
        await query.edit_message_text("👻 <b>请先 /bind 缔结魔法契约喵！</b>", parse_mode='HTML')
        session.close()
        return

    base_cost = 200
    cost = int(base_cost * 0.5) if u.is_vip else base_cost

    if u.points < cost:
        await query.edit_message_text(
            f"🔥 <b>魔法炉火熄灭了...</b>\n\n"
            f"魔力不足喵！锻造需要 <b>{cost} MP</b>~\n"
            f"当前余额：{u.points} MP",
            parse_mode='HTML'
        )
        session.close()
        return

    u.points -= cost
    new_name, base_atk, rank = _generate_weapon()

    old_weapon = u.weapon if u.weapon else "无"
    old_atk = u.attack if u.attack else 0

    u.weapon = new_name
    u.attack = base_atk
    # 追踪活动用于悬赏任务
    await track_activity_wrapper(user.id, "forge")
    session.commit()

    txt = (
        f"⚒️ <b>【 魔 法 武 器 · 炼 金 完 成 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔥 消耗魔力：-{cost} MP\n\n"
        f"🗑️ <b>替换旧物：</b> {old_weapon} (ATK: {old_atk})\n"
        f"✨ <b>获得新武器：</b> <b>{new_name}</b>\n"
        f"📊 <b>武器评级：</b> {rank}\n"
        f"⚔️ <b>战力评估：</b> <b>{base_atk}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>“感受到了吗？这股涌动的魔法力量... Master 喜欢吗？(｡•̀ᴗ-)✧”</i>"
    )

    buttons = [[InlineKeyboardButton("再来一次 /forge", callback_data="forge_again")]]
    await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
    session.close()


async def my_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看当前装备"""
    user = update.effective_user
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()

    if not u or not u.emby_account:
        await reply_with_auto_delete(update.message, "👻 <b>请先 /bind 缔结魔法契约喵！</b>")
        session.close()
        return

    weapon = u.weapon if u.weapon else "无"
    attack = u.attack if u.attack else 0

    txt = (
        f"⚔️ <b>【 魔 法 武 器 栏 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>武器：</b> {weapon}\n"
        f"💪 <b>战力：</b> {attack}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

    await reply_with_auto_delete(update.message, txt)
    session.close()


def register(app):
    """注册插件处理器"""
    app.add_handler(CommandHandler("forge", forge_weapon))
    app.add_handler(CommandHandler("weapon", forge_weapon))
    app.add_handler(CommandHandler("myweapon", my_weapon))
    app.add_handler(CallbackQueryHandler(forge_callback, pattern="^forge_again$"))
