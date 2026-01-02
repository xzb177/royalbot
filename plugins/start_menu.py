from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete


def get_menu_layout(is_vip: bool = False) -> list:
    """获取菜单按钮布局"""
    # 第一行：个人档案/成为VIP + 每日签到
    first_button_text = "📜 个人档案" if is_vip else "💎 成为 VIP"
    first_button_data = "me" if is_vip else "upgrade_vip"

    buttons = [
        # 核心功能
        [InlineKeyboardButton(first_button_text, callback_data=first_button_data),
         InlineKeyboardButton("🍬 每日签到", callback_data="checkin")],

        # 每日任务 & 赚钱
        [InlineKeyboardButton("📋 每日任务", callback_data="daily_tasks"),
         InlineKeyboardButton("🎡 幸运转盘", callback_data="lucky_wheel")],

        # 资产管理
        [InlineKeyboardButton("🏦 皇家银行", callback_data="bank"),
         InlineKeyboardButton("🛒 魔法商店", callback_data="shop")],

        # 背包 & 排行
        [InlineKeyboardButton("🎒 次源背包", callback_data="bag"),
         InlineKeyboardButton("🏆 荣耀殿堂", callback_data="hall")],

        # 娱乐
        [InlineKeyboardButton("🔮 命运占卜", callback_data="tarot"),
         InlineKeyboardButton("🎰 盲盒抽取", callback_data="poster")],

        # 战斗 & 活跃
        [InlineKeyboardButton("⚔️ 决斗场", callback_data="duel_info"),
         InlineKeyboardButton("📊 活跃度", callback_data="presence")],

        # 工坊 & 帮助
        [InlineKeyboardButton("⚒️ 灵装炼金", callback_data="forge"),
         InlineKeyboardButton("📖 魔法指南", callback_data="help_manual")]
    ]
    return buttons


def get_menu_text(user, is_vip: bool = False) -> str:
    """获取菜单文本"""
    if is_vip:
        return (
            f"🌸 <b>【 魔 法 少 女 · 星 辰 殿 堂 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ <b>Welcome back, Master {user.first_name}</b> ✨\n"
            f"您的专属魔法少女看板娘已就位喵~\n\n"
            f"💎 <b>:: 皇 家 特 权 已 激 活 ::</b>\n"
            f"🚀 4K 极速通道 · <b>已开启</b>\n"
            f"🏰 皇家金库 · <b>已解锁</b>\n"
            f"💕 魔力加成 · <b>生效中</b>\n\n"
            f"<i>\"只要Master开口，无论是摘星星还是捕月亮，\n"
            f"人家都会为您办到的~💖\"</i>\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
    else:
        return (
            f"🏰 <b>【 云 海 · 魔 法 学 院 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ <b>欢迎来到魔法世界，{user.first_name}酱！</b> ✨\n"
            f"我是你的魔法少女向导 <b>看板娘</b>喵~\n\n"
            f"🎀 <b>:: 当 前 状 态 ::</b>\n"
            f"🌱 身份：见习魔法少女\n"
            f"🔒 皇家特权：<b>未觉醒</b>\n\n"
            f"<i>\"只要努力收集魔力结晶，\n"
            f"总有一天会变成大魔法少女的！\n"
            f"加油喵~！(≧◡≦)\"</i>\n"
            f"━━━━━━━━━━━━━━━━━━"
        )


async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()
    is_vip = u.is_vip if u else False
    session.close()

    txt = get_menu_text(user, is_vip)
    buttons = get_menu_layout(is_vip)
    await update.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))


async def help_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "📖 <b>【 魔 法 指 南 】</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "🔗 <b>基础魔法：</b>\n"
        "• <code>/bind</code> — 缔结魔法契约 (必做!)\n"
        "• <code>/daily</code> — 每日签到领魔力\n"
        "• <code>/me</code> — 查看魔法少女档案\n\n"

        "📋 <b>每日任务：</b>\n"
        "• <code>/tasks</code> — 查看每日任务\n"
        "• <code>/wheel</code> — 幸运转盘抽奖\n"
        "• <code>/active</code> — 查看活跃度\n"
        "• <code>/rank</code> — 活跃排行榜\n\n"

        "💰 <b>皇家金库：</b>\n"
        "• <code>/bank</code> — 打开魔法金库\n"
        "• <code>/shop</code> — 魔法商店\n"
        "• <code>/gift</code> — 转赠给小伙伴\n\n"

        "🔮 <b>娱乐时光：</b>\n"
        "• <code>/tarot</code> — 塔罗牌占卜\n"
        "• <code>/poster</code> — 魔法盲盒\n"
        "• <code>/airdrop</code> — 幸运空投(管理员)\n\n"

        "⚔️ <b>战斗竞技：</b>\n"
        "• <code>/duel</code> — 魔法少女决斗\n"
        "• <code>/hall</code> — 战力排行榜\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "<i>\"遇到困难的话...随时召唤看板娘哦！(｡•̀ᴗ-)✧\"</i>"
    )
    msg = update.effective_message
    if msg:
        await reply_with_auto_delete(msg, txt)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理按钮点击事件"""
    query = update.callback_query
    await query.answer()

    data = query.data

    # 返回菜单
    if data == "back_menu":
        user = query.from_user
        session = Session()
        u = session.query(UserBinding).filter_by(tg_id=user.id).first()
        is_vip = u.is_vip if u else False
        session.close()

        txt = get_menu_text(user, is_vip)
        buttons = get_menu_layout(is_vip)
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))
        return

    # 个人档案
    if data == "me":
        from plugins.me import me_panel
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'effective_message': query.message,
            'message': query.message,
            'callback_query': query,
        })()
        await me_panel(fake_update, context)

    # 签到
    elif data == "checkin":
        from plugins.checkin_bind import checkin
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
            'effective_message': query.message,
        })()
        await checkin(fake_update, context)

    # 银行
    elif data == "bank":
        from plugins.bank import bank_panel
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
            'effective_message': query.message,
        })()
        await bank_panel(fake_update, context)

    # 商店
    elif data == "shop":
        from plugins.shop import shop_main
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
            'effective_message': query.message,
        })()
        await shop_main(fake_update, context)

    # 背包
    elif data == "bag":
        from plugins.bag import my_bag
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
            'effective_message': query.message,
        })()
        await my_bag(fake_update, context)

    # 排行榜
    if data == "hall":
        from plugins.hall import hall_leaderboard
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
            'effective_message': query.message,  # 添加这个属性
        })()
        await hall_leaderboard(fake_update, context)

    # 活跃度
    elif data == "presence":
        from plugins.presence import presence_cmd
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
            'effective_message': query.message,  # 添加这个属性
        })()
        await presence_cmd(fake_update, context)

    # 炼金
    elif data == "forge":
        from plugins.forge import forge_callback
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'callback_query': query,
            'effective_message': query.message,
        })()
        await forge_callback(fake_update, context)

    # 每日任务
    elif data == "daily_tasks":
        from plugins.unified_mission import mission_main
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
            'effective_message': query.message,
            'effective_chat': query.message.chat,
        })()
        await mission_main(fake_update, context, "daily")

    # 幸运转盘
    elif data == "lucky_wheel":
        from plugins.lucky_wheel import wheel_cmd
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
            'effective_message': query.message,
        })()
        await wheel_cmd(fake_update, context)

    # 塔罗
    elif data == "tarot":
        from plugins.fun_games import tarot
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
            'effective_message': query.message,
        })()
        await tarot(fake_update, context)

    # 盲盒
    elif data == "poster":
        from plugins.fun_games import gacha_poster
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
            'effective_message': query.message,
        })()
        await gacha_poster(fake_update, context)

    # 决斗说明
    elif data == "duel_info":
        txt = (
            "⚔️ <b>【 魔 法 少 女 · 决 斗 竞 技 场 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "📜 <b>决斗规则：</b>\n"
            "1️⃣ 回复要挑战的小伙伴消息\n"
            "2️⃣ 发送 <code>/duel 金额</code>\n"
            "3️⃣ 等待对方接受挑战喵~\n"
            "4️⃣ 胜者获得全部赌注！\n\n"
            "<i>\"想成为魔法少女决斗王吗？\n"
            "来试试吧！(｡･ω･｡)ﾉ♡\"</i>\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        buttons = [[InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # VIP中心
    elif data == "vip":
        user = query.from_user
        from database import Session, UserBinding
        session = Session()
        u = session.query(UserBinding).filter_by(tg_id=user.id).first()
        is_vip = u.is_vip if u else False
        session.close()

        if is_vip:
            txt = (
                "👑 <b>【 皇 家 · 星 辰 殿 堂 】</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "✨ <b>欢迎回来，尊贵的 Master~</b> ✨\n\n"
                "💠 <b>:: 已 觉 醒 之 力 ::</b>\n\n"
                "🚀 4K 极速通道 · <b>已开启</b>\n"
                "🏰 皇家金库 · <b>0 手续费</b>\n"
                "💰 魔力加成 · <b>签到 1.5x</b>\n"
                "⚒️ 炼金工坊 · <b>锻造 5 折</b>\n"
                "🔮 命运眷顾 · <b>塔罗 5 折</b>\n"
                "🎁 魔力转赠 · <b>免手续费</b>\n"
                "⚔️ 决斗祝福 · <b>+5% 胜率</b>\n"
                "🏆 星辰称号 · <b>尊贵头衔</b>\n"
                "🏦 银行利息 · <b>日息 1%</b>\n"
                "🛡️ 连败安慰 · <b>额外奖励</b>\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "<i>「星光永远照耀您~💖」</i>"
            )
        else:
            txt = (
                "🗝️ <b>【 觉 醒 之 门 】</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "✨ <b>准备好觉醒成为真正的皇家魔法少女了吗？</b> ✨\n\n"
                "💠 <b>:: 觉 醒 后 获 得 的 力 量 ::</b>\n\n"
                "🚀 4K 极速通道 · 画质飞跃\n"
                "🏰 皇家金库 · 0 手续费\n"
                "💰 魔力加成 · 签到 1.5x\n"
                "⚒️ 炼金工坊 · 锻造 5 折\n"
                "🔮 命运眷顾 · 塔罗 5 折\n"
                "🎁 魔力转赠 · 免手续费\n"
                "⚔️ 决斗祝福 · +5% 胜率\n"
                "🏆 星辰称号 · 尊贵头衔\n"
                "🏦 银行利息 · 日息 1%\n"
                "🛡️ 连败安慰 · 额外奖励\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "<i>「仅需一次证明材料，即可永久觉醒喵~(｡･ω･｡)ﾉ♡」</i>"
            )
        buttons = [[InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 升级VIP
    elif data == "upgrade_vip":
        txt = (
            "🗝️ <b>【 觉 醒 之 门 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "✨ <b>准备好觉醒成为真正的皇家魔法少女了吗？</b> ✨\n\n"
            "💠 <b>:: 觉 醒 后 获 得 的 力 量 ::</b>\n\n"
            "🚀 4K 极速通道 · 画质飞跃\n"
            "🏰 皇家金库 · 0 手续费\n"
            "💰 魔力加成 · 签到 1.5x\n"
            "⚒️ 炼金工坊 · 锻造 5 折\n"
            "🔮 命运眷顾 · 塔罗 5 折\n"
            "🎁 魔力转赠 · 免手续费\n"
            "⚔️ 决斗祝福 · +5% 胜率\n"
            "🏆 星辰称号 · 尊贵头衔\n"
            "🏦 银行利息 · 日息 1%\n"
            "🛡️ 连败安慰 · 额外奖励\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "<i>「仅需一次证明材料，即可永久觉醒喵~(｡･ω･｡)ﾉ♡」</i>"
        )
        buttons = [
            [InlineKeyboardButton("📩 申请觉醒", callback_data="apply_vip")],
            [InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]
        ]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 申请VIP
    elif data == "apply_vip":
        txt = (
            "📜 <b>【 V I P · 觉 醒 仪 式 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "请在 <b>私聊</b> 中使用以下命令申请觉醒喵~\n\n"
            "<code>/applyvip</code>\n\n"
            "📋 <b>觉醒步骤：</b>\n"
            "1️⃣ 私聊看板娘发送 <code>/applyvip</code>\n"
            "2️⃣ 发送证明材料喵\n"
            "3️⃣ 等待审核通过\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "<i>\"点击下方按钮直接跳转私聊哦 (｡•̀ᴗ-)✧\"</i>"
        )
        buttons = [
            [InlineKeyboardButton("📩 前往私聊申请", url=f"https://t.me/{context.bot.username}")],
            [InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]
        ]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 帮助手册
    elif data == "help_manual":
        txt = (
            "📖 <b>【 魔 法 指 南 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            "🔗 <b>基础魔法：</b>\n"
            "• <code>/bind</code> — 缔结魔法契约 (必做!)\n"
            "• <code>/daily</code> — 每日签到领魔力\n"
            "• <code>/me</code> — 查看魔法少女档案\n\n"

            "📋 <b>每日任务：</b>\n"
            "• <code>/tasks</code> — 查看每日任务\n"
            "• <code>/wheel</code> — 幸运转盘抽奖\n"
            "• <code>/active</code> — 查看活跃度\n"
            "• <code>/rank</code> — 活跃排行榜\n\n"

            "💰 <b>皇家金库：</b>\n"
            "• <code>/bank</code> — 打开魔法金库\n"
            "• <code>/shop</code> — 魔法商店\n"
            "• <code>/gift</code> — 转赠给小伙伴\n\n"

            "🔮 <b>娱乐时光：</b>\n"
            "• <code>/tarot</code> — 塔罗牌占卜\n"
            "• <code>/poster</code> — 魔法盲盒\n"
            "• <code>/airdrop</code> — 幸运空投(管理员)\n\n"

            "⚔️ <b>战斗竞技：</b>\n"
            "• <code>/duel</code> — 魔法少女决斗\n"
            "• <code>/hall</code> — 战力排行榜\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "<i>\"遇到困难的话...随时召唤看板娘哦！(｡•̀ᴗ-)✧\"</i>"
        )
        buttons = [[InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))


def register(app):
    app.add_handler(CommandHandler("start", start_menu))
    app.add_handler(CommandHandler("menu", start_menu))
    app.add_handler(CommandHandler("help", help_manual))
    # 只处理其他模块未匹配的回调
    # 排除: admin_(管理员), vip_(VIP审核), duel_(决斗), forge_(锻造操作), me_(个人档案操作)
    #       buy_(购买), shop_home_(商店首页), wheel_(转盘), airdrop_(空投), mission_(悬赏任务)
    app.add_handler(CallbackQueryHandler(button_callback, pattern="^(?!admin_|vip_|duel_accept|duel_reject|forge_again|me_|buy_|shop_home|wheel_spin|wheel_back|airdrop_open|mission_|mission_tab_).*$"), group=1)
