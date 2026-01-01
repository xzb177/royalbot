"""
悬赏公会系统 (Mission)
群内数学题抢答，先答对者获得 MP 奖励
"""

from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
from database import Session, UserBinding
from utils import reply_with_auto_delete
import random

# 全局变量：存储每个群的任务 {chat_id: {"answer": str, "reward": int, "msg": Message}}
CURRENT_MISSIONS = {}


async def post_mission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发布新的悬赏任务"""
    chat_id = update.effective_chat.id

    # 防止刷屏：如果当前有未完成任务，不允许发新的
    if chat_id in CURRENT_MISSIONS:
        await reply_with_auto_delete(
            update.message,
            "⚠️ <b>悬赏令已存在！</b>\n请先完成当前的题目！"
        )
        return

    # 生成题目：加减乘混合
    op = random.choice(["+", "-", "*"])
    if op == "*":
        a, b = random.randint(2, 12), random.randint(2, 12)
    else:
        a, b = random.randint(10, 99), random.randint(10, 99)

    if op == "+":
        ans = a + b
    elif op == "-":
        ans = a - b
    else:
        ans = a * b

    # 随机赏金
    reward = random.randint(30, 80)

    txt = (
        f"📜 <b>【 公 会 · 紧 急 悬 赏 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"魔物来袭！急需智慧的魔法师破解护盾！\n\n"
        f"🧠 <b>魔法谜题：</b> <code>{a} {op} {b} = ?</code>\n"
        f"💰 <b>悬赏金额：</b> <b>{reward} MP</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>⚡ 请直接发送 <b>数字答案</b> 抢单！手快有手慢无！</i>"
    )
    msg = await update.message.reply_html(txt)

    # 存储任务信息（包括消息对象，用于答对后删除题目）
    CURRENT_MISSIONS[chat_id] = {
        "answer": str(ans),
        "reward": reward,
        "msg": msg
    }


async def check_mission_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """检查悬赏答案"""
    chat_id = update.effective_chat.id

    # 如果没任务，或者是命令，忽略
    if chat_id not in CURRENT_MISSIONS:
        return

    user_text = update.message.text.strip()
    mission = CURRENT_MISSIONS[chat_id]

    if user_text == mission["answer"]:
        # 回答正确！
        user = update.effective_user
        reward = mission["reward"]

        session = Session()
        u = session.query(UserBinding).filter_by(tg_id=user.id).first()

        if u and u.emby_account:
            # VIP 加成逻辑
            bonus_msg = ""
            if u.is_vip:
                bonus = int(reward * 0.2)  # VIP 多给 20%
                reward += bonus
                bonus_msg = f" (👑 VIP加成 +{bonus})"

            u.points += reward
            session.commit()

            await reply_with_auto_delete(
                update.message,
                f"🎉 <b>悬 赏 完 成 ！</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"⚡ <b>MVP：</b> {user.first_name}\n"
                f"✅ <b>答案：</b> {mission['answer']}\n"
                f"💰 <b>赏金：</b> <b>+{reward} MP</b>{bonus_msg}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>“反应速度好快！不愧是魔导士大人！”</i>"
            )

            # 尝试删除原题目消息
            try:
                await mission["msg"].delete()
            except Exception:
                pass
        else:
            await reply_with_auto_delete(
                update.message,
                "⚠️ 回答正确，但您未绑定账号，赏金消散了... (/bind)"
            )

        session.close()
        # 清除任务
        del CURRENT_MISSIONS[chat_id]


def register(app):
    """注册插件处理器"""
    app.add_handler(CommandHandler("mission", post_mission))
    app.add_handler(CommandHandler("task", post_mission))
    # 监听纯文本消息用于检查答案（排除命令）
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_mission_answer))
