"""
统一错误处理模块 - Error Handler
提供全局错误处理和日志记录功能
"""
import logging
import traceback
from typing import Optional
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from database import get_session, UserBinding

logger = logging.getLogger(__name__)


class GameError(Exception):
    """游戏基础异常类"""

    def __init__(self, message: str, user_message: str = None, code: str = None):
        self.message = message
        self.user_message = user_message or message
        self.code = code
        super().__init__(self.message)


class UserError(GameError):
    """用户操作错误（如余额不足、未绑定等）"""


class SystemError(GameError):
    """系统错误（如数据库连接失败等）"""


class BusinessError(GameError):
    """业务逻辑错误"""


# ==========================================
# 错误处理器
# ==========================================

class ErrorHandler:
    """
    统一错误处理器
    """

    # 错误码定义
    ERROR_NOT_BOUND = "USER_NOT_BOUND"
    ERROR_INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    ERROR_INVALID_INPUT = "INVALID_INPUT"
    ERROR_COOLDOWN = "COOLDOWN"
    ERROR_DAILY_LIMIT = "DAILY_LIMIT"
    ERROR_PERMISSION_DENIED = "PERMISSION_DENIED"
    ERROR_SYSTEM = "SYSTEM_ERROR"

    # 用户友好的错误消息
    ERROR_MESSAGES = {
        ERROR_NOT_BOUND: "💔 请先绑定账号喵！\n\n使用 <code>/bind 账号</code> 绑定后再来~",
        ERROR_INSUFFICIENT_FUNDS: "💸 魔力不足喵！",
        ERROR_INVALID_INPUT: "⚠️ 输入的内容有误，请检查后重试",
        ERROR_COOLDOWN: "⏰ 操作太快啦！请稍后再试",
        ERROR_DAILY_LIMIT: "🚫 今日次数已用完，明天再来吧~",
        ERROR_PERMISSION_DENIED: "🚫 你没有权限执行此操作",
        ERROR_SYSTEM: "⚠️ 系统繁忙，请稍后再试",
    }

    @staticmethod
    async def handle(update: Update, error: Exception,
                    context: ContextTypes.DEFAULT_TYPE = None) -> None:
        """
        统一错误处理入口

        Args:
            update: Telegram Update 对象
            error: 异常对象
            context: Bot Context
        """
        # 记录错误
        ErrorHandler.log_error(error, update, context)

        # 发送用户消息
        await ErrorHandler.notify_user(update, error)

    @staticmethod
    def log_error(error: Exception, update: Update = None,
                  context: ContextTypes.DEFAULT_TYPE = None) -> None:
        """
        记录错误日志

        Args:
            error: 异常对象
            update: Telegram Update 对象
            context: Bot Context
        """
        user_info = ""
        if update and update.effective_user:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name
            user_info = f" | User: {username}({user_id})"

        chat_info = ""
        if update and update.effective_chat:
            chat_info = f" | Chat: {update.effective_chat.id}"

        error_type = type(error).__name__
        error_msg = str(error)

        # 根据错误类型选择日志级别
        if isinstance(error, (UserError, BusinessError)):
            # 用户错误，记录为警告
            logger.warning(f"[{error_type}] {error_msg}{user_info}{chat_info}")
        else:
            # 系统错误，记录为错误并包含堆栈
            logger.error(
                f"[{error_type}] {error_msg}{user_info}{chat_info}\n"
                f"Traceback:\n{traceback.format_exc()}",
                exc_info=True
            )

    @staticmethod
    async def notify_user(update: Update, error: Exception) -> None:
        """
        向用户发送错误通知

        Args:
            update: Telegram Update 对象
            error: 异常对象
        """
        msg = None
        if update:
            msg = update.effective_message

        if not msg:
            return

        # 获取用户友好的错误消息
        if isinstance(error, GameError):
            user_msg = error.user_message
        elif isinstance(error, UserError):
            user_msg = str(error)
        else:
            # 系统错误，使用通用消息
            user_msg = ErrorHandler.ERROR_MESSAGES[ErrorHandler.ERROR_SYSTEM]

        # 发送消息
        try:
            from utils import reply_with_auto_delete
            await reply_with_auto_delete(msg, f"⚠️ <b>{user_msg}</b>")
        except Exception as e:
            logger.error(f"发送错误消息失败: {e}")

    @staticmethod
    def get_user_error_message(error_code: str, detail: str = None) -> str:
        """
        获取标准错误消息

        Args:
            error_code: 错误码
            detail: 详细信息

        Returns:
            格式化的错误消息
        """
        base_msg = ErrorHandler.ERROR_MESSAGES.get(
            error_code,
            ErrorHandler.ERROR_MESSAGES[ErrorHandler.ERROR_SYSTEM]
        )
        if detail:
            return f"{base_msg}\n\n<i>{detail}</i>"
        return base_msg


# ==========================================
# 装饰器
# ==========================================

def handle_errors(user_message: str = "操作失败，请稍后再试喵~",
                  log_exception: bool = True):
    """
    错误处理装饰器

    Args:
        user_message: 向用户显示的默认错误消息
        log_exception: 是否记录异常日志

    使用方式：
        @handle_errors("签到失败")
        async def my_command(self, update, context):
            ...
    """
    def decorator(func):
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            try:
                return await func(self, update, context, *args, **kwargs)
            except GameError as e:
                # 游戏错误，使用自定义消息
                await ErrorHandler.handle(update, e, context)
                return None
            except Exception as e:
                # 其他错误
                if log_exception:
                    logger.error(f"未捕获的异常 in {func.__name__}: {e}", exc_info=True)

                msg = update.effective_message
                if msg:
                    from utils import reply_with_auto_delete
                    await reply_with_auto_delete(msg, f"⚠️ <b>{user_message}</b>")
                return None
        return wrapper
    return decorator


def safe_execute(default_return=None, reraise: bool = False):
    """
    安全执行装饰器，确保异常不会中断程序

    Args:
        default_return: 异常时的返回值
        reraise: 是否重新抛出异常

    使用方式：
        @safe_execute(default_return=False)
        async def risky_operation():
            ...
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"异常 in {func.__name__}: {e}", exc_info=True)
                if reraise:
                    raise
                return default_return

        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"异常 in {func.__name__}: {e}", exc_info=True)
                if reraise:
                    raise
                return default_return

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


# ==========================================
# 便捷函数
# ==========================================

async def require_user(user_id: int, update: Update = None) -> Optional[UserBinding]:
    """
    检查用户是否已绑定，未绑定则抛出异常

    Args:
        user_id: 用户ID
        update: Update 对象

    Returns:
        UserBinding 对象

    Raises:
        UserError: 用户未绑定
    """
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user or not user.emby_account:
            raise UserError(
                "用户未绑定",
                ErrorHandler.ERROR_MESSAGES[ErrorHandler.ERROR_NOT_BOUND],
                ErrorHandler.ERROR_NOT_BOUND
            )
        return user


async def require_balance(user: UserBinding, amount: int,
                          item_name: str = "此物品") -> None:
    """
    检查用户余额，不足则抛出异常

    Args:
        user: 用户对象
        amount: 所需金额
        item_name: 物品名称

    Raises:
        UserError: 余额不足
    """
    if (user.points or 0) < amount:
        raise UserError(
            f"用户余额不足: 需要{amount}, 拥有{user.points or 0}",
            f"{ErrorHandler.ERROR_MESSAGES[ErrorHandler.ERROR_INSUFFICIENT_FUNDS]}\n\n"
            f"{item_name} 需要 {amount} MP\n"
            f"当前余额：{user.points or 0} MP",
            ErrorHandler.ERROR_INSUFFICIENT_FUNDS
        )


def validate_range(value: int, min_val: int, max_val: int,
                  name: str = "数值") -> None:
    """
    验证数值范围，不符合则抛出异常

    Args:
        value: 待验证值
        min_val: 最小值
        max_val: 最大值
        name: 数值名称

    Raises:
        UserError: 数值超出范围
    """
    if value < min_val or value > max_val:
        raise UserError(
            f"{name}超出范围: {value} not in [{min_val}, {max_val}]",
            f"⚠️ {name}必须在 {min_val} 到 {max_val} 之间",
            ErrorHandler.ERROR_INVALID_INPUT
        )
