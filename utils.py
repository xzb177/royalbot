"""
工具函数模块
提供消息自毁等通用功能
"""

import asyncio
from typing import Optional
from telegram import Message, CallbackQuery
from config import Config


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
