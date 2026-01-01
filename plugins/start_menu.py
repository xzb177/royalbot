from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete

async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = Session()
    u = session.query(UserBinding).filter_by(tg_id=user.id).first()
    is_vip = u.is_vip if u else False
    session.close()

    if is_vip:
        txt = (
            f"🌌 <b>【 星 灵 · 指 挥 中 枢 】</b>\n\n"
            f"🥂 <b>Welcome back, Master {user.first_name}.</b>\n"
            f"云海看板娘已就位，全领域魔力充盈，随时听候您的差遣。\n\n"
            f"💠 <b>:: 权 限 激 活 ::</b>\n"
            f"✅ 4K 极速通道：<b>已连接</b>\n"
            f"✅ 皇家银行金库：<b>已开放</b>\n"
            f"✅ 双倍签到魔力：<b>已加持</b>\n\n"
            f"<i>\"只要是您的愿望，无论是天上的星星还是深海的宝藏，我都为您取来！(｡•̀ᴗ-)✧\"</i>"
        )
    else:
        txt = (
            f"🏰 <b>【 云 海 · 冒 险 者 公 会 】</b>\n\n"
            f"✨ <b>欢迎来到魔法世界，{user.first_name}！</b>\n"
            f"我是您的向导 <b>看板娘</b>。准备好开始今天的冒险了吗？\n\n"
            f"💠 <b>:: 当 前 状 态 ::</b>\n"
            f"🌱 身份：见习冒险者\n"
            f"🔒 VIP特权：未解锁\n\n"
            f"<i>\"虽然现在只是见习，但只要努力收集魔力，总有一天您也能成为传说中的大魔导师！加油哦！(ง •_•)ง\"</i>"
        )

    buttons = [
        [InlineKeyboardButton("📜 个人档案", callback_data="me"),
         InlineKeyboardButton("🍬 每日签到", callback_data="checkin")],
        [InlineKeyboardButton("🏦 皇家银行", callback_data="bank"),
         InlineKeyboardButton("🎒 次源背包", callback_data="bag")],
        [InlineKeyboardButton("🔮 命运占卜", callback_data="tarot"),
         InlineKeyboardButton("🎰 盲盒抽取", callback_data="poster")],
        [InlineKeyboardButton("👑 贵族中心", callback_data="vip"),
         InlineKeyboardButton("⚔️ 决斗场", callback_data="duel_info")],
        [InlineKeyboardButton("📖 魔法指南", url="https://t.me/YourChannel")]
    ]
    await update.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

async def help_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        f"📖 <b>【 终 极 · 魔 法 禁 书 目 录 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"这里记载着操作魔力的所有咒语...\n\n"
        f"🔗 <b>基础咒语：</b>\n"
        f"• <code>/bind</code> - 缔结灵魂契约 (必做!)\n"
        f"• <code>/daily</code> - 汲取每日魔力\n"
        f"• <code>/me</code> - 查看魔法档案\n\n"
        f"💰 <b>金融咒语：</b>\n"
        f"• <code>/bank</code> - 打开银行面板\n"
        f"• <code>/deposit</code> - 存入魔力\n"
        f"• <code>/gift</code> - 馈赠好友 (转账)\n\n"
        f"🔮 <b>娱乐咒语：</b>\n"
        f"• <code>/tarot</code> - 命运塔罗牌占卜 (每日一次)\n"
        f"• <code>/poster</code> - 海报盲盒抽取 (100MP)\n\n"
        f"⚔️ <b>战斗与荣耀：</b>\n"
        f"• <code>/duel</code> - 发起魔法决斗\n"
        f"• <code>/hall</code> - 查看荣耀殿堂\n\n"
        f"<i>\"遇到困难记得呼叫管理员大人哦！🆘\"</i>"
    )
    await update.message.reply_html(txt)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理按钮点击事件"""
    query = update.callback_query
    await query.answer()

    data = query.data

    # 导入各模块的处理函数
    if data == "me":
        from plugins.me import me_panel
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
            'effective_chat': query.message.chat
        })()
        await me_panel(fake_update, context)

    elif data == "checkin":
        from plugins.checkin_bind import checkin
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
        })()
        await checkin(fake_update, context)

    elif data == "bank":
        from plugins.bank import bank_panel
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
        })()
        await bank_panel(fake_update, context)

    elif data == "bag":
        from plugins.bag import my_bag
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
        })()
        await my_bag(fake_update, context)

    elif data == "vip":
        from plugins.vip_shop import vip_center
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
        })()
        await vip_center(fake_update, context)

    elif data == "request":
        await query.message.reply_html("🎋 <b>【 许 愿 池 】</b>\n\n✨ 功能开发中...敬请期待！")

    elif data == "dep_all":
        from plugins.bank import deposit
        from database import Session, UserBinding
        session = Session()
        user = session.query(UserBinding).filter_by(tg_id=query.from_user.id).first()
        amount = user.points if user else 0
        session.close()

        if amount > 0:
            fake_update = type('Update', (), {
                'effective_user': query.from_user,
                'message': query.message,
            })()
            context.args = [str(amount)]
            await deposit(fake_update, context)
        else:
            await query.message.reply_html("💸 <b>钱包空空如也！</b>")

    elif data == "with_all":
        from plugins.bank import withdraw
        from database import Session, UserBinding
        session = Session()
        user = session.query(UserBinding).filter_by(tg_id=query.from_user.id).first()
        amount = user.bank_points if user else 0
        session.close()

        if amount > 0:
            fake_update = type('Update', (), {
                'effective_user': query.from_user,
                'message': query.message,
            })()
            context.args = [str(amount)]
            await withdraw(fake_update, context)
        else:
            await query.message.reply_html("🏦 <b>金库空空如也！</b>")

    elif data in ["buy_vip", "pay_vip", "shop"]:
        from plugins.vip_shop import vip_center
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
        })()
        await vip_center(fake_update, context)

    elif data == "apply_vip":
        from plugins.vip_apply import apply_vip_start
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
        })()
        await apply_vip_start(fake_update, context)

    elif data == "tarot":
        from plugins.fun_games import tarot
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
        })()
        await tarot(fake_update, context)

    elif data == "poster":
        from plugins.fun_games import gacha_poster
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
        })()
        await gacha_poster(fake_update, context)

    elif data == "duel_info":
        await query.message.reply_html(
            "⚔️ <b>【 魔 法 决 斗 场 】</b>\n\n"
            "📜 <b>规则：</b>\n"
            "1. 回复要挑战的人的消息\n"
            "2. 发送 <code>/duel 金额</code>\n"
            "3. 等待对方接受挑战\n"
            "4. 胜者获得赌注！\n\n"
            "<i>\"想成为决斗王吗？来试试吧！\"</i>"
        )

def register(app):
    app.add_handler(CommandHandler("start", start_menu))
    app.add_handler(CommandHandler("menu", start_menu))
    app.add_handler(CommandHandler("help", help_manual))
    # 只处理非其他模块的回调（排除 admin_, vip_, duel_, forge_ 开头的）
    app.add_handler(CallbackQueryHandler(button_callback, pattern="^(?!admin_|vip_|duel_|forge_).*$"))
