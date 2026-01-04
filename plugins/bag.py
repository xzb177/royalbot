"""
背包系统模块 - 魔法少女版
- 显示用户收集的物品
- 物品数量自动统计
- 按稀有度排序显示
"""
from collections import Counter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from database import get_session, UserBinding
from utils import reply_with_auto_delete, edit_with_auto_delete


# 稀有度配置（用于排序和图标）
RARITY_CONFIG = {
    "🌈": {"name": "UR", "order": 0, "items": ["签名照", "契约书", "小饼干", "传说", "限定"]},
    "🟡": {"name": "SSR", "order": 1, "items": ["4K", "原盘", "典藏", "剧场版", "签名卡"]},
    "🟣": {"name": "SR", "order": 2, "items": ["蓝光", "1080P", "原声带", "设定集"]},
    "🔵": {"name": "R", "order": 3, "items": ["720P", "高清", "主题曲", "立绘"]},
    "⚪": {"name": "N", "order": 4, "items": ["480P", "标清", "剧照", "名片", "宣传"]},
}


def get_item_rarity(item_name: str) -> tuple:
    """根据物品名称返回稀有度图标和排序值

    优先检查盲盒抽到的格式：🟡 电影名 (SSR)
    兼容关键词匹配方式：4K、原盘等
    """
    item_upper = item_name.upper()

    # 优先检查盲盒系统抽到的格式：(UR), (SSR), (SR), (R), (N), (CURSED)
    if "(UR)" in item_upper:
        return "🌈", 0
    if "(SSR)" in item_upper:
        return "🟡", 1
    if "(SR)" in item_upper:
        return "🟣", 2
    if "(R)" in item_upper:
        return "🔵", 3
    if "(CURSED)" in item_upper:
        return "💀", 5  # CURSED 特殊处理

    # 兼容关键词匹配方式（用于手动添加的物品）
    for emoji, config in RARITY_CONFIG.items():
        for keyword in config["items"]:
            if keyword in item_name or keyword.upper() in item_upper:
                return emoji, config["order"]

    # 默认返回普通稀有度
    return "⚪", 4


async def my_bag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示用户背包（支持命令和回调两种方式）"""
    query = getattr(update, "callback_query", None)
    msg = update.effective_message
    if not msg and not query:
        return

    user_id = update.effective_user.id
    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        # 检查是否绑定
        if not u or not u.emby_account:
            error_txt = "💔 <b>请先绑定账号喵！</b>\n\n使用 <code>/bind 账号</code> 绑定后再查看背包~"
            if query:
                await query.edit_message_text(error_txt, parse_mode='HTML')
            else:
                await reply_with_auto_delete(msg, error_txt)
            return

        # 解析背包物品
        raw_items = u.items if u.items else ""

        if not raw_items.strip():
            items_display = "🍃 <i>包包空空的...去抽点盲盒吧喵~(｡･ω･｡)</i>"
        else:
            # 统计物品数量
            items_list = [item.strip() for item in raw_items.split(",") if item.strip()]
            counts = Counter(items_list)

            # 按稀有度分组
            rarity_groups = {
                "🌈": [],  # UR
                "🟡": [],  # SSR
                "🟣": [],  # SR
                "🔵": [],  # R
                "⚪": [],  # N
                "💀": [],  # CURSED
            }

            # 将物品分组
            for item_name, num in counts.items():
                emoji, _ = get_item_rarity(item_name)
                if emoji not in rarity_groups:
                    rarity_groups[emoji] = []
                rarity_groups[emoji].append((item_name, num))

            # 构建显示文本（精简版 - 每个稀有度最多显示3个）
            items_display = ""
            for emoji in ["🌈", "🟡", "🟣", "🔵", "⚪", "💀"]:
                group = rarity_groups[emoji]
                if group:
                    # CURSED 特殊处理，其他从 RARITY_CONFIG 获取
                    rarity_name = "CURSED" if emoji == "💀" else RARITY_CONFIG[emoji]['name']
                    items_display += f"\n{emoji} <b>{rarity_name}</b>："
                    # 精简显示：最多显示3个，多的显示 "等X件"
                    if len(group) > 3:
                        display_items = group[:3]
                        items_display += f" <b>{', '.join([f'{n}×{c}' for _, n, c in [(item, num, counts[item]) for item, num in display_items]])}</b>"
                        items_display += f" <i>等{len(group)}种</i>"
                    else:
                        items_display += f" <b>{', '.join([f'{n}×{c}' for n, c in group])}</b>"

        # 计算总物品数
        total_items = len(raw_items.split(",")) if raw_items.strip() else 0

        # 显示VIP状态
        vip_badge = " 👑" if u.is_vip else ""

        txt = (
            f"🎒 <b>【 背 包 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>{u.emby_account}</b>{vip_badge} | 💎 {u.points} MP\n"
            f"⚔️ 战力: {u.attack or 10} | 📊 {total_items}件\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>收藏</b>{items_display}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>\"快去 /poster 填充宝库喵~(｡•̀ᴗ-)✧\"</i>"
        )

        # 快捷按钮（添加物品详情按钮）
        keyboard = [
            [
                InlineKeyboardButton("🎰 抽盲盒", callback_data="bag_gacha"),
                InlineKeyboardButton("📜 个人档案", callback_data="bag_me")
            ],
            [InlineKeyboardButton("📋 物品详情", callback_data="bag_detail")]
        ]

        # 根据调用方式选择编辑或回复
        if query:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        else:
            await reply_with_auto_delete(msg, txt, reply_markup=InlineKeyboardMarkup(keyboard))


async def bag_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理背包按钮回调"""
    query = update.callback_query
    await query.answer()

    if query.data == "bag_gacha":
        await edit_with_auto_delete(
            query,
            f"🎰 <b>【 命 运 · 盲 盒 机 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"请使用 <code>/poster</code> 命令抽取盲盒喵~\n"
            f"VIP 用户享受 5 折优惠！\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>\"欧气满满，抽卡必出 SSR 喵！(｡•̀ᴗ-)✧\"</i>",
            parse_mode='HTML'
        )
    elif query.data == "bag_me":
        await edit_with_auto_delete(
            query,
            f"📜 <b>【 冒 险 者 · 档 案 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"请使用 <code>/me</code> 命令查看详细个人资料喵~\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>\"了解自己的实力，才能变得更强喵！(｡･ω･｡)\"</i>",
            parse_mode='HTML'
        )
    elif query.data == "bag_detail":
        # 显示物品详情
        user_id = query.from_user.id
        with get_session() as session:
            u = session.query(UserBinding).filter_by(tg_id=user_id).first()

            if not u or not u.emby_account:
                await edit_with_auto_delete(query, "💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
                return

            raw_items = u.items if u.items else ""

            if not raw_items.strip():
                await edit_with_auto_delete(
                    query,
                    "📋 <b>【 物 品 详 情 】</b>\n\n"
                    "🍃 背包空空如也...",
                    parse_mode='HTML'
                )
                return

            # 统计物品数量
            items_list = [item.strip() for item in raw_items.split(",") if item.strip()]
            counts = Counter(items_list)

            # 按稀有度排序
            sorted_items = sorted(counts.items(), key=lambda x: get_item_rarity(x[0])[1])

            # 构建详情文本
            detail_text = "📋 <b>【 物 品 详 情 】</b>\n"
            detail_text += "━━━━━━━━━━━━━━━━━━\n"

            for item_name, num in sorted_items:
                emoji, _ = get_item_rarity(item_name)
                # 提取物品名（去掉稀有度标记）
                clean_name = item_name
                for marker in ["(UR)", "(SSR)", "(SR)", "(R)", "(N)", "(CURSED)"]:
                    clean_name = clean_name.replace(marker, "").strip()

                detail_text += f"{emoji} <b>{clean_name}</b> × {num}\n"

            detail_text += "━━━━━━━━━━━━━━━━━━\n"
            detail_text += f"📊 总计: {len(items_list)} 件物品\n"
            detail_text += "━━━━━━━━━━━━━━━━━━\n"
            detail_text += "<i>💡 UR>SSR>SR>R>N 稀有度排序</i>"

            buttons = [[InlineKeyboardButton("🔙 返回背包", callback_data="bag_back")]]

            await query.edit_message_text(
                detail_text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode='HTML'
            )
    elif query.data == "bag_back":
        # 返回背包界面
        user_id = query.from_user.id
        with get_session() as session:
            u = session.query(UserBinding).filter_by(tg_id=user_id).first()

            if not u or not u.emby_account:
                await edit_with_auto_delete(query, "💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
                return

            raw_items = u.items if u.items else ""

            if not raw_items.strip():
                items_display = "🍃 <i>包包空空的...去抽点盲盒吧喵~(｡･ω･｡)</i>"
            else:
                items_list = [item.strip() for item in raw_items.split(",") if item.strip()]
                counts = Counter(items_list)

                rarity_groups = {
                    "🌈": [], "🟡": [], "🟣": [], "🔵": [], "⚪": [], "💀": [],
                }

                for item_name, num in counts.items():
                    emoji, _ = get_item_rarity(item_name)
                    if emoji not in rarity_groups:
                        rarity_groups[emoji] = []
                    rarity_groups[emoji].append((item_name, num))

                items_display = ""
                for emoji in ["🌈", "🟡", "🟣", "🔵", "⚪", "💀"]:
                    group = rarity_groups[emoji]
                    if group:
                        rarity_name = "CURSED" if emoji == "💀" else RARITY_CONFIG[emoji]['name']
                        items_display += f"\n{emoji} <b>{rarity_name}</b>："
                        if len(group) > 3:
                            display_items = group[:3]
                            items_display += f" <b>{', '.join([f'{n}×{c}' for _, n, c in [(item, num, counts[item]) for item, num in display_items]])}</b>"
                            items_display += f" <i>等{len(group)}种</i>"
                        else:
                            items_display += f" <b>{', '.join([f'{n}×{c}' for n, c in group])}</b>"

            total_items = len(raw_items.split(",")) if raw_items.strip() else 0
            vip_badge = " 👑" if u.is_vip else ""

            txt = (
                f"🎒 <b>【 背 包 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>{u.emby_account}</b>{vip_badge} | 💎 {u.points} MP\n"
                f"⚔️ 战力: {u.attack or 10} | 📊 {total_items}件\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 <b>收藏</b>{items_display}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>\"快去 /poster 填充宝库喵~(｡•̀ᴗ-)✧\"</i>"
            )

            keyboard = [
                [
                    InlineKeyboardButton("🎰 抽盲盒", callback_data="bag_gacha"),
                    InlineKeyboardButton("📜 个人档案", callback_data="bag_me")
                ],
                [InlineKeyboardButton("📋 物品详情", callback_data="bag_detail")]
            ]

            await query.edit_message_text(
                txt,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )


def register(app):
    app.add_handler(CommandHandler("bag", my_bag))
    app.add_handler(CommandHandler("items", my_bag))
    app.add_handler(CallbackQueryHandler(bag_callback, pattern=r"^bag_"))
