"""
外观系统 - Cosmetics System
- 头像框：装饰个人信息
- 称号：展示成就身份
- 主题：个性化界面
- 限时外观：稀有收藏
"""
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding
from utils import reply_with_auto_delete

logger = logging.getLogger(__name__)


# ==========================================
# 外观配置
# ==========================================

# 头像框商店
AVATAR_FRAMES = {
    # === 免费头像框 ===
    "default": {
        "name": "默认",
        "emoji": "⬜",
        "price": 0,
        "rarity": "N",
        "desc": "简约而不简单",
        "preview": "[⬜ ▓▓▓▓⬜]"
    },
    "bronze": {
        "name": "青铜边框",
        "emoji": "🟫",
        "price": 0,
        "rarity": "N",
        "desc": "新手专属边框",
        "preview": "[🟫 ▓▓▓▓🟫]",
        "condition": lambda u: (u.attack or 0) >= 50
    },

    # === 付费头像框 ===
    "silver": {
        "name": "白银边框",
        "emoji": "⚪",
        "price": 500,
        "rarity": "R",
        "desc": "优雅的白银光泽",
        "preview": "[⚪ ▓▓▓▓⚪]"
    },
    "gold": {
        "name": "黄金边框",
        "emoji": "🟡",
        "price": 1000,
        "rarity": "SR",
        "desc": "金灿灿的土豪气息",
        "preview": "[🟡 ▓▓▓▓🟡]"
    },
    "diamond": {
        "name": "钻石边框",
        "emoji": "💎",
        "price": 3000,
        "rarity": "SSR",
        "desc": "璀璨夺目的钻石",
        "preview": "[💎 ▓▓▓▓💎]"
    },
    "rainbow": {
        "name": "彩虹边框",
        "emoji": "🌈",
        "price": 5000,
        "rarity": "UR",
        "desc": "七彩斑斓的梦幻边框",
        "preview": "[🌈 ▓▓▓▓🌈]"
    },
    "fire": {
        "name": "烈焰边框",
        "emoji": "🔥",
        "price": 2000,
        "rarity": "SR",
        "desc": "燃烧着熊熊烈火",
        "preview": "[🔥 ▓▓▓▓🔥]"
    },
    "ice": {
        "name": "冰霜边框",
        "emoji": "❄️",
        "price": 2000,
        "rarity": "SR",
        "desc": "寒气逼人的冰晶",
        "preview": "[❄️ ▓▓▓▓❄️]"
    },
    "void": {
        "name": "虚空边框",
        "emoji": "🌌",
        "price": 10000,
        "rarity": "UR",
        "desc": "来自虚空的神秘力量",
        "preview": "[🌌 ▓▓▓▓🌌]"
    },
}

# 称号商店
TITLES = {
    # === 免费称号 ===
    "novice": {
        "name": "见习魔法师",
        "emoji": "🌱",
        "price": 0,
        "rarity": "N",
        "desc": "刚入门的魔法师",
        "condition": lambda u: True
    },

    # === 付费称号 ===
    "warrior": {
        "name": "勇士",
        "emoji": "⚔️",
        "price": 300,
        "rarity": "R",
        "desc": "勇敢的战士",
        "preview": "⚔️ 勇士"
    },
    "champion": {
        "name": "冠军",
        "emoji": "🏆",
        "price": 1000,
        "rarity": "SR",
        "desc": "比赛的冠军",
        "preview": "🏆 冠军"
    },
    "legend": {
        "name": "传奇",
        "emoji": "🌟",
        "price": 3000,
        "rarity": "SSR",
        "desc": "传说中的存在",
        "preview": "🌟 传奇"
    },
    "rich": {
        "name": "大富翁",
        "emoji": "💰",
        "price": 5000,
        "rarity": "UR",
        "desc": "富可敌国",
        "preview": "💰 大富翁"
    },
    "lucky": {
        "name": "欧皇",
        "emoji": "🍀",
        "price": 2000,
        "rarity": "SR",
        "desc": "运气爆棚",
        "preview": "🍀 欧皇"
    },
    "emperor": {
        "name": "皇帝",
        "emoji": "👑",
        "price": 10000,
        "rarity": "UR",
        "desc": "至高无上的统治者",
        "preview": "👑 皇帝"
    },
}

# 限时外观（特殊活动）
LIMITED_EDITIONS = {
    "newyear_frame": {
        "name": "新年边框",
        "emoji": "🧧",
        "price": 0,  # 活动赠送
        "rarity": "SSR",
        "desc": "新年快乐！",
        "preview": "[🧧 ▓▓▓▓🧧]",
        "limited": True,
        "expiry": "2026-12-31"
    }
}


# ==========================================
# 工具函数
# ==========================================

def get_owned_list(user, item_type: str) -> list:
    """获取用户拥有的外观列表"""
    if item_type == "frames":
        return (user.owned_frames or "").split(",") if user.owned_frames else ["default"]
    elif item_type == "titles":
        return (user.owned_titles or "").split(",") if user.owned_titles else ["novice"]
    elif item_type == "themes":
        return (user.owned_themes or "").split(",") if user.owned_themes else ["default"]
    return []


def add_owned_item(user, item_type: str, item_id: str) -> None:
    """添加拥有的外观"""
    if item_type == "frames":
        current = user.owned_frames or ""
        items = current.split(",") if current else ["default"]
        if item_id not in items:
            items.append(item_id)
        user.owned_frames = ",".join(items)
    elif item_type == "titles":
        current = user.owned_titles or ""
        items = current.split(",") if current else ["novice"]
        if item_id not in items:
            items.append(item_id)
        user.owned_titles = ",".join(items)
    elif item_type == "themes":
        current = user.owned_themes or ""
        items = current.split(",") if current else ["default"]
        if item_id not in items:
            items.append(item_id)
        user.owned_themes = ",".join(items)


def has_item(user, item_type: str, item_id: str) -> bool:
    """检查是否拥有某外观"""
    owned = get_owned_list(user, item_type)
    return item_id in owned


def get_rarity_color(rarity: str) -> str:
    """获取稀有度颜色"""
    colors = {
        "N": "⚪",
        "R": "🔵",
        "SR": "🟣",
        "SSR": "🟡",
        "UR": "🌈"
    }
    return colors.get(rarity, "⚪")


async def get_cosmetics_main_panel(user: UserBinding, first_name: str) -> tuple:
    """获取外观主面板（用于编辑消息）"""
    # 获取当前装备
    current_frame = user.equipped_frame or "default"
    current_title = user.equipped_title or "novice"
    current_theme = user.equipped_theme or "default"

    # 获取拥有的数量
    owned_frames = len(get_owned_list(user, "frames"))
    owned_titles = len(get_owned_list(user, "titles"))
    owned_themes = len(get_owned_list(user, "themes"))

    # 获取当前装备信息
    frame_info = AVATAR_FRAMES.get(current_frame, AVATAR_FRAMES["default"])
    title_info = TITLES.get(current_title, TITLES["novice"])

    lines = [
        "🎨 <b>【 外 观 系 统 】</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"👤 <b>魔法师：</b> {first_name or '神秘人'}",
        "",
        "📋 <b>当前装备：</b>",
        f"   🖼️ <b>头像框：</b> {frame_info['emoji']} {frame_info['name']}",
        f"   🏷️ <b>称号：</b> {title_info['emoji']} {title_info['name']}",
        f"   🎨 <b>主题：</b> 默认主题",
        "",
        "📦 <b>我的收藏：</b>",
        f"   🖼️ 头像框: {owned_frames} 个",
        f"   🏷️ 称号: {owned_titles} 个",
        f"   🎨 主题: {owned_themes} 个",
        "",
        f"💰 <b>当前余额：</b> {user.points} MP",
    ]

    buttons = [
        [
            InlineKeyboardButton("🖼️ 头像框商店", callback_data="cos_frame_shop"),
            InlineKeyboardButton("🏷️ 称号商店", callback_data="cos_title_shop")
        ],
        [
            InlineKeyboardButton("🎒 我的收藏", callback_data="cos_collection"),
            InlineKeyboardButton("👔 当前装备", callback_data="cos_equipped")
        ],
        [InlineKeyboardButton("🔙 返回", callback_data="cos_back")]
    ]

    return "\n".join(lines), InlineKeyboardMarkup(buttons)


# ==========================================
# 主界面
# ==========================================

async def cosmetics_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """外观系统主界面（命令入口，发送新消息）"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user or not user.emby_account:
            await reply_with_auto_delete(msg, "💔 <b>请先绑定账号喵！</b>\n\n使用 <code>/bind 账号</code> 绑定后再来。")
            return

        text, markup = await get_cosmetics_main_panel(user, update.effective_user.first_name)
        await msg.reply_html(text, reply_markup=markup)


async def cosmetics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """外观系统主界面（菜单入口，编辑消息）"""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    user_id = query.from_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user or not user.emby_account:
            await query.edit_message_text("💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        text, markup = await get_cosmetics_main_panel(user, query.from_user.first_name)
        await query.edit_message_text(text, reply_markup=markup, parse_mode='HTML')


# ==========================================
# 头像框商店
# ==========================================

async def frame_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """头像框商店"""
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

        owned = get_owned_list(user, "frames")

        # 构建商店列表
        lines = [
            "🖼️ <b>【 头 像 框 商 店 】</b>",
            "━━━━━━━━━━━━━━━━━━",
            f"💰 <b>余额：</b> {user.points} MP",
            ""
        ]

        buttons = []

        for frame_id, frame in AVATAR_FRAMES.items():
            is_owned = frame_id in owned
            is_equipped = user.equipped_frame == frame_id
            rarity_color = get_rarity_color(frame["rarity"])

            if is_owned:
                status = "✅已拥有"
                if is_equipped:
                    status = "🔵已装备"
            else:
                status = f"💰{frame['price']} MP"

            lines.append(
                f"{rarity_color} {frame['emoji']} <b>{frame['name']}</b>"
            )
            lines.append(
                f"    {frame['preview']} | {status}"
            )

            # 添加按钮
            if is_owned:
                if not is_equipped:
                    buttons.append([
                        InlineKeyboardButton(f"🔵 装备 {frame['name']}", callback_data=f"cos_equip_frame_{frame_id}")
                    ])
            else:
                if frame["price"] > 0:
                    buttons.append([
                        InlineKeyboardButton(f"💰 购买 {frame['name']} ({frame['price']}MP)", callback_data=f"cos_buy_frame_{frame_id}")
                    ])

        buttons.append([InlineKeyboardButton("🔙 返回", callback_data="cos_back")])

        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )


# ==========================================
# 称号商店
# ==========================================

async def title_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """称号商店"""
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

        owned = get_owned_list(user, "titles")

        lines = [
            "🏷️ <b>【 称 号 商 店 】</b>",
            "━━━━━━━━━━━━━━━━━━",
            f"💰 <b>余额：</b> {user.points} MP",
            ""
        ]

        buttons = []

        for title_id, title in TITLES.items():
            is_owned = title_id in owned
            is_equipped = user.equipped_title == title_id
            rarity_color = get_rarity_color(title["rarity"])

            if is_owned:
                status = "✅已拥有"
                if is_equipped:
                    status = "🔵已装备"
            else:
                status = f"💰{title['price']} MP"

            lines.append(
                f"{rarity_color} {title['emoji']} <b>{title['name']}</b>"
            )
            lines.append(
                f"    {title['desc']} | {status}"
            )

            if is_owned and not is_equipped:
                buttons.append([
                    InlineKeyboardButton(f"🔵 装备 {title['name']}", callback_data=f"cos_equip_title_{title_id}")
                ])
            elif not is_owned and title["price"] > 0:
                buttons.append([
                    InlineKeyboardButton(f"💰 购买 ({title['price']}MP)", callback_data=f"cos_buy_title_{title_id}")
                ])

        buttons.append([InlineKeyboardButton("🔙 返回", callback_data="cos_back")])

        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )


# ==========================================
# 购买外观
# ==========================================

async def buy_cosmetic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """购买外观"""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data
    parts = data.split("_")

    if parts[2] == "frame":
        item_id = parts[3]
        item = AVATAR_FRAMES.get(item_id)
        item_type = "frames"
        field = "owned_frames"
        equip_field = "equipped_frame"
    elif parts[2] == "title":
        item_id = parts[3]
        item = TITLES.get(item_id)
        item_type = "titles"
        field = "owned_titles"
        equip_field = "equipped_title"
    else:
        await query.edit_message_text("⚠️ <b>未知的商品喵！</b>", parse_mode='HTML')
        return

    if not item:
        await query.edit_message_text("⚠️ <b>商品不存在喵！</b>", parse_mode='HTML')
        return

    user_id = query.from_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user:
            await query.edit_message_text("💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        # 检查是否已拥有
        if has_item(user, item_type, item_id):
            await query.answer("您已拥有此商品！", show_alert=True)
            return

        # 检查余额
        price = item["price"]
        if user.is_vip:
            price = int(price * 0.8)  # VIP 8折

        if user.points < price:
            await query.edit_message_text(
                f"💸 <b>魔力不足喵！</b>\n\n"
                f"购买需要 <b>{price}</b> MP\n"
                f"当前余额：<b>{user.points}</b> MP",
                parse_mode='HTML'
            )
            return

        # 扣款并添加
        user.points -= price
        add_owned_item(user, item_type, item_id)

        session.commit()

        await query.edit_message_text(
            f"🎉 <b>购买成功！</b>\n\n"
            f"您获得了 <b>{item['emoji']} {item['name']}</b>！\n"
            f"💰 <b>剩余魔力：</b> {user.points} MP",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 返回商店", callback_data=f"cos_{parts[2]}_shop")],
                [InlineKeyboardButton("🔵 立即装备", callback_data=f"cos_equip_{parts[2]}_{item_id}")]
            ]),
            parse_mode='HTML'
        )


# ==========================================
# 装备外观
# ==========================================

async def equip_cosmetic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """装备外观"""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data
    parts = data.split("_")

    if parts[2] == "frame":
        item_id = parts[3]
        item = AVATAR_FRAMES.get(item_id)
        field = "equipped_frame"
    elif parts[2] == "title":
        item_id = parts[3]
        item = TITLES.get(item_id)
        field = "equipped_title"
    else:
        return

    if not item:
        return

    user_id = query.from_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user:
            return

        setattr(user, field, item_id)
        session.commit()

        await query.answer(f"已装备 {item['name']}！", show_alert=True)


# ==========================================
# 返回
# ==========================================

async def cos_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """返回主界面（编辑消息）"""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    user_id = query.from_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user or not user.emby_account:
            await query.edit_message_text("💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        text, markup = await get_cosmetics_main_panel(user, query.from_user.first_name)
        await query.edit_message_text(text, reply_markup=markup, parse_mode='HTML')


# ==========================================
# 注册模块
# ==========================================

def register(app):
    app.add_handler(CommandHandler("cosmetics", cosmetics_main))
    app.add_handler(CommandHandler("shop", cosmetics_main))
    app.add_handler(CallbackQueryHandler(cosmetics_menu, pattern="^cosmetics$"))  # 从菜单进入

    # 回调处理
    app.add_handler(CallbackQueryHandler(cos_back, pattern="^cos_back$"))
    app.add_handler(CallbackQueryHandler(frame_shop, pattern="^cos_frame_shop$"))
    app.add_handler(CallbackQueryHandler(title_shop, pattern="^cos_title_shop$"))
    app.add_handler(CallbackQueryHandler(buy_cosmetic, pattern=r"^cos_buy_(frame|title)_\w+$"))
    app.add_handler(CallbackQueryHandler(equip_cosmetic, pattern=r"^cos_equip_(frame|title)_\w+$"))
