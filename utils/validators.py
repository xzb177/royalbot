"""
输入验证工具类 - Validators
提供统一的输入验证功能，增强安全性
"""
import re
from typing import Optional, Tuple
from database import UserBinding


class ValidationError(Exception):
    """验证错误异常"""
    def __init__(self, message: str, user_message: str = None):
        self.message = message
        self.user_message = user_message or message


class Validator:
    """
    输入验证工具类
    提供各种输入验证方法
    """

    # ==========================================
    # 用户名验证
    # ==========================================

    @staticmethod
    def validate_emby_username(username: str) -> Tuple[bool, str]:
        """
        验证 Emby 用户名

        Args:
            username: 用户名

        Returns:
            (是否有效, 错误消息)
        """
        if not username:
            return False, "用户名不能为空"

        username = username.strip()

        if len(username) < 2:
            return False, "用户名至少需要 2 个字符"

        if len(username) > 50:
            return False, "用户名最多 50 个字符"

        # 检查特殊字符（只允许字母、数字、下划线、连字符、点）
        if not re.match(r'^[a-zA-Z0-9_.\-]+$', username):
            return False, "用户名只能包含字母、数字、下划线、连字符和点"

        return True, ""

    @staticmethod
    def validate_guild_name(name: str) -> Tuple[bool, str]:
        """
        验证公会名称

        Args:
            name: 公会名称

        Returns:
            (是否有效, 错误消息)
        """
        from config.game_config import guild

        if not name:
            return False, "公会名称不能为空"

        name = name.strip()

        if len(name) < guild.NAME_MIN_LEN:
            return False, f"公会名称至少需要 {guild.NAME_MIN_LEN} 个字符"

        if len(name) > guild.NAME_MAX_LEN:
            return False, f"公会名称最多 {guild.NAME_MAX_LEN} 个字符"

        # 检查敏感词
        sensitive_words = ["管理", "官方", "系统", "robot", "bot", "admin"]
        name_lower = name.lower()
        for word in sensitive_words:
            if word in name_lower:
                return False, f"公会名称不能包含「{word}」"

        return True, ""

    # ==========================================
    # 数值验证
    # ==========================================

    @staticmethod
    def validate_bet_amount(amount: int, user_points: int) -> Tuple[bool, str]:
        """
        验证决斗赌注

        Args:
            amount: 赌注金额
            user_points: 用户余额

        Returns:
            (是否有效, 错误消息)
        """
        from config.game_config import duel

        if amount < duel.MIN_BET:
            return False, f"赌注太小啦！最少需要 {duel.MIN_BET} MP"

        if amount > duel.MAX_BET:
            return False, f"赌注太大啦！最多 {duel.MAX_BET} MP"

        if amount > user_points:
            return False, f"余额不足！你只有 {user_points} MP"

        return True, ""

    @staticmethod
    def validate_positive_integer(value: str, min_val: int = 1,
                                  max_val: int = None) -> Tuple[bool, int, str]:
        """
        验证并转换正整数

        Args:
            value: 字符串值
            min_val: 最小值
            max_val: 最大值

        Returns:
            (是否有效, 转换后的值, 错误消息)
        """
        try:
            num = int(value)
            if num < min_val:
                return False, 0, f"数值不能小于 {min_val}"
            if max_val and num > max_val:
                return False, 0, f"数值不能大于 {max_val}"
            return True, num, ""
        except ValueError:
            return False, 0, "请输入有效的数字"

    # ==========================================
    # 用户验证
    # ==========================================

    @staticmethod
    def validate_user_bound(user: Optional[UserBinding]) -> Tuple[bool, str]:
        """
        验证用户是否已绑定

        Args:
            user: 用户对象

        Returns:
            (是否有效, 错误消息)
        """
        if not user:
            return False, "请先绑定账号喵！\n使用 /bind 账号 绑定后再来~"

        if not user.emby_account:
            return False, "请先绑定账号喵！\n使用 /bind 账号 绑定后再来~"

        return True, ""

    @staticmethod
    def validate_user_balance(user: UserBinding, amount: int,
                             item_name: str = "此物品") -> Tuple[bool, str]:
        """
        验证用户余额

        Args:
            user: 用户对象
            amount: 所需金额
            item_name: 物品名称

        Returns:
            (是否有效, 错误消息)
        """
        balance = user.points or 0
        if balance < amount:
            return False, f"💸 魔力不足喵！\n\n{item_name} 需要 {amount} MP\n当前余额：{balance} MP"

        return True, ""

    # ==========================================
    # 权限验证
    # ==========================================

    @staticmethod
    def validate_button_owner(user_id: int, owner_id: int) -> Tuple[bool, str]:
        """
        验证按钮操作权限

        Args:
            user_id: 操作用户ID
            owner_id: 按钮所有者ID

        Returns:
            (是否有效, 错误消息)
        """
        if user_id != owner_id:
            return False, "这不是你的按钮喵！吃瓜群众请后退~"

        return True, ""

    @staticmethod
    def validate_admin(user_id: int, admin_ids: list) -> Tuple[bool, str]:
        """
        验证管理员权限

        Args:
            user_id: 用户ID
            admin_ids: 管理员ID列表

        Returns:
            (是否有效, 错误消息)
        """
        if user_id not in admin_ids:
            return False, "此功能仅限管理员使用喵！"

        return True, ""

    # ==========================================
    # 字符串验证
    # ==========================================

    @staticmethod
    def validate_text_length(text: str, min_len: int = 1,
                             max_len: int = 1000) -> Tuple[bool, str]:
        """
        验证文本长度

        Args:
            text: 文本内容
            min_len: 最小长度
            max_len: 最大长度

        Returns:
            (是否有效, 错误消息)
        """
        text_len = len(text or "")

        if text_len < min_len:
            return False, f"内容太短啦！至少需要 {min_len} 个字符"

        if text_len > max_len:
            return False, f"内容太长啦！最多 {max_len} 个字符"

        return True, ""

    @staticmethod
    def sanitize_text(text: str, max_length: int = 500) -> str:
        """
        清理文本（移除危险字符）

        Args:
            text: 原始文本
            max_length: 最大长度

        Returns:
            清理后的文本
        """
        if not text:
            return ""

        # 移除控制字符（保留换行和制表符）
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        # 限制长度
        if len(text) > max_length:
            text = text[:max_length] + "..."

        return text.strip()

    # ==========================================
    # 业务验证
    # ==========================================

    @staticmethod
    def validate_daily_limit(current_count: int, limit: int,
                           action_name: str = "此操作") -> Tuple[bool, str]:
        """
        验证每日次数限制

        Args:
            current_count: 当前次数
            limit: 限制次数
            action_name: 操作名称

        Returns:
            (是否有效, 错误消息)
        """
        if current_count >= limit:
            return False, f"今日{action_name}次数已用完喵！\n明天再来吧~"

        return True, ""

    @staticmethod
    def validate_cooldown(last_time, cooldown_seconds: int,
                         action_name: str = "此操作") -> Tuple[bool, int]:
        """
        验证冷却时间

        Args:
            last_time: 上次操作时间
            cooldown_seconds: 冷却秒数
            action_name: 操作名称

        Returns:
            (是否有效, 剩余秒数)
        """
        from datetime import datetime

        if not last_time:
            return True, 0

        elapsed = (datetime.now() - last_time).total_seconds()
        remaining = cooldown_seconds - elapsed

        if remaining > 0:
            return False, int(remaining)

        return True, 0


# ==========================================
# 装饰器
# ==========================================

def validate_and_reply(error_message: str = "操作失败，请稍后再试喵~"):
    """
    验证并自动回复错误消息的装饰器

    使用方式：
        @validate_and_reply("绑定失败")
        async def my_command(self, update, context):
            ...

    如果函数抛出 ValidationError，会自动发送错误消息
    """
    def decorator(func):
        async def wrapper(self, update, *args, **kwargs):
            try:
                return await func(self, update, *args, **kwargs)
            except ValidationError as e:
                msg = update.effective_message if update else None
                if msg:
                    from utils import reply_with_auto_delete
                    await reply_with_auto_delete(msg, f"⚠️ <b>{e.user_message or error_message}</b>")
                return None
        return wrapper
    return decorator
