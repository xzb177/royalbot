"""
有奖推送插件
管理员可发送带互动奖励的魔法传讯，用户回复即可获得 MP
"""
import random
from datetime import datetime
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
from config import Config
from utils import reply_with_auto_delete
from database import get_session, UserBinding


# === ⚙️ 配置区域 ===
REWARD_RANGE = (10, 50)         # 每次互动奖励 MP 范围
MAX_REWARD_COUNT = 50          # 每条推送最多奖励人数（防刷分）
VIP_REWARD_MULTIPLIER = 2      # VIP 奖励倍数
REWARD_COOLDOWN_SECONDS = 5    # 防止连续刷屏，同一用户最小间隔


# === 📦 全局存储（ExtBot 不允许动态属性） ===
ACTIVE_PUSHES = {}      # 活跃推送: {message_id: {chat_id, push_id, claimed_users, created_at, ...}}
LAST_REWARD_TIME = {}   # 防刷记录: {user_id: datetime}


# === 导出全局变量供其他模块使用 ===
__all__ = ['ACTIVE_PUSHES', 'LAST_REWARD_TIME']


# ==========================================
# 💬 1. 发送有奖推送 (仅管理员)
# ==========================================
async def cmd_push(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发送有奖魔法传讯（仅管理员）"""
    msg = update.effective_message
    user = msg.from_user

    # 🔒 权限检查
    if user.id != Config.OWNER_ID:
        await reply_with_auto_delete(msg, "⛔ <b>权限不足</b>\n此魔法仅限白名单法师发动喵~")
        return

    # 获取推送内容
    if not context.args:
        await reply_with_auto_delete(
            msg,
            "📢 <b>【 有奖推送帮助 】</b>\n\n"
            "用法：<code>/push 推送内容</code>\n\n"
            "示例：\n"
            "<code>/push 本周新片《魔法少女》上线啦！</code>\n\n"
            "<i>用户回复推送即可获得 MP 奖励喵~</i>"
        )
        return

    content = ' '.join(context.args)

    # 📡 发送魔法传讯
    push_msg = await msg.reply_html(
        f"📜 <b>【 官 方 · 魔 法 传 讯 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{content}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ <b>互动有奖：</b>\n"
        f"👇 <b>回复</b> 这条消息，即可获得魔力馈赠！\n"
        f"<i>(每人限领一次，先到先得喵~)</i>"
    )

    # 💾 记录这条推送消息的元数据
    push_id = f"push_{push_msg.message_id}_{int(datetime.now().timestamp())}"

    # 记录到全局变量（用于快速查找）
    ACTIVE_PUSHES[push_msg.message_id] = {
        'chat_id': msg.chat_id,
        'push_id': push_id,
        'claimed_users': set(),
        'created_at': datetime.now()
    }

    await reply_with_auto_delete(
        msg,
        f"✅ <b>魔法传讯已发布！</b>\n\n"
        f"📋 消息 ID: <code>{push_msg.message_id}</code>\n"
        f"🎁 奖励池: {MAX_REWARD_COUNT} 份\n"
        f"<i>用户回复即可领取奖励喵~</i>"
    )


# ==========================================
# 💬 2. 监听回复 (发放奖励)
# ==========================================
async def check_reply_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """检查用户回复是否为有奖推送，发放奖励"""
    msg = update.message
    if not msg or not msg.reply_to_message:
        return

    user = msg.from_user
    if not user:
        return

    target_msg_id = msg.reply_to_message.message_id

    # 🔍 检查是否为"有奖推送"
    if target_msg_id not in ACTIVE_PUSHES:
        return

    push_data = ACTIVE_PUSHES[target_msg_id]
    claimed_users = push_data['claimed_users']

    # 1. 检查是否领过
    if user.id in claimed_users:
        return  # 领过了，保持安静不刷屏

    # 2. 检查是否领完了
    if len(claimed_users) >= MAX_REWARD_COUNT:
        return

    # 3. 防刷检查：同一用户短时间内不能连续领取
    last_time = LAST_REWARD_TIME.get(user.id)
    if last_time and (datetime.now() - last_time).total_seconds() < REWARD_COOLDOWN_SECONDS:
        return

    # ✅ 发放奖励
    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user.id).first()

        # 用户必须已绑定
        if not u:
            await reply_with_auto_delete(
                msg,
                "⚠️ <b>未缔结契约</b>\n\n"
                "请先使用 <code>/bind</code> 缔结魔法契约，才能领取奖励喵~"
            )
            return

        # 计算奖励
        reward = random.randint(*REWARD_RANGE)

        # VIP 暴击逻辑
        if u.is_vip:
            reward *= VIP_REWARD_MULTIPLIER
            icon = "✨"
            flair = "[VIP暴击]"
        else:
            icon = "💰"
            flair = "[共鸣]"

        u.points += reward
        session.commit()

        # 📝 标记为已领取
        claimed_users.add(user.id)

        # 记录领取时间（防刷）
        LAST_REWARD_TIME[user.id] = datetime.now()

    # 💬 回复用户
    try:
        await msg.reply_html(
            f"{icon} <b>{flair} +{reward} MP</b>\n"
            f"<i>魔力已注入您的契约喵~ (｡•̀ᴗ-)✧</i>",
            disable_notification=True
        )
    except Exception:
        pass  # 发送失败静默忽略


def register(app):
    """注册命令处理器"""
    app.add_handler(CommandHandler("push", cmd_push))
    # 监听所有文本回复消息
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, check_reply_reward))
