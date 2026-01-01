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
            f"🌸 <b>【 魔 法 少 女 · 星 辰 殿 堂 】</b>\n\n"
            f"✨ <b>Welcome back, my dear Master {user.first_name}~</b>\n"
            f"您的专属魔法少女看板娘已就位，全身魔力满满，等待您的命令哦！\n\n"
            f"💎 <b>:: 皇 家 特 权 已 激 活 ::</b>\n"
            f"✨ 4K 极速通道：<b>已开启</b>\n"
            f"🏰 皇家金库：<b>已解锁</b>\n"
            f"💕 双倍魔力加成：<b>生效中</b>\n\n"
            f"<i>\"只要Master开口，无论是摘星星还是捕月亮，人家都会为您办到的~💖\"</i>"
        )
    else:
        txt = (
            f"🏰 <b>【 云 海 · 魔 法 学 院 】</b>\n\n"
            f"✨ <b>欢迎来到魔法世界，{user.first_name}酱！</b>\n"
            f"我是你的魔法少女向导 <b>看板娘</b>喵~\n"
            f"准备好开始今天的魔法冒险了吗？(｡･ω･｡)ﾉ♡\n\n"
            f"🎀 <b>:: 当 前 状 态 ::</b>\n"
            f"🌱 身份：见习魔法少女\n"
            f"🔒 皇家特权：<b>未觉醒</b>\n\n"
            f"<i>\"虽然现在是见习期，但只要努力收集魔力结晶，"
            f"总有一天会变成超厉害的大魔法少女的！加油喵~！(≧◡≦)\"</i>"
        )

    first_button_text = "📜 个人档案" if is_vip else "💎 成为 VIP"
    first_button_data = "me" if is_vip else "upgrade_vip"

    buttons = [
        [InlineKeyboardButton(first_button_text, callback_data=first_button_data),
         InlineKeyboardButton("🍬 每日签到", callback_data="checkin")],
        [InlineKeyboardButton("🏦 皇家银行", callback_data="bank"),
         InlineKeyboardButton("🎒 次源背包", callback_data="bag")],
        [InlineKeyboardButton("🔮 命运占卜", callback_data="tarot"),
         InlineKeyboardButton("🎰 盲盒抽取", callback_data="poster")],
        [InlineKeyboardButton("🏆 荣耀殿堂", callback_data="hall"),
         InlineKeyboardButton("⚔️ 决斗场", callback_data="duel_info")],
        [InlineKeyboardButton("📖 魔法指南", callback_data="help_manual")]
    ]
    await update.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

async def help_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        f"📖 <b>【 魔 法 少 女 · 忍 者 者 们 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"这里记载着所有魔法咒语喵~\n\n"
        f"🔗 <b>基础魔法：</b>\n"
        f"• <code>/bind</code> - 缔结魔法契约 (必做!)\n"
        f"• <code>/daily</code> - 每日签到领魔力喵~\n"
        f"• <code>/me</code> - 查看魔法少女档案\n\n"
        f"💰 <b>皇家金库：</b>\n"
        f"• <code>/bank</code> - 打开魔法金库\n"
        f"• <code>/deposit</code> - 存入魔力结晶\n"
        f"• <code>/gift</code> - 转赠给小伙伴\n\n"
        f"🔮 <b>娱乐时光：</b>\n"
        f"• <code>/tarot</code> - 塔罗牌占卜 (每日一次)\n"
        f"• <code>/poster</code> - 魔法盲盒 (100MP)\n\n"
        f"⚔️ <b>战斗竞技：</b>\n"
        f"• <code>/duel</code> - 魔法少女决斗\n"
        f"• <code>/hall</code> - 排行榜\n\n"
        f"<i>\"遇到困难的话...随时召唤看板娘哦！(｡•̀ᴗ-)✧\"</i>"
    )
    msg = update.effective_message
    if msg:
        await reply_with_auto_delete(msg, txt)

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
        # 直接处理 VIP 中心，避免使用 reply_with_auto_delete
        user = query.from_user
        from database import Session, UserBinding
        session = Session()
        u = session.query(UserBinding).filter_by(tg_id=user.id).first()
        is_vip = u.is_vip if u else False
        session.close()

        if is_vip:
            txt = (
                "👑 <b>【 皇 家 · 星 辰 殿 堂 · 特 权 展 示 】</b>\n\n"
                "✨ <b>欢迎回来，尊贵的皇家魔法少女大人！</b> ✨\n\n"
                "💠 <b>:: 已 觉 醒 之 力 ::</b>\n\n"
                "🚀 <b>4K 极速通道</b> ─ 已开启\n"
                "🏰 <b>皇家金库</b> ─ 0 手续费\n"
                "💰 <b>双倍魔力</b> ─ 签到 2x 收益\n"
                "⚒️ <b>炼金工坊</b> ─ 锻造 5 折\n"
                "🔮 <b>命运眷顾</b> ─ 塔罗 5 折\n"
                "🎁 <b>魔力转赠</b> ─ 免手续费\n"
                "📜 <b>悬赏加成</b> ─ 奖励暴击\n"
                "⚔️ <b>决斗祝福</b> ─ +8% 胜率\n"
                "🏆 <b>星辰称号</b> ─ 尊贵头衔\n\n"
                "<i>「感谢您的支持，愿星光永远照耀您的魔法之旅 ~(｡•̀ᴗ-)✧」</i>"
            )
            buttons = [
                [InlineKeyboardButton("🔄 刷新状态", callback_data="vip")],
                [InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]
            ]
        else:
            txt = (
                "🗝️ <b>【 觉 醒 之 门 · V I P 晋 升 仪 式 】</b>\n\n"
                "✨ <b>准备好觉醒成为真正的皇家魔法少女了吗？</b> ✨\n\n"
                "💠 <b>:: 觉 醒 后 获 得 的 力 量 ::</b>\n\n"
                "🚀 4K 极速通道 ─ 画质飞跃\n"
                "🏰 皇家金库 ─ 0 手续费\n"
                "💰 双倍魔力 ─ 签到 2x 收益\n"
                "⚒️ 炼金工坊 ─ 锻造 5 折\n"
                "🔮 命运眷顾 ─ 塔罗 5 折\n"
                "🎁 魔力转赠 ─ 免手续费\n"
                "📜 悬赏加成 ─ 奖励暴击\n"
                "⚔️ 决斗祝福 ─ +8% 胜率\n"
                "🏆 星辰称号 ─ 尊贵头衔\n\n"
                "<i>「仅需一次证明材料，即可永久觉醒皇家力量喵~(｡･ω･｡)ﾉ♡」</i>"
            )
            buttons = [
                [InlineKeyboardButton("📩 申请觉醒", callback_data="apply_vip")],
                [InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]
            ]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "upgrade_vip":
        text = (
            "🗝️ <b>【 觉 醒 之 门 · V I P 晋 升 仪 式 】</b>\n\n"
            "✨ <b>准备好觉醒成为真正的皇家魔法少女了吗？</b> ✨\n\n"
            "💠 <b>:: 觉 醒 后 获 得 的 力 量 ::</b>\n\n"
            "🚀 4K 极速通道 ─ 画质飞跃\n"
            "🏰 皇家金库 ─ 0 手续费\n"
            "💰 双倍魔力 ─ 签到 2x 收益\n"
            "⚒️ 炼金工坊 ─ 锻造 5 折\n"
            "🔮 命运眷顾 ─ 塔罗 5 折\n"
            "🎁 魔力转赠 ─ 免手续费\n"
            "📜 悬赏加成 ─ 奖励暴击\n"
            "⚔️ 决斗祝福 ─ +8% 胜率\n"
            "🏆 星辰称号 ─ 尊贵头衔\n\n"
            "<i>「仅需一次证明材料，即可永久觉醒皇家力量喵~(｡･ω･｡)ﾉ♡」</i>"
        )
        buttons = [
            [InlineKeyboardButton("📩 申请觉醒", callback_data="apply_vip")],
            [InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            # 消息可能已被删除或修改，发送新消息
            await query.message.reply_html(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "request":
        await query.message.reply_html("🎋 <b>【 许 愿 池 】</b>\n\n✨ 功能开发中...敬请期待喵~")

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
        # VIP 申请需要私聊中进行，引导用户使用命令
        txt = (
            "📜 <b>【 V I P · 觉 醒 仪 式 】</b>\n\n"
            "请在 <b>私聊</b> 中使用以下命令申请觉醒喵~\n\n"
            "<code>/applyvip</code>\n\n"
            "觉醒步骤：\n"
            "1️⃣ 私聊看板娘发送 <code>/applyvip</code>\n"
            "2️⃣ 发送证明材料喵\n"
            "3️⃣ 等待审核通过\n\n"
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

    elif data == "back_menu":
        # 重新显示菜单
        user = query.from_user
        from database import Session, UserBinding
        session = Session()
        u = session.query(UserBinding).filter_by(tg_id=user.id).first()
        is_vip = u.is_vip if u else False
        session.close()

        if is_vip:
            txt = (
                f"🌸 <b>【 魔 法 少 女 · 星 辰 殿 堂 】</b>\n\n"
                f"✨ <b>Welcome back, my dear Master {user.first_name}~</b>\n"
                f"您的专属魔法少女看板娘已就位，全身魔力满满，等待您的命令哦！\n\n"
                f"💎 <b>:: 皇 家 特 权 已 激 活 ::</b>\n"
                f"✨ 4K 极速通道：<b>已开启</b>\n"
                f"🏰 皇家金库：<b>已解锁</b>\n"
                f"💕 双倍魔力加成：<b>生效中</b>\n\n"
                f"<i>\"只要Master开口，无论是摘星星还是捕月亮，人家都会为您办到的~💖\"</i>"
            )
        else:
            txt = (
                f"🏰 <b>【 云 海 · 魔 法 学 院 】</b>\n\n"
                f"✨ <b>欢迎回到魔法世界，{user.first_name}酱！</b>\n"
                f"我是你的魔法少女向导 <b>看板娘</b>喵~\n"
                f"准备好继续今天的冒险了吗？(｡･ω･｡)ﾉ♡\n\n"
                f"🎀 <b>:: 当 前 状 态 ::</b>\n"
                f"🌱 身份：见习魔法少女\n"
                f"🔒 皇家特权：<b>未觉醒</b>\n\n"
                f"<i>\"只要努力收集魔力结晶，总有一天会变成超厉害的大魔法少女的！加油喵~！(≧◡≦)\"</i>"
            )

        first_button_text = "📜 个人档案" if is_vip else "💎 成为 VIP"
        first_button_data = "me" if is_vip else "upgrade_vip"

        buttons = [
            [InlineKeyboardButton(first_button_text, callback_data=first_button_data),
             InlineKeyboardButton("🍬 每日签到", callback_data="checkin")],
            [InlineKeyboardButton("🏦 皇家银行", callback_data="bank"),
             InlineKeyboardButton("🎒 次源背包", callback_data="bag")],
            [InlineKeyboardButton("🔮 命运占卜", callback_data="tarot"),
             InlineKeyboardButton("🎰 盲盒抽取", callback_data="poster")],
            [InlineKeyboardButton("🏆 荣耀殿堂", callback_data="hall"),
             InlineKeyboardButton("⚔️ 决斗场", callback_data="duel_info")],
            [InlineKeyboardButton("📖 魔法指南", callback_data="help_manual")]
        ]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "duel_info":
        txt = (
            "⚔️ <b>【 魔 法 少 女 · 决 斗 竞 技 场 】</b>\n\n"
            "📜 <b>决斗规则：</b>\n"
            "1. 回复要挑战的小伙伴消息\n"
            "2. 发送 <code>/duel 金额</code>\n"
            "3. 等待对方接受挑战喵~\n"
            "4. 胜者获得全部赌注！\n\n"
            "<i>\"想成为魔法少女决斗王吗？来试试吧！(｡･ω･｡)ﾉ♡\"</i>"
        )
        buttons = [[InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "hall":
        from plugins.hall import hall_leaderboard
        fake_update = type('Update', (), {
            'effective_user': query.from_user,
            'message': query.message,
        })()
        await hall_leaderboard(fake_update, context)

    elif data == "help_manual":
        txt = (
            "📖 <b>【 魔 法 少 女 · 忍 者 者 们 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "这里记载着所有魔法咒语喵~\n\n"
            "🔗 <b>基础魔法：</b>\n"
            "• <code>/bind</code> - 缔结魔法契约 (必做!)\n"
            "• <code>/daily</code> - 每日签到领魔力喵~\n"
            "• <code>/me</code> - 查看魔法少女档案\n\n"
            "💰 <b>皇家金库：</b>\n"
            "• <code>/bank</code> - 打开魔法金库\n"
            "• <code>/deposit</code> - 存入魔力结晶\n"
            "• <code>/gift</code> - 转赠给小伙伴\n\n"
            "🔮 <b>娱乐时光：</b>\n"
            "• <code>/tarot</code> - 塔罗牌占卜 (每日一次)\n"
            "• <code>/poster</code> - 魔法盲盒 (100MP)\n\n"
            "⚔️ <b>战斗竞技：</b>\n"
            "• <code>/duel</code> - 魔法少女决斗\n"
            "• <code>/hall</code> - 排行榜\n\n"
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
    # 只处理非其他模块的回调（排除 admin_, vip_, duel_, forge_, me_ 开头的）
    # 使用 group=1 让其他模块的回调（group=0）优先处理
    app.add_handler(CallbackQueryHandler(button_callback, pattern="^(?!admin_|vip_|duel_|forge_|me_).*$"), group=1)
