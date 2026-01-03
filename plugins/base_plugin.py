"""
通用插件基类 - Base Plugin
提供所有插件共享的通用功能，减少代码重复

使用方式：
    from plugins.base_plugin import BasePlugin

    class MyPlugin(BasePlugin):
        async def my_command(self, update, context):
            user = await self.get_user(update.effective_user.id)
            if not user:
                return
            # 使用 user 进行后续操作...
"""
import logging
from typing import Optional, Tuple
from telegram import Update
from telegram.ext import ContextTypes
from database import get_session, UserBinding

logger = logging.getLogger(__name__)


class BasePlugin:
    """
    插件基类
    提供通用的用户检查、VIP折扣、成就等功能
    """

    # ==========================================
    # 用户管理
    # ==========================================

    async def get_user(self, user_id: int, session=None) -> Optional[UserBinding]:
        """
        获取用户对象（自动检查绑定状态）

        Args:
            user_id: Telegram 用户ID
            session: 数据库会话（可选，如果提供则不创建新会话）

        Returns:
            UserBinding 对象，如果用户未绑定返回 None
        """
        if session:
            return session.query(UserBinding).filter_by(tg_id=user_id).first()

        with get_session() as s:
            user = s.query(UserBinding).filter_by(tg_id=user_id).first()
            # 返回detach的对象避免session过期问题
            if user and user.emby_account:
                # 重新查询获取最新数据
                return s.query(UserBinding).filter_by(tg_id=user_id).first()
            return None

    async def require_user(self, update: Update, session=None) -> Optional[UserBinding]:
        """
        获取用户并自动发送未绑定提示

        Args:
            update: Telegram Update 对象
            session: 数据库会话（可选）

        Returns:
            UserBinding 对象，未绑定时返回 None 并自动发送提示
        """
        user = await self.get_user(update.effective_user.id, session)
        if user and user.emby_account:
            return user

        # 用户未绑定
        msg = update.effective_message
        if msg:
            from utils import reply_with_auto_delete
            await reply_with_auto_delete(
                msg,
                "💔 <b>请先绑定账号喵！</b>\n\n使用 <code>/bind 账号</code> 绑定后再来~"
            )
        return None

    def is_user_bound(self, user: UserBinding) -> bool:
        """检查用户是否已绑定"""
        return user is not None and user.emby_account is not None and user.emby_account != ""

    # ==========================================
    # VIP 相关
    # ==========================================

    def is_vip(self, user: UserBinding) -> bool:
        """检查用户是否是VIP"""
        return user.is_vip if user else False

    def get_vip_discount(self, user: UserBinding, base_price: int,
                        discount_rate: float = 0.5) -> int:
        """
        获取VIP折扣后价格

        Args:
            user: 用户对象
            base_price: 基础价格
            discount_rate: 折扣率（默认5折）

        Returns:
            折扣后的价格
        """
        if self.is_vip(user):
            return int(base_price * discount_rate)
        return base_price

    def get_vip_multiplier(self, user: UserBinding,
                          base_value: int,
                          multiplier: float = 1.5) -> int:
        """
        获取VIP倍率加成后的值

        Args:
            user: 用户对象
            base_value: 基础值
            multiplier: 倍率（默认1.5倍）

        Returns:
            加成后的值
        """
        if self.is_vip(user):
            return int(base_value * multiplier)
        return base_value

    # ==========================================
    # 成就系统
    # ==========================================

    async def check_achievement(self, user: UserBinding,
                                achievement_id: str,
                                session) -> Tuple[bool, dict]:
        """
        检查并颁发成就

        Args:
            user: 用户对象
            achievement_id: 成就ID
            session: 数据库会话

        Returns:
            (是否新成就, 成就信息字典)
        """
        from plugins.achievement import check_and_award_achievement
        result = check_and_award_achievement(user, achievement_id, session)
        return result.get("new", False), result

    async def award_achievement_with_message(self,
                                            user: UserBinding,
                                            achievement_id: str,
                                            session,
                                            bonus_text: str = "") -> str:
        """
        检查成就并返回消息文本

        Args:
            user: 用户对象
            achievement_id: 成就ID
            session: 数据库会话
            bonus_text: 额外的文本

        Returns:
            成就获得的消息文本（空字符串表示未获得新成就）
        """
        is_new, result = await self.check_achievement(user, achievement_id, session)
        if is_new:
            user.points += result.get("reward", 0)
            return f"\n\n🎉 {result.get('emoji', '')} {result.get('name', '')} (+{result.get('reward', 0)}MP)"
        return ""

    # ==========================================
    # 战力计算
    # ==========================================

    def calculate_total_power(self, user: UserBinding) -> int:
        """
        计算用户总战力（基础战力 + 突破加成）

        Args:
            user: 用户对象

        Returns:
            总战力
        """
        base_power = user.attack or 0

        # 突破加成
        from plugins.breakthrough import get_total_power_bonus
        breakthrough_bonus = get_total_power_bonus(user)

        return base_power + breakthrough_bonus

    def get_weapon_rarity_bonus(self, weapon: str) -> int:
        """
        根据武器稀有度获取加成

        Args:
            weapon: 武器名称

        Returns:
            加成值
        """
        if not weapon:
            return 0
        weapon_upper = weapon.upper()
        if "SSR" in weapon_upper or "神器" in weapon_upper or "神话" in weapon_upper or "终焉" in weapon_upper or "创世" in weapon_upper:
            return 15
        elif "SR" in weapon_upper or "史诗" in weapon_upper or "传说" in weapon_upper:
            return 10
        elif "R" in weapon_upper or "稀有" in weapon_upper or "精良" in weapon_upper or "普通" in weapon_upper:
            return 5
        elif "咸鱼" in weapon_upper:
            return -5
        return 0

    # ==========================================
    # 消息构建工具
    # ==========================================

    def build_user_info_line(self, user: UserBinding, name: str = None) -> str:
        """
        构建用户信息展示行

        Args:
            user: 用户对象
            name: 用户名称（可选）

        Returns:
            格式化的用户信息字符串
        """
        display_name = name or "神秘人"
        vip_badge = "👑 " if self.is_vip(user) else ""
        power = self.calculate_total_power(user)

        return (
            f"👤 <b>用户：</b> {vip_badge}{display_name}\n"
            f"⚡ <b>战力：</b> {power}\n"
            f"💰 <b>余额：</b> {user.points or 0} MP"
        )

    def build_progress_bar(self, current: int, total: int,
                          filled: str = "🔥", empty: str = "⚪",
                          length: int = 10) -> str:
        """
        构建进度条

        Args:
            current: 当前进度
            total: 总进度
            filled: 填充字符
            empty: 空字符
            length: 进度条长度

        Returns:
            进度条字符串
        """
        if total == 0:
            return empty * length
        filled_count = int((current / total) * length)
        filled_count = min(filled_count, length)
        return filled * filled_count + empty * (length - filled_count)

    # ==========================================
    # 错误处理
    # ==========================================

    async def handle_error(self, update: Update, error: Exception,
                          user_message: str = "操作失败，请稍后再试喵~"):
        """
        统一的错误处理

        Args:
            update: Telegram Update 对象
            error: 异常对象
            user_message: 给用户的提示消息
        """
        logger.error(f"插件错误: {error}", exc_info=True)

        msg = update.effective_message if update else None
        if msg:
            from utils import reply_with_auto_delete
            await reply_with_auto_delete(
                msg,
                f"⚠️ <b>{user_message}</b>\n\n<i>错误已记录，请联系管理员</i>"
            )

    # ==========================================
    # 余额检查
    # ==========================================

    def can_afford(self, user: UserBinding, amount: int) -> bool:
        """检查用户是否有足够的余额"""
        return (user.points or 0) >= amount

    async def require_balance(self, update: Update,
                             user: UserBinding,
                             amount: int,
                             item_name: str = "此物品") -> bool:
        """
        检查余额并发送提示

        Args:
            update: Telegram Update 对象
            user: 用户对象
            amount: 所需金额
            item_name: 物品名称

        Returns:
            True 表示余额充足，False 表示余额不足
        """
        if self.can_afford(user, amount):
            return True

        msg = update.effective_message
        if msg:
            from utils import reply_with_auto_delete
            await reply_with_auto_delete(
                msg,
                f"💸 <b>魔力不足喵！</b>\n\n"
                f"{item_name} 需要 <b>{amount}</b> MP\n"
                f"当前余额：<b>{user.points or 0}</b> MP"
            )
        return False

    # ==========================================
    # 保底系统
    # ==========================================

    def get_gacha_pity_count(self, user: UserBinding) -> int:
        """获取抽卡保底计数"""
        total = user.gacha_total_count or 0
        last_sr = user.last_sr_gacha_count or 0
        return total - last_sr

    def is_pity_trigger(self, user: UserBinding) -> bool:
        """检查是否触发保底（80抽）"""
        return self.get_gacha_pity_count(user) >= 80


# ==========================================
# 装饰器工具
# ==========================================

def require_user_binding(func):
    """
    装饰器：要求用户已绑定

    使用方式：
        @require_user_binding
        async def my_command(self, update, context):
            user = await self.require_user(update)
            ...
    """
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = await self.require_user(update)
        if not user:
            return
        return await func(self, update, context, user, *args, **kwargs)
    return wrapper


def with_error_handling(user_message: str = "操作失败，请稍后再试喵~"):
    """
    装饰器：自动捕获并处理异常

    使用方式：
        @with_error_handling("签到失败")
        async def my_command(self, update, context):
            ...
    """
    def decorator(func):
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            try:
                return await func(self, update, context, *args, **kwargs)
            except Exception as e:
                await self.handle_error(update, e, user_message)
                return None
        return wrapper
    return decorator
