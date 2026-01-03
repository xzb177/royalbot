"""
签到绑定系统 - 魔法少女版
- 每日签到领取魔力
- VIP用户1.5倍收益
- 成就系统
- 缔结魔法契约
"""
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database import get_session, UserBinding, create_or_update_user
from datetime import datetime, timedelta
from utils import reply_with_auto_delete
import random


# ==========================================
# 任务追踪包装函数
# ==========================================
async def track_activity_wrapper(user_id: int, activity_type: str):
    """包装函数，延迟导入避免循环依赖"""
    from plugins.unified_mission import track_and_check_task
    await track_and_check_task(user_id, activity_type)


def check_achievement(user, user_id=None):
    """检查成就（导入achievement模块）"""
    try:
        from plugins.achievement import check_and_award_achievement
        return check_and_award_achievement(user, user_id)
    except ImportError:
        return None


async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """每日签到"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user or not user.emby_account:
            await reply_with_auto_delete(msg, "💔 <b>请先缔结魔法契约喵！</b>\n使用 <code>/bind 账号</code> 绑定后再来签到~")
            return

        # 检查是否今天已经签到过
        now = datetime.now()
        if user.last_checkin:
            last_checkin_date = user.last_checkin.date()
            today_date = now.date()
            if last_checkin_date >= today_date:
                next_available = user.last_checkin.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                remaining = next_available - now
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)

                await reply_with_auto_delete(
                    msg,
                    f"⏰ <b>【 今 日 已 签 到 】</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"今天已经领取过魔力了呢喵~\n"
                    f"距离下次签到还有：<b>{hours}小时{minutes}分钟</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"<i>\"明天再来哦，看板娘等你喵~(｡•̀ᴗ-)✧\"</i>"
                )
                return

        # 签到奖励 (平衡调整后 2026-01-02)
        # 基础奖励：15-25 MP (从10-30调整，降低上限)
        base_points = random.randint(15, 25)
        user.last_checkin = now

        # 计算连续签到
        yesterday = now - timedelta(days=1)
        if user.last_checkin_date:
            last_date = user.last_checkin_date.replace(tzinfo=None)
            if last_date >= yesterday.replace(hour=0, minute=0, second=0):
                # 昨天签到了，连续+1
                user.consecutive_checkin = (user.consecutive_checkin or 0) + 1
            else:
                # 中断了，重置
                user.consecutive_checkin = 1
        else:
            user.consecutive_checkin = 1
        user.last_checkin_date = now
        user.total_checkin_days = (user.total_checkin_days or 0) + 1

        # 幸运草效果：暴击率30% (从50%降低)
        lucky_crit = False
        lucky_bonus = 0
        if user.lucky_boost:
            if random.random() < 0.3:  # 30% 暴击率
                lucky_bonus = base_points  # 暴击 = 额外获得基础值
                lucky_crit = True
            user.lucky_boost = False  # 消耗幸运草

        # 检查签到成就
        achievement_msg = ""
        if user.consecutive_checkin >= 7:
            result = check_achievement(user, "checkin_7")
            if result and result.get("new"):
                achievement_msg = f"\n🎉 <b>成就解锁：{result['name']}</b>\n获得 {result['reward']} MP！"
        if user.consecutive_checkin >= 30:
            result = check_achievement(user, "checkin_30")
            if result and result.get("new"):
                achievement_msg += f"\n🎉 <b>成就解锁：{result['name']}</b>\n获得 {result['reward']} MP + 称号「{result['title']}」！"
        if user.total_checkin_days >= 100:
            result = check_achievement(user, "checkin_100")
            if result and result.get("new"):
                achievement_msg += f"\n🎉 <b>成就解锁：{result['name']}</b>\n获得 {result['reward']} MP + 称号「{result['title']}」！"

        if user.is_vip:
            # VIP加成：×1.5 (从×2降低)
            base_points = int(base_points * 1.5)
            total_points = base_points + lucky_bonus
            user.points += total_points

            # VIP 文案
            text = (
                f"🍬 <b>【 皇 家 · 每 日 补 给 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👑 <b>Welcome back, Master~</b>\n"
                f"📅 <b>连续签到：</b> {user.consecutive_checkin} 天 | 累计 {user.total_checkin_days} 天\n"
            )
            if lucky_crit:
                text += (
                    f"🍀 <b>幸运草暴击！</b>\n"
                    f"星辰的眷顾降临了喵~\n\n"
                    f"💎 <b>基础奖励：</b> +{base_points} MP\n"
                    f"🍀 <b>暴击加成：</b> +{lucky_bonus} MP\n"
                    f"💰 <b>总计获得：</b> <b>+{total_points}</b> MP\n"
                )
            else:
                text += (
                    f"感谢您对星辰的眷顾，这是今日的1.5倍馈赠喵~\n\n"
                    f"💎 <b>获得魔力：</b> <b>+{base_points}</b> MP\n"
                )
            text += (
                f"💰 <b>当前余额：</b> {user.points} MP\n"
                f"{achievement_msg}"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>\"明天见哦，亲爱的Master...(｡･ω･｡)ﾉ♡\"</i>"
            )
        else:
            total_points = base_points + lucky_bonus
            user.points += total_points

            # 普通用户文案
            text = (
                f"🍬 <b>【 魔 法 学 院 · 每 日 补 给 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✨ <b>签到成功喵~</b>\n"
                f"📅 <b>连续签到：</b> {user.consecutive_checkin} 天 | 累计 {user.total_checkin_days} 天\n"
            )
            if lucky_crit:
                text += (
                    f"🍀 <b>幸运草暴击！</b>\n"
                    f"四叶草的魔法生效啦~\n\n"
                    f"💎 <b>基础奖励：</b> +{base_points} MP\n"
                    f"🍀 <b>暴击加成：</b> +{lucky_bonus} MP\n"
                    f"💰 <b>总计获得：</b> <b>+{total_points}</b> MP\n"
                )
            else:
                text += (
                    f"今天也要加油哦，小魔法少女！\n\n"
                    f"💎 <b>获得魔力：</b> +{base_points} MP\n"
                )
            text += (
                f"💰 <b>当前余额：</b> {user.points} MP\n"
                f"{achievement_msg}"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>💡 VIP 可享 <b>1.5倍</b> 魔力加成哦！</i>\n"
                f"<i>\"成为VIP，星辰将永远眷顾你喵~(≧◡≦)\"</i>"
            )

        session.commit()

        # 追踪任务进度
        await track_activity_wrapper(user_id, "checkin")
        if lucky_crit:
            await track_activity_wrapper(user_id, "lucky")

        await reply_with_auto_delete(msg, text)


async def bind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """缔结魔法契约"""
    msg = update.effective_message
    if not msg:
        return

    try:
        name = context.args[0]
        user = update.effective_user
        create_or_update_user(user.id, name)

        await reply_with_auto_delete(
            msg,
            f"🌸 <b>【 魔 法 契 约 · 缔 结 完 成 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ <b>Welcome, {name}酱！</b>\n"
            f"欢迎来到云海魔法学院~\n"
            f"从今天起，你就是见习魔法少女啦！\n\n"
            f"📜 <b>你可以：</b>\n"
            f"   • 🍬 每日签到领取魔力\n"
            f"   • 🎰 抽取魔法盲盒收集道具\n"
            f"   • ⚔️ 与其他魔导师决斗\n"
            f"   • 🏦 存储魔力到皇家金库\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>\"让我们一起踏上魔法之旅吧喵！(｡･ω･｡)ﾉ♡\"</i>"
        )
    except:
        await reply_with_auto_delete(
            msg,
            f"⚠️ <b>【 咒 语 念 错 啦 喵 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"请发送：<code>/bind 您的Emby账号</code>\n\n"
            f"<i>\"看板娘听不懂你在说什么喵... (｡•́︿•̀｡)\"</i>"
        )


def register(app):
    app.add_handler(CommandHandler("checkin", checkin))
    app.add_handler(CommandHandler("daily", checkin))
    app.add_handler(CommandHandler("bind", bind))
