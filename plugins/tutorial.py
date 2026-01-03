"""
新手教程模块
引导新用户完成第一步：绑定 → 签到 → 查看任务
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding


TUTORIAL_STEPS = {
    0: {
        "title": "🌸 欢迎来到云海魔法学院！",
        "content": (
            "👋 嗨！我是你的魔法向导 <b>看板娘</b> 喵~\n\n"
            "让我带你开启魔法之旅吧！\n\n"
            "📚 <b>课程大纲：</b>\n"
            "第一步 ⭐ 缔结魔法契约\n"
            "第二步 🍬 每日签到领魔力\n"
            "第三步 📋 完成新手任务\n\n"
            "<i>准备好了吗？点击下方按钮开始喵！(≧◡≦)</i>"
        ),
        "button": "🌟 开始教程",
        "next_step": 1
    },
    1: {
        "title": "📖 第一步：缔结魔法契约",
        "content": (
            "想要成为魔法少女，首先要缔结契约喵！\n\n"
            "📝 <b>操作方法：</b>\n"
            "发送命令：<code>/bind 你的Emby账号</code>\n\n"
            "💡 <b>小贴士：</b>\n"
            "Emby账号就是你看电影用的账号名\n\n"
            "<i>完成后点击下方按钮继续~</i>"
        ),
        "button": "✅ 我已绑定",
        "next_step": 2
    },
    2: {
        "title": "🍬 第二步：每日签到",
        "content": (
            "恭喜完成第一步！现在来领取今日的魔力补给喵~\n\n"
            "📝 <b>操作方法：</b>\n"
            "发送命令：<code>/checkin</code> 或 <code>/daily</code>\n\n"
            "🎁 <b>签到福利：</b>\n"
            "• 每天都有魔力奖励\n"
            "• 有概率触发 <b>双倍暴击</b> 喔！\n"
            "• 连续签到有额外奖励\n\n"
            "<i>签完回来点击继续~</i>"
        ),
        "button": "✅ 我已签到",
        "next_step": 3
    },
    3: {
        "title": "📋 第三步：查看每日任务",
        "content": (
            "太棒了！现在来看看今天的任务吧喵~\n\n"
            "📝 <b>操作方法：</b>\n"
            "发送命令：<code>/mission</code>\n\n"
            "🎯 <b>任务类型：</b>\n"
            "• 💬 聊天任务（在群里说话）\n"
            "• ⚔️ 决斗任务（和其他玩家PK）\n"
            "• 🔮 占卜任务（抽盲盒）\n"
            "• 还有很多更多...\n\n"
            "<i>完成任务有奖励喵！</i>"
        ),
        "button": "✅ 我明白了",
        "next_step": 4
    },
    4: {
        "title": "🎉 毕业啦！",
        "content": (
            "恭喜你完成了新手教程！\n\n"
            "🌟 <b>你已经掌握：</b>\n"
            "✅ 缔结魔法契约\n"
            "✅ 每日签到领魔力\n"
            "✅ 查看每日任务\n\n"
            "🎮 <b>接下来可以：</b>\n"
            "• <code>/start</code> — 打开主菜单\n"
            "• <code>/duel</code> — 和其他玩家决斗\n"
            "• <code>/forge</code> — 锻造武器\n"
            "• <code>/tarot</code> — 抽取命运盲盒\n\n"
            "🗼 <b>【通天塔】</b> — 无限爬塔挑战\n"
            "   输入 <code>/tower</code> 开始爬塔\n"
            "   每10层有强大Boss，击败有奖励！\n\n"
            "💫 <b>【灵魂共鸣】</b> — 与看板娘互动\n"
            "   输入 <code>/me</code> 打开个人面板\n"
            "   点击「灵魂共鸣」增加好感度\n"
            "   有几率抽到UR/SSR/SR特殊互动！\n\n"
            "🏆 <b>最后提醒：</b>\n"
            "每天记得签到和做任务哦！\n"
            "看板娘会陪伴你成长的喵~ 💖"
        ),
        "button": "🚀 开始冒险",
        "next_step": None
    }
}


def get_tutorial_message(step: int) -> dict:
    """获取指定步骤的教程消息"""
    return TUTORIAL_STEPS.get(step, TUTORIAL_STEPS[0])


async def tutorial_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始教程"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    # 检查用户状态
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        is_bound = user and user.emby_account

    step_data = get_tutorial_message(0)

    # 如果已经绑定，可以跳过第一步
    if is_bound and step_data["next_step"] == 1:
        step_data = get_tutorial_message(1)

    buttons = [[InlineKeyboardButton(step_data["button"], callback_data=f"tutorial_step_{step_data['next_step']}")]]

    await msg.reply_html(
        f"{step_data['title']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{step_data['content']}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def tutorial_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理教程按钮点击"""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split('_')
    step = int(parts[2]) if len(parts) > 2 else 0

    if step not in TUTORIAL_STEPS:
        # 教程结束
        await query.edit_message_text(
            "🎉 <b>教程已结束！</b>\n\n"
            "输入 <code>/start</code> 开始你的冒险吧！"
        )
        return

    step_data = TUTORIAL_STEPS[step]

    if step_data["next_step"] is None:
        # 最后一步，显示完成消息
        await query.edit_message_text(
            f"{step_data['title']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{step_data['content']}"
        )
    else:
        # 显示下一步
        next_step_data = TUTORIAL_STEPS[step_data["next_step"]]
        buttons = [[InlineKeyboardButton(next_step_data["button"], callback_data=f"tutorial_step_{next_step_data['next_step']}")]]

        await query.edit_message_text(
            f"{step_data['title']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{step_data['content']}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def quick_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """快速指南（简化版教程）"""
    msg = update.effective_message
    if not msg:
        return

    text = (
        "📖 <b>【 新 手 快 速 指 南 】</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👋 欢迎来到云海魔法学院喵！\n\n"
        "🌟 <b>第一步：绑定账号</b>\n"
        "  <code>/bind 你的Emby账号</code>\n\n"
        "🍬 <b>第二步：每日签到</b>\n"
        "  <code>/checkin</code>\n\n"
        "📋 <b>第三步：查看任务</b>\n"
        "  <code>/mission</code>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎮 <b>更多功能：</b>\n"
        "🗼 <code>/tower</code> — 通天塔挑战\n"
        "💫 <code>/me</code> — 灵魂共鸣\n"
        "⚔️ <code>/duel</code> — 玩家决斗\n"
        "⚒️ <code>/forge</code> — 锻造武器\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 输入 <code>/start</code> 打开主菜单\n"
        "💡 输入 <code>/tutorial</code> 查看完整教程\n"
    )

    buttons = [
        [InlineKeyboardButton("🎓 开始完整教程", callback_data="tutorial_start")],
        [InlineKeyboardButton("🚀 返回主菜单", callback_data="back_menu")]
    ]

    await msg.reply_html(text, reply_markup=InlineKeyboardMarkup(buttons))


def register(app):
    app.add_handler(CommandHandler("tutorial", tutorial_start))
    app.add_handler(CommandHandler("guide", quick_guide))
    app.add_handler(CallbackQueryHandler(tutorial_callback, pattern=r"^tutorial_step_"))
