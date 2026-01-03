"""
签到绑定系统 - 魔法少女版
- 每日签到领取魔力
- VIP用户1.5倍收益
- 成就系统
- 缔结魔法契约（绑定Emby账号）
- 签到日历视图
- 全面正面反馈增强
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding, create_or_update_user
from datetime import datetime, timedelta, date
from utils import reply_with_auto_delete, get_unbound_message, edit_with_auto_delete
from plugins.feedback_utils import progress_bar, get_crit_effect, success_burst, random_loading
from plugins.quotes import get_checkin_greeting, get_milestone_congrats, random_cute_emoji
from plugins.lucky_events import calculate_lucky_reward, check_random_drop
import random
import logging
import aiohttp
import os

logger = logging.getLogger(__name__)


# ==========================================
# 任务追踪包装函数
# ==========================================
async def track_activity_wrapper(user_id: int, activity_type: str) -> tuple:
    """包装函数，延迟导入避免循环依赖"""
    from plugins.unified_mission import track_and_check_task
    return await track_and_check_task(user_id, activity_type)


def check_achievement(user, user_id=None):
    """检查成就（导入achievement模块）"""
    try:
        from plugins.achievement import check_and_award_achievement
        return check_and_award_achievement(user, user_id)
    except ImportError:
        return None


async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """每日签到（全面正面反馈增强版）"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    first_name = update.effective_user.first_name or "酱"

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user or not user.emby_account:
            await reply_with_auto_delete(msg, await get_unbound_message(first_name))
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
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"{success_burst(2)} 今天已经领取过魔力了呢喵~ {success_burst(2)}\n"
                    f"📅 连续签到：{user.consecutive_checkin or 0} 天\n"
                    f"⏰ 距离下次签到还有：<b>{hours}小时{minutes}分钟</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"<i>\"明天再来哦，看板娘等你喵~(｡•̀ᴗ-)✧\"</i>"
                )
                return

        # 基础奖励：15-25 MP
        base_points = random.randint(15, 25)
        user.last_checkin = now

        # 计算连续签到
        yesterday = now - timedelta(days=1)
        if user.last_checkin_date:
            last_date = user.last_checkin_date.replace(tzinfo=None)
            if last_date >= yesterday.replace(hour=0, minute=0, second=0):
                user.consecutive_checkin = (user.consecutive_checkin or 0) + 1
            else:
                user.consecutive_checkin = 1
        else:
            user.consecutive_checkin = 1
        user.last_checkin_date = now
        user.total_checkin_days = (user.total_checkin_days or 0) + 1

        # 幸运草效果
        lucky_boost_active = user.lucky_boost
        if lucky_boost_active:
            user.lucky_boost = False  # 消耗幸运草

        # [修复] 全面检查所有成就（不再只检查3个）
        achievement_msg = ""
        new_achievements = []
        for ach_id in ["first_checkin", "checkin_1", "checkin_3", "checkin_7", "checkin_30", "checkin_100"]:
            result = check_achievement(user, ach_id)
            if result and result.get("new"):
                new_achievements.append(result)
        if new_achievements:
            lines = []
            for ach in new_achievements:
                title = f" 「{ach['title']}」" if ach.get('title') else ""
                lines.append(f"🎉 {ach['emoji']} {ach['name']} (+{ach['reward']}MP{title})")
            achievement_msg = "\n" + "\n".join(lines)

        # === 幸运事件检测 ===
        # 1. 随机暴击
        lucky_result = calculate_lucky_reward(base_points, user.is_vip)
        actual_points = lucky_result["actual"]
        crit_multiplier = lucky_result["multiplier"]

        # 2. 随机掉落
        drop_result = check_random_drop(user.is_vip)

        # 3. 幸运草额外加成
        if lucky_boost_active:
            lucky_bonus = base_points
            actual_points += lucky_bonus
            crit_effect = f"🍀 幸运草暴击！+{lucky_bonus} MP"
        else:
            lucky_bonus = 0
            crit_effect = lucky_result["effect"]

        # VIP 加成
        if user.is_vip:
            actual_points = int(actual_points * 1.5)

        # 奖励入账
        user.points += actual_points
        session.commit()

        # === 构建签到消息 ===
        if user.is_vip:
            title = f"🍬✨ 【 皇 家 · 每 日 补 给 】✨🍬"
            welcome = get_checkin_greeting(first_name, is_vip=True)
        else:
            title = f"🍬✨ 【 每 日 签 到 】✨🍬"
            welcome = get_checkin_greeting(first_name, is_vip=False)

        # 进度条（10天为一个周期）
        cycle_day = (user.consecutive_checkin - 1) % 10 + 1
        cycle_progress = f"📅 连续签到：{progress_bar(cycle_day, 10)} {cycle_day}/10 天 (累计{user.total_checkin_days}天)"

        # 奖励部分
        reward_lines = [f"💎 基础奖励：+{base_points} MP"]

        if crit_multiplier > 1:
            reward_lines.append(f"{crit_effect}")
            reward_lines.append(f"💰💰💰 额外 +{actual_points - base_points - lucky_bonus} MP 💰💰💰")

        if lucky_boost_active:
            reward_lines.append(f"🍀 幸运草加成：+{lucky_bonus} MP")

        if user.is_vip:
            reward_lines.append(f"👑 VIP加成：x1.5")

        reward_lines.append(f"💰 总计获得：<b>+{actual_points}</b> MP")

        # 随机掉落部分
        drop_text = ""
        if drop_result["dropped"]:
            drop_text = f"\n🎁 <b>随机掉落：</b> {drop_result['name']} x{drop_result['amount']}\n"
            # 如果掉落的是幸运草或盲盒券，更新数据库
            if drop_result["type"] == "lucky_grass":
                with get_session() as drop_session:
                    drop_user = drop_session.query(UserBinding).filter_by(tg_id=user_id).first()
                    if drop_user:
                        drop_user.lucky_boost = True
                        drop_session.commit()
            elif drop_result["type"] == "extra_gacha":
                with get_session() as drop_session:
                    drop_user = drop_session.query(UserBinding).filter_by(tg_id=user_id).first()
                    if drop_user:
                        drop_user.extra_gacha = (drop_user.extra_gacha or 0) + drop_result["amount"]
                        drop_session.commit()
            elif drop_result["type"] == "free_forge":
                with get_session() as drop_session:
                    drop_user = drop_session.query(UserBinding).filter_by(tg_id=user_id).first()
                    if drop_user:
                        drop_user.free_forges = (drop_user.free_forges or 0) + drop_result["amount"]
                        drop_session.commit()

        # 组装完整消息（精简版）
        # 压缩奖励显示
        reward_display = f"💎 +{base_points}"
        if crit_multiplier > 1:
            reward_display += f" {crit_effect}"
        if lucky_boost_active:
            reward_display += f" 🍀+{lucky_bonus}"
        if user.is_vip:
            reward_display += f" 👑×1.5"
        reward_display = f"<b>{reward_display} = {actual_points} MP</b>"

        # 成就和掉落合并一行
        extras = []
        if drop_result["dropped"]:
            extras.append(f"🎁{drop_result['name']}×{drop_result['amount']}")
            # 处理掉落更新数据库...
            if drop_result["type"] == "lucky_grass":
                with get_session() as drop_session:
                    drop_user = drop_session.query(UserBinding).filter_by(tg_id=user_id).first()
                    if drop_user:
                        drop_user.lucky_boost = True
                        drop_session.commit()
            elif drop_result["type"] == "extra_gacha":
                with get_session() as drop_session:
                    drop_user = drop_session.query(UserBinding).filter_by(tg_id=user_id).first()
                    if drop_user:
                        drop_user.extra_gacha = (drop_user.extra_gacha or 0) + drop_result["amount"]
                        drop_session.commit()
            elif drop_result["type"] == "free_forge":
                with get_session() as drop_session:
                    drop_user = drop_session.query(UserBinding).filter_by(tg_id=user_id).first()
                    if drop_user:
                        drop_user.free_forges = (drop_user.free_forges or 0) + drop_result["amount"]
                        drop_session.commit()
        if new_achievements:
            extras.append(f"🏆{new_achievements[0]['name']}")
        extras_line = " | ".join(extras) if extras else ""

        text = (
            f"{title}\n"
            f"━━━━━━━━━━━━━━\n"
            f"{welcome}\n"
            f"━━━━━━━━━━━━━━\n"
            f"{cycle_progress}\n"
            f"{success_burst(2)}\n"
            f"{reward_display}\n"
            f"💰 余额: {user.points} MP"
        )
        if extras_line:
            text += f"\n{extras_line}"
        text += f"\n━━━━━━━━━━━━━━\n<i>💡 {random_cute_emoji()}</i>"

        # 追踪任务进度
        checkin_completed, checkin_msg = await track_activity_wrapper(user_id, "checkin")
        if lucky_boost_active:
            lucky_completed, lucky_msg = await track_activity_wrapper(user_id, "lucky")

        # 如果有任务完成，在签到消息下方显示
        task_notes = []
        if checkin_completed and checkin_msg:
            task_notes.append("✅ 每日签到任务完成！")
        if lucky_boost_active and lucky_completed and lucky_msg:
            task_notes.append("✅ 幸运尝试任务完成！")

        if task_notes:
            text += "\n" + " | ".join(task_notes)

        await reply_with_auto_delete(msg, text)


async def bind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """缔结魔法契约（绑定Emby账号）"""
    msg = update.effective_message
    if not msg:
        return

    if not context.args:
        await reply_with_auto_delete(
            msg,
            f"📜 <b>【 魔 法 契 约 · 缔 结 仪 式 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 <b>使用方法：</b>\n"
            f"<code>/bind Emby用户名</code>\n\n"
            f"💡 <b>如何查看用户名？</b>\n"
            f"1. 打开 Emby 网站/APP\n"
            f"2. 点击左上角头像\n"
            f"3. 查看显示的名称\n\n"
            f"🎁 <b>新手福利：</b>\n"
            f"• 150 MP 魔力\n"
            f"• 3个盲盒券\n"
            f"• 1张锻造券\n"
            f"• 新手武器（+10战力）\n\n"
            f"<i>\"绑定后即可签到领取魔力，观影还能赚MP哦~(｡•̀ᴗ-)✧\"</i>"
        )
        return

    emby_username = context.args[0]
    user = update.effective_user

    # 验证 Emby 用户是否存在
    emby_url = os.getenv("EMBY_URL", "")
    emby_api_key = os.getenv("EMBY_API_KEY", "")

    emby_valid = False
    if emby_url and emby_api_key:
        try:
            headers = {
                "X-Emby-Token": emby_api_key,
                "Accept": "application/json",
                "User-Agent": "curl/7.68.0"
            }
            async with aiohttp.ClientSession() as session:
                url = f"{emby_url}/Users"
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        emby_users = {u.get('Name', ''): u.get('Id', '') for u in data}
                        # 尝试精确匹配
                        if emby_username in emby_users:
                            emby_valid = True
                        else:
                            # 尝试忽略大小写匹配
                            for key in emby_users.keys():
                                if key.lower() == emby_username.lower():
                                    emby_username = key  # 使用正确的用户名
                                    emby_valid = True
                                    break
        except Exception:
            pass  # 验证失败时继续，允许绑定

    # 检查是否是新用户
    with get_session() as session:
        existing_user = session.query(UserBinding).filter_by(tg_id=user.id).first()
        is_new_user = existing_user is None

        # 如果是新用户，设置注册日期
        if is_new_user:
            from datetime import datetime as dt
            create_or_update_user(user.id, emby_username)
            # 重新获取用户并设置注册日期
            user_data = session.query(UserBinding).filter_by(tg_id=user.id).first()
            if user_data and not user_data.registered_date:
                user_data.registered_date = dt.now()
                session.commit()

    # 创建或更新用户
    create_or_update_user(user.id, emby_username)

    # 新手礼包发放
    newbie_rewards = []
    if is_new_user:
        with get_session() as session:
            user_data = session.query(UserBinding).filter_by(tg_id=user.id).first()
            if user_data and not user_data.newbie_package_claimed:
                # 发放新手礼包
                user_data.points += 150  # 150 MP（增加到让新手能体验一次锻造）
                user_data.extra_gacha = (user_data.extra_gacha or 0) + 3  # 3个盲盒券
                user_data.free_forges = (user_data.free_forges or 0) + 1  # 1张锻造券
                user_data.attack = (user_data.attack or 0) + 10  # 初始战力
                user_data.weapon = "练习木剑"  # 新手武器
                user_data.newbie_package_claimed = True
                session.commit()

                newbie_rewards = [
                    "💰 150 MP",
                    "🎰 3个盲盒券",
                    "⚒️ 1张锻造券",
                    "🗡️ 练习木剑 (+10战力)"
                ]

    # 构建绑定成功消息
    if emby_valid:
        validity_msg = "✅ <b>Emby账号验证成功</b>\n"
        features = "   • 🍬 每日签到领取魔力\n   • 🎬 观影挖矿赚取MP\n"
    else:
        validity_msg = "⚠️ <b>Emby账号未验证（请检查用户名）</b>\n"
        features = "   • 🍬 每日签到领取魔力\n"

    # 新手礼包展示
    newbie_section = ""
    if newbie_rewards:
        newbie_section = f"\n🎁 <b>【 新手礼包已发放 】</b>\n"
        for reward in newbie_rewards:
            newbie_section += f"   {reward}\n"
        newbie_section += "\n💡 <b>下一步：</b>\n"
        newbie_section += "   发送 <code>/daily</code> 签到领更多奖励喵~\n"

    await reply_with_auto_delete(
        msg,
        f"🌸 <b>【 魔 法 契 约 · 缔 结 完 成 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✨ <b>Welcome, {emby_username}酱！</b>\n"
        f"欢迎来到云海魔法学院~\n"
        f"{validity_msg}"
        f"从今天起，你就是见习魔法少女啦！\n\n"
        f"{newbie_section}"
        f"📜 <b>你可以：</b>\n"
        f"{features}"
        f"   • 🎰 抽取魔法盲盒收集道具\n"
        f"   • ⚔️ 与其他魔导师决斗\n"
        f"   • 🏦 存储魔力到皇家金库\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"让我们一起踏上魔法之旅吧喵！(｡･ω･｡)ﾉ♡\"</i>"
    )

    # 自动触发新手教程
    from plugins.tutorial import tutorial_start
    await tutorial_start(update, context)


async def checkin_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """签到日历视图 - 显示本月签到情况"""
    msg = update.effective_message
    query = getattr(update, "callback_query", None)

    if not msg and not query:
        return

    user_id = update.effective_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user or not user.emby_account:
            target = query.edit_message_text if query else msg.reply_html
            await target("💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        # 获取当前月份信息
        now = datetime.now()
        year = now.year
        month = now.month
        today = now.day

        # 获取用户注册日期（用于显示从什么时候开始签到）
        reg_date = user.registered_date
        if reg_date:
            reg_day = reg_date.day if reg_date.month == month and reg_date.year == year else None
        else:
            reg_day = None

        # 获取最后签到日期
        last_checkin = user.last_checkin
        last_checkin_day = last_checkin.day if last_checkin and last_checkin.month == month and last_checkin.year == year else None

        # 获取连续签到天数
        consecutive = user.consecutive_checkin or 0
        total_days = user.total_checkin_days or 0

        # 构建日历
        import calendar
        cal = calendar.monthcalendar(year, month)

        # 构建日历视图
        calendar_text = f"📅 <b>【 签 到 日 历 】</b>\n"
        calendar_text += f"━━━━━━━━━━━━━━━━━━\n"
        calendar_text += f"👤 <b>{user.emby_account}</b>\n"
        calendar_text += f"📆 <b>{year}年{month}月</b>\n"
        calendar_text += f"🔥 连续签到：<b>{consecutive}</b> 天\n"
        calendar_text += f"📊 累计签到：<b>{total_days}</b> 天\n"
        calendar_text += f"━━━━━━━━━━━━━━━━━━\n"
        calendar_text += f"  一  二  三  四  五  六  日\n"

        for week in cal:
            week_text = ""
            for day in week:
                if day == 0:
                    week_text += "    "
                else:
                    # 判断签到状态
                    if day == last_checkin_day:
                        # 今日已签到
                        week_text += " ✅ "
                    elif day < last_checkin_day or (reg_day and day >= reg_day):
                        # 可能的签到日期（简化处理）
                        if day == today:
                            week_text += f" <b>{day:2}</b> "
                        else:
                            week_text += f" {day:2} "
                    else:
                        # 未注册或未来日期
                        if day == today:
                            week_text += f" ❓{day:2} "
                        else:
                            week_text += f" •  "
            calendar_text += week_text + "\n"

        calendar_text += f"━━━━━━━━━━━━━━━━━━\n"
        calendar_text += f"✅ 今日已签到  |  ❓ 今日未签到\n"
        calendar_text += f"━━━━━━━━━━━━━━━━━━\n"
        calendar_text += f"<i>\"坚持签到，奖励丰厚喵~(｡•̀ᴗ-)✧\"</i>"

        buttons = [[InlineKeyboardButton("🔙 返回", callback_data="calendar_back")]]

        if query:
            await query.edit_message_text(
                calendar_text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode='HTML'
            )
        else:
            await msg.reply_html(calendar_text, reply_markup=InlineKeyboardMarkup(buttons))


async def calendar_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """返回日历主界面"""
    query = update.callback_query
    await query.answer()
    await checkin_calendar(update, context)


def register(app):
    app.add_handler(CommandHandler("checkin", checkin))
    app.add_handler(CommandHandler("daily", checkin))
    app.add_handler(CommandHandler("calendar", checkin_calendar))
    app.add_handler(CommandHandler("checkin_calendar", checkin_calendar))
    app.add_handler(CommandHandler("bind", bind))
    app.add_handler(CallbackQueryHandler(calendar_back_callback, pattern="^calendar_back$"))
