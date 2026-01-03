"""
工具函数模块
提供消息自毁等通用功能
"""

import asyncio
from typing import Optional
from telegram import Message, CallbackQuery, Update, InlineKeyboardButton, InlineKeyboardMarkup
from config import Config


# 统一的未绑定提示消息
UNBOUND_MESSAGE = """
💔 <b>【 未 缔 契 约 】</b>

我看不到您的灵魂波长... (´;ω;`)

━━━━━━━━━━━━━━━━━━
📝 <b>请先发送：</b>
<code>/bind 你的Emby用户名</code>

🎁 <b>新手福利：</b>
• 💰 100 MP 魔力
• 🎰 3个盲盒券
• ⚒️ 1张锻造券
• 🗡️ 新手武器 (+10战力)
━━━━━━━━━━━━━━━━━━

<i>\"绑定后即可开始冒险喵~(｡•̀ᴗ-)✧\"</i>
"""


async def get_unbound_message(user_first_name: str = None) -> str:
    """获取统一的未绑定提示消息"""
    if user_first_name:
        return f"""
💔 <b>【 未 缔 契 约 】</b>

{user_first_name}酱，我看不到您的灵魂波长... (´;ω;`)

━━━━━━━━━━━━━━━━━━
📝 <b>请先发送：</b>
<code>/bind 你的Emby用户名</code>

🎁 <b>新手福利：</b>
• 💰 100 MP 魔力
• 🎰 3个盲盒券
• ⚒️ 1张锻造券
• 🗡️ 新手武器 (+10战力)
━━━━━━━━━━━━━━━━━━

<i>\"绑定后即可开始冒险喵~(｡•̀ᴗ-)✧\"</i>
"""
    return UNBOUND_MESSAGE


async def self_destruct(message: Optional[Message], delay: Optional[int] = None) -> None:
    """
    消息自毁函数

    Args:
        message: 要删除的消息对象（可能为 None，比如私聊消息）
        delay: 延迟秒数，None 则使用配置默认值
    """
    if message is None:
        return

    # 群组消息才自毁，私聊不删除
    if message.chat.type == "private":
        return

    # 如果配置为 0，不删除
    delay = delay if delay is not None else Config.MESSAGE_DELETE_DELAY
    if delay <= 0:
        return

    try:
        await asyncio.sleep(delay)
        await message.delete()
    except Exception:
        # 删除失败（比如消息已被删除、机器人权限不足等）静默忽略
        pass


async def reply_with_auto_delete(
    message: Message,
    text: str,
    delay: Optional[int] = None,
    **kwargs
) -> Optional[Message]:
    """
    发送回复消息并在延迟后自动删除

    Args:
        message: 原始消息对象
        text: 回复文本
        delay: 延迟秒数，None 则使用配置默认值
        **kwargs: 传递给 reply_html 的其他参数

    Returns:
        发送的消息对象（如果发送成功）
    """
    if not message:
        return None

    reply = await message.reply_html(text, **kwargs)

    # 只在群组中自毁
    if reply and reply.chat.type != "private":
        delay = delay if delay is not None else Config.MESSAGE_DELETE_DELAY
        if delay > 0:
            asyncio.create_task(_delete_after(reply, delay))

    return reply


# ==========================================
# 按钮权限检查
# ==========================================

def register_button_owner(context, message_id: int, user_id: int) -> None:
    """
    注册按钮所有者，用于权限检查

    Args:
        context: Bot context
        message_id: 消息ID
        user_id: 发起菜单的用户ID
    """
    if not context.bot_data:
        context.bot_data = {}
    if "button_owners" not in context.bot_data:
        context.bot_data["button_owners"] = {}

    # 使用 message_id 作为键存储 user_id
    context.bot_data["button_owners"][message_id] = user_id


def check_button_owner(context, query: CallbackQuery) -> bool:
    """
    检查点击按钮的用户是否是菜单发起者

    Args:
        context: Bot context
        query: CallbackQuery 对象

    Returns:
        True 如果用户有权限，False 否则
    """
    message_id = query.message.message_id
    user_id = query.from_user.id

    if not context.bot_data:
        return True  # 没有数据时允许通过（兼容性）

    owners = context.bot_data.get("button_owners", {})
    owner_id = owners.get(message_id)

    # 如果没有记录所有者，允许任何人点击（兼容性）
    if owner_id is None:
        return True

    # 检查是否是所有者
    return user_id == owner_id


async def deny_button_access(query: CallbackQuery) -> None:
    """
    拒绝非所有者的按钮点击

    Args:
        query: CallbackQuery 对象
    """
    await query.answer("⚠️ 这不是你的菜单哦！", show_alert=True)


async def _delete_after(message: Message, delay: int) -> None:
    """内部函数：延迟删除消息"""
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except Exception:
        pass


async def send_with_auto_delete(
    bot,
    chat_id: int,
    text: str,
    delay: Optional[int] = None,
    **kwargs
) -> Optional[Message]:
    """
    发送消息并在延迟后自动删除（群组有效）

    Args:
        bot: Bot 实例
        chat_id: 目标聊天ID
        text: 消息文本
        delay: 延迟秒数，None 则使用配置默认值
        **kwargs: 传递给 send_message 的其他参数

    Returns:
        发送的消息对象（如果发送成功）
    """
    msg = await bot.send_message(chat_id, text, **kwargs)

    # 只在群组中自毁
    if msg and msg.chat.type != "private":
        delay = delay if delay is not None else Config.MESSAGE_DELETE_DELAY
        if delay > 0:
            asyncio.create_task(_delete_after(msg, delay))

    return msg


async def edit_with_auto_delete(
    query: CallbackQuery,
    text: str,
    delay: Optional[int] = None,
    **kwargs
) -> Optional[Message]:
    """
    编辑回调消息并在延迟后自动删除

    Args:
        query: CallbackQuery 对象
        text: 新文本
        delay: 延迟秒数，None 则使用配置默认值
        **kwargs: 传递给 edit_message_text 的其他参数

    Returns:
        编辑后的消息对象（如果成功）
    """
    if not query:
        return None

    msg = await query.edit_message_text(text, **kwargs)

    # 只在群组中自毁
    if msg and msg.chat.type != "private":
        delay = delay if delay is not None else Config.MESSAGE_DELETE_DELAY
        if delay > 0:
            asyncio.create_task(_delete_after(msg, delay))

    return msg


async def smart_reply(
    update: Update,
    text: str,
    buttons=None,
    parse_mode='HTML',
    delay: Optional[int] = None,
    context=None
) -> Optional[Message]:
    """
    智能响应函数：自动检测是回调还是普通消息，选择编辑或发送新消息

    Args:
        update: Update 对象
        text: 响应文本
        buttons: 按钮列表
        parse_mode: 解析模式
        delay: 自毁延迟（仅群组有效）
        context: Bot context (用于按钮权限管理)

    Returns:
        发送/编辑的消息对象
    """
    query = getattr(update, 'callback_query', None)
    
    # 如果是回调，编辑原消息
    if query and query.message:
        keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="back_menu")]] if buttons is None else buttons
        try:
            msg = await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=parse_mode)
            return msg
        except Exception:
            pass
    
    # 不是回调或编辑失败，发送新消息
    msg = update.effective_message
    if not msg:
        return None

    if buttons is None:
        reply = await msg.reply_html(text)
    else:
        reply = await msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=parse_mode)

    # 注册按钮所有者（如果有按钮和context）
    if reply and buttons and context:
        user_id = update.effective_user.id if update.effective_user else None
        if user_id:
            register_button_owner(context, reply.message_id, user_id)

    # 只在群组中自毁
    if reply and reply.chat.type != "private":
        delay = delay if delay is not None else Config.MESSAGE_DELETE_DELAY
        if delay > 0:
            asyncio.create_task(_delete_after(reply, delay))

    return reply
