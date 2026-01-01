"""
魔法商店系统 - 魔法少女版
- 购买各种道具和增益效果
- VIP 用户享受折扣优惠
- 支持参数购买和按钮购买
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete
import random


# 商店商品配置
SHOP_ITEMS = {
    "tarot": {
        "name": "🔮 塔罗占卜券",
        "desc": "额外一次塔罗占卜机会",
        "price": 50,
        "vip_price": 25,
        "emoji": "🔮"
    },
    "gacha": {
        "name": "🎰 盲盒券",
        "desc": "抽取一次魔法盲盒",
        "price": 100,
        "vip_price": 50,
        "emoji": "🎰"
    },
    "forge_small": {
        "name": "⚒️ 锻造锤(小)",
        "desc": "免费锻造一次(普通价100MP)",
        "price": 50,
        "vip_price": 25,
        "emoji": "⚒️"
    },
    "forge_big": {
        "name": "⚒️ 锻造锤(大)",
        "desc": "免费锻造一次+高稀有度概率UP",
        "price": 500,
        "vip_price": 250,
        "emoji": "⚒️"
    },
    "lucky": {
        "name": "🍀 幸运草",
        "desc": "下次签到暴击率+50%",
        "price": 30,
        "vip_price": 15,
        "emoji": "🍀"
    },
    "energy": {
        "name": "⚡ 能量药水",
        "desc": "恢复200MP(直接获得)",
        "price": 150,
        "vip_price": 75,
        "emoji": "⚡"
    },
    "shield": {
        "name": "🛡️ 防御卷轴",
        "desc": "下次决斗失败不掉钱",
        "price": 80,
        "vip_price": 40,
        "emoji": "🛡️"
    },
    "box": {
        "name": "🎁 神秘宝箱",
        "desc": "随机开出50-500MP",
        "price": 100,
        "vip_price": 50,
        "emoji": "🎁"
    },
}


async def shop_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示商店主页"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user_id).first()

    if not u or not u.emby_account:
        session.close()
        await reply_with_auto_delete(
            msg,
            "💔 <b>请先绑定账号喵！</b>\n\n"
            "使用 <code>/bind 账号</code> 绑定后再购物~"
        )
        return

    vip_badge = " 👑" if u.is_vip else ""
    discount = "5折" if u.is_vip else "原价"

    txt = (
        f"🛒 <b>【 魔 法 · 商 店 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>客人：</b> {u.emby_account}{vip_badge}\n"
        f"💎 <b>钱包：</b> {u.points} MP\n"
        f"🏷️ <b>折扣：</b> {discount}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📜 <b>使用 /buy 商品名 购买商品</b>\n"
        f"💡 <b>或点击下方按钮购买</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )

    # 构建商品列表
    shop_list = ""
    for item_id, item in SHOP_ITEMS.items():
        price = item["vip_price"] if u.is_vip else item["price"]
        shop_list += f"{item['emoji']} <b>{item['name']}</b> — <b>{price} MP</b>\n"

    txt += f"\n📦 <b>今日商品：</b>\n{shop_list}"
    txt += "\n━━━━━━━━━━━━━━━━━━\n"
    txt += "<i>\"欢迎光临！这里有你需要的所有魔法道具喵~(｡•̀ᴗ-)✧\"</i>"

    # 构建按钮
    buttons = []
    row = []
    for i, (item_id, item) in enumerate(SHOP_ITEMS.items()):
        price = item["vip_price"] if u.is_vip else item["price"]
        row.append(InlineKeyboardButton(f"{item['emoji']} {price}MP", callback_data=f"buy_{item_id}"))
        if len(row) == 2 or i == len(SHOP_ITEMS) - 1:
            buttons.append(row)
            row = []

    await msg.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))
    session.close()


async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str = None):
    """购买商品"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user_id).first()

    if not u or not u.emby_account:
        session.close()
        await reply_with_auto_delete(
            msg,
            "💔 <b>请先绑定账号喵！</b>\n\n"
            "使用 <code>/bind 账号</code> 绑定后再购物~"
        )
        return

    # 从参数获取商品ID
    if not item_id and context.args:
        item_id = context.args[0].lower()

    if not item_id or item_id not in SHOP_ITEMS:
        session.close()
        items_list = ", ".join(SHOP_ITEMS.keys())
        await reply_with_auto_delete(
            msg,
            f"🛒 <b>【 商 店 】</b>\n\n"
            f"❓ 找不到这个商品喵~\n\n"
            f"📜 <b>可用商品：</b>\n"
            f"{items_list}\n\n"
            f"💡 使用 <code>/buy 商品名</code> 购买\n"
            f"或使用 <code>/shop</code> 查看商品列表"
        )
        return

    item = SHOP_ITEMS[item_id]
    price = item["vip_price"] if u.is_vip else item["price"]

    if u.points < price:
        session.close()
        await reply_with_auto_delete(
            msg,
            f"💸 <b>【 魔 力 不 足 】</b>\n\n"
            f"钱包里只有 <b>{u.points} MP</b>\n"
            f"购买 {item['name']} 需要 <b>{price} MP</b> 喵~"
        )
        return

    # 扣除费用
    u.points -= price

    # 处理商品效果
    result_msg = ""
    if item_id == "energy":
        # 能量药水：直接获得MP
        gain = 200
        u.points += gain
        result_msg = f"⚡ <b>获得 200 MP！</b>"

    elif item_id == "box":
        # 神秘宝箱：随机开出MP
        gain = random.randint(50, 500)
        u.points += gain
        result_msg = f"🎁 <b>宝箱开出 {gain} MP！</b>"

    elif item_id == "lucky":
        # 幸运草：设置幸运标记
        u.lucky_boost = True
        result_msg = "🍀 <b>下次签到暴击率+50%！</b>"

    elif item_id == "shield":
        # 防护卷轴：设置防护标记
        u.shield_active = True
        result_msg = "🛡️ <b>下次决斗失败不掉钱！</b>"

    elif item_id == "tarot":
        # 塔罗券：增加塔罗次数
        u.extra_tarot = (u.extra_tarot or 0) + 1
        result_msg = "🔮 <b>获得一次额外塔罗占卜！</b>"

    elif item_id == "gacha":
        # 盲盒券：增加盲盒次数
        u.extra_gacha = (u.extra_gacha or 0) + 1
        result_msg = "🎰 <b>获得一次额外盲盒抽取！</b>"

    elif item_id == "forge_small":
        # 小锻造锤：免费锻造
        u.free_forges = (u.free_forges or 0) + 1
        result_msg = "⚒️ <b>获得一张免费锻造券！</b>"

    elif item_id == "forge_big":
        # 大锻造锤：免费锻造+高稀有度
        u.free_forges_big = (u.free_forges_big or 0) + 1
        result_msg = "⚒️ <b>获得高级锻造券(稀有度UP)！</b>"

    session.commit()
    session.close()

    vip_badge = " 👑" if u.is_vip else ""

    txt = (
        f"🛒 <b>【 购 买 成 功 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>客人：</b> {u.emby_account}{vip_badge}\n"
        f"✨ <b>购买：</b> {item['name']}\n"
        f"💸 <b>花费：</b> {price} MP\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{result_msg}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>剩余魔力：</b> {u.points} MP\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"感谢惠顾！期待您的下次光临喵~(｡•̀ᴗ-)✧\"</i>"
    )

    await reply_with_auto_delete(msg, txt)


async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理商店按钮回调"""
    query = update.callback_query
    await query.answer()

    # 解析商品ID
    item_id = query.data.replace("buy_", "")

    user_id = query.from_user.id
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user_id).first()

    if not u or not u.emby_account:
        await query.edit_message_text("💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
        session.close()
        return

    if item_id not in SHOP_ITEMS:
        await query.edit_message_text("❓ <b>商品不存在喵~</b>", parse_mode='HTML')
        session.close()
        return

    item = SHOP_ITEMS[item_id]
    price = item["vip_price"] if u.is_vip else item["price"]

    if u.points < price:
        await query.edit_message_text(
            f"💸 <b>【 魔 力 不 足 】</b>\n\n"
            f"钱包里只有 <b>{u.points} MP</b>\n"
            f"购买 {item['name']} 需要 <b>{price} MP</b> 喵~",
            parse_mode='HTML'
        )
        session.close()
        return

    # 扣除费用
    u.points -= price

    # 处理商品效果
    result_msg = ""
    if item_id == "energy":
        gain = 200
        u.points += gain
        result_msg = f"⚡ <b>获得 200 MP！</b>"
    elif item_id == "box":
        gain = random.randint(50, 500)
        u.points += gain
        result_msg = f"🎁 <b>宝箱开出 {gain} MP！</b>"
    elif item_id == "lucky":
        u.lucky_boost = True
        result_msg = "🍀 <b>下次签到暴击率+50%！</b>"
    elif item_id == "shield":
        u.shield_active = True
        result_msg = "🛡️ <b>下次决斗失败不掉钱！</b>"
    elif item_id == "tarot":
        u.extra_tarot = (u.extra_tarot or 0) + 1
        result_msg = "🔮 <b>获得一次额外塔罗占卜！</b>"
    elif item_id == "gacha":
        u.extra_gacha = (u.extra_gacha or 0) + 1
        result_msg = "🎰 <b>获得一次额外盲盒抽取！</b>"
    elif item_id == "forge_small":
        u.free_forges = (u.free_forges or 0) + 1
        result_msg = "⚒️ <b>获得一张免费锻造券！</b>"
    elif item_id == "forge_big":
        u.free_forges_big = (u.free_forges_big or 0) + 1
        result_msg = "⚒️ <b>获得高级锻造券(稀有度UP)！</b>"

    session.commit()
    session.close()

    vip_badge = " 👑" if u.is_vip else ""

    txt = (
        f"🛒 <b>【 购 买 成 功 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>客人：</b> {u.emby_account}{vip_badge}\n"
        f"✨ <b>购买：</b> {item['name']}\n"
        f"💸 <b>花费：</b> {price} MP\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{result_msg}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>剩余魔力：</b> {u.points} MP\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"感谢惠顾！期待您的下次光临喵~(｡•̀ᴗ-)✧\"</i>"
    )

    buttons = [[InlineKeyboardButton("🔙 返回商店", callback_data="shop_back")]]
    try:
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
    except Exception:
        await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))


async def shop_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """返回商店主页"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user_id).first()

    if not u or not u.emby_account:
        await query.edit_message_text("💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
        session.close()
        return

    vip_badge = " 👑" if u.is_vip else ""
    discount = "5折" if u.is_vip else "原价"

    txt = (
        f"🛒 <b>【 魔 法 · 商 店 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>客人：</b> {u.emby_account}{vip_badge}\n"
        f"💎 <b>钱包：</b> {u.points} MP\n"
        f"🏷️ <b>折扣：</b> {discount}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📜 <b>使用 /buy 商品名 购买商品</b>\n"
        f"💡 <b>或点击下方按钮购买</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )

    shop_list = ""
    for item_id, item in SHOP_ITEMS.items():
        price = item["vip_price"] if u.is_vip else item["price"]
        shop_list += f"{item['emoji']} <b>{item['name']}</b> — <b>{price} MP</b>\n"

    txt += f"\n📦 <b>今日商品：</b>\n{shop_list}"
    txt += "\n━━━━━━━━━━━━━━━━━━\n"
    txt += "<i>\"欢迎光临！这里有你需要的所有魔法道具喵~(｡•̀ᴗ-)✧\"</i>"

    buttons = []
    row = []
    for i, (item_id, item) in enumerate(SHOP_ITEMS.items()):
        price = item["vip_price"] if u.is_vip else item["price"]
        row.append(InlineKeyboardButton(f"{item['emoji']} {price}MP", callback_data=f"buy_{item_id}"))
        if len(row) == 2 or i == len(SHOP_ITEMS) - 1:
            buttons.append(row)
            row = []

    session.close()
    try:
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
    except Exception:
        pass


def register(app):
    """注册商店处理器"""
    app.add_handler(CommandHandler("shop", shop_main))
    app.add_handler(CommandHandler("store", shop_main))
    app.add_handler(CommandHandler("buy", buy_item))
    app.add_handler(CallbackQueryHandler(shop_callback, pattern=r"^buy_"))
    app.add_handler(CallbackQueryHandler(shop_back_callback, pattern=r"^shop_back$"))
