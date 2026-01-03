"""
Emby 观影挖矿系统
- 观影时长自动赚取 MP
- 每日观影上限
- VIP 加成
- 新片首发冲刺
- 每周观影排行榜
- 新片自动推送
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding
from utils import reply_with_auto_delete, get_unbound_message
import aiohttp
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)

# Emby 配置
EMBY_URL = os.getenv("EMBY_URL", "")
EMBY_API_KEY = os.getenv("EMBY_API_KEY", "")

# 新片推送配置 - 环境变量配置多个群组，逗号分隔
NOTIFICATION_CHATS = os.getenv("EMBY_NOTIFY_CHATS", "").split(",") if os.getenv("EMBY_NOTIFY_CHATS") else []
CHECK_NEW_RELEASES_INTERVAL = 1800  # 每30分钟检查一次新片

# 观影奖励配置
MINUTES_PER_MP = 5  # 每5分钟1MP（降低门槛）
NEWBIE_MINUTES_PER_MP = 5  # 新手期也是5分钟1MP (统一)
NEWBIE_DAYS = 7  # 新手期天数
DAILY_MAX_MINUTES = 180  # 每日最多计算180分钟（即36MP）
VIP_BONUS_MULTIPLIER = 1.5  # VIP加成
NEW_RELEASE_LIMIT = 10  # 前N个看完得奖励
NEW_RELEASE_REWARD = 100  # 首播奖励
NEW_RELEASE_TIME_LIMIT_HOURS = 48  # 新片发布后48小时内算首播（延长到2天）

# 每周观影奖励
WEEKLY_TOP_REWARD = 500  # 周榜第一奖励
WEEKLY_SECOND_REWARD = 300  # 周榜第二奖励
WEEKLY_THIRD_REWARD = 150  # 周榜第三奖励

# 追踪新片首播
early_bird_tracking = {}  # {item_id: {user_id: finish_time}}
announced_items = set()  # 已推送的新片ID集合

# 首播冲刺活动存储
active_races = {}  # {item_id: {"name": str, "premiere_time": datetime, "finishers": [user_ids], "limit": int}}


async def get_emby_users():
    """获取 Emby 用户列表"""
    if not EMBY_URL or not EMBY_API_KEY:
        return {}

    headers = {
        "X-Emby-Token": EMBY_API_KEY,
        "Accept": "application/json",
        "User-Agent": "curl/7.68.0"
    }

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{EMBY_URL}/Users"
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # 返回 {username: user_id} 映射
                    return {u.get('Name', ''): u.get('Id', '') for u in data}
    except Exception as e:
        logger.error(f"获取 Emby 用户失败: {e}")

    return {}


async def get_user_watch_time(emby_user_id: str, date: datetime = None) -> int:
    """获取指定日期的观影时长（分钟）"""
    if not emby_user_id:
        return 0

    headers = {
        "X-Emby-Token": EMBY_API_KEY,
        "Accept": "application/json",
        "User-Agent": "curl/7.68.0"
    }

    # 计算日期范围
    if date is None:
        date = datetime.now(timezone.utc)

    start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{EMBY_URL}/Users/{emby_user_id}/Items"
            params = {
                "Filters": "IsPlayed",
                "SortBy": "DatePlayed",
                "SortOrder": "Descending",
                "MediaTypes": "Video",
                "MinDatePlayed": start_of_day.isoformat(),
                "MaxDatePlayed": end_of_day.isoformat(),
                "Limit": 1000
            }
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if 'Items' in data:
                        total_seconds = 0
                        for item in data['Items']:
                            if item.get('RunTimeTicks'):
                                total_seconds += (item['RunTimeTicks'] // 10000000)
                        return total_seconds // 60  # 转换为分钟
    except Exception as e:
        logger.error(f"获取观影时长失败: {e}")

    return 0


def is_newbie_user(user) -> bool:
    """检查用户是否在新手期（注册7天内）"""
    if not user or not user.registered_date:
        return False
    from datetime import datetime as dt, timedelta
    days_since_reg = (dt.now() - user.registered_date).days
    return days_since_reg < NEWBIE_DAYS


def get_minutes_per_mp(user) -> int:
    """获取每1MP需要的观影分钟数"""
    # 新手期：5分钟 = 1MP
    # 正常期：10分钟 = 1MP
    if user and is_newbie_user(user):
        return NEWBIE_MINUTES_PER_MP
    return MINUTES_PER_MP


async def get_recently_added_media(limit: int = 20) -> list:
    """获取最近添加的媒体"""
    headers = {
        "X-Emby-Token": EMBY_API_KEY,
        "Accept": "application/json",
        "User-Agent": "curl/7.68.0"
    }

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{EMBY_URL}/Items"
            params = {
                "SortBy": "DateCreated",
                "SortOrder": "Descending",
                "MediaTypes": "Video",
                "Limit": limit,
                "IncludeItemTypes": "Movie,Episode"
            }
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('Items', [])
    except Exception as e:
        logger.error(f"获取新媒体失败: {e}")

    return []


async def get_item_played_users(item_id: str) -> list:
    """获取已播放指定媒体的所有用户"""
    headers = {
        "X-Emby-Token": EMBY_API_KEY,
        "Accept": "application/json",
        "User-Agent": "curl/7.68.0"
    }

    try:
        async with aiohttp.ClientSession() as session:
            # 先获取所有用户
            users_url = f"{EMBY_URL}/Users"
            async with session.get(users_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return []
                users = await resp.json()

            played_users = []
            for user in users:
                user_id = user.get('Id')
                user_name = user.get('Name')
                # 检查用户是否播放过此媒体
                play_url = f"{EMBY_URL}/Users/{user_id}/Items"
                params = {
                    "Filters": "IsPlayed",
                    "Ids": item_id,
                    "Limit": 1
                }
                async with session.get(play_url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=5)) as play_resp:
                    if play_resp.status == 200:
                        play_data = await play_resp.json()
                        if play_data.get('Items'):
                            played_users.append({'user_id': user_id, 'user_name': user_name})

            return played_users
    except Exception as e:
        logger.error(f"获取播放用户失败: {e}")

    return []


async def check_emby_binding(tg_id: int) -> tuple:
    """检查 Emby 绑定状态"""
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=tg_id).first()
        if not user or not user.emby_account:
            return False, None
        return True, user.emby_account


async def cmd_watch_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看观影状态"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    has_emby, emby_account = await check_emby_binding(user_id)

    if not has_emby:
        await reply_with_auto_delete(msg, await get_unbound_message())
        return

    # 获取观影数据
    emby_users = await get_emby_users()
    emby_user_id = emby_users.get(emby_account)

    if not emby_user_id:
        await reply_with_auto_delete(
            msg,
            f"🎬 <b>【 观 影 状 态 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💔 未找到 Emby 用户: {emby_account}\n\n"
            f"请确认用户名是否正确喵~"
        )
        return

    # 获取今日观影时长
    today_minutes = await get_user_watch_time(emby_user_id)

    # 获取用户数据
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        total_watch = getattr(user, 'total_watch_minutes', 0)
        daily_watch = getattr(user, 'daily_watch_minutes', 0)
        last_claim = getattr(user, 'last_watch_claimed', None)
        early_birds = getattr(user, 'early_bird_wins', 0)

        # 计算今日可领取奖励
        claimable_minutes = max(0, today_minutes - daily_watch)
        claimable_minutes = min(claimable_minutes, DAILY_MAX_MINUTES - daily_watch)

        # 新手期使用更快的兑换率
        minutes_per_mp = get_minutes_per_mp(user)
        mp_reward = claimable_minutes // minutes_per_mp

        if user.is_vip:
            mp_reward = int(mp_reward * VIP_BONUS_MULTIPLIER)

        is_vip = user.is_vip

    # 计算今日剩余可领取
    remaining_daily = max(0, DAILY_MAX_MINUTES - today_minutes)

    # 新手提示
    newbie_badge = " 🌱新手期" if is_newbie_user(user) else ""
    newbie_hint = f"🌱 <b>新手加成: {minutes_per_mp}分钟 = 1 MP</b> (剩余{NEWBIE_DAYS - (datetime.now() - user.registered_date).days}天)\n" if is_newbie_user(user) else ""

    text = (
        f"🎬 <b>【 观 影 状 态 】{newbie_badge}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>账号:</b> {emby_account}\n"
        f"{'👑 VIP会员' if is_vip else '⭐ 普通用户'}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>今日观影:</b> {today_minutes} 分钟\n"
        f"💰 <b>已领取:</b> {daily_watch // minutes_per_mp} MP\n"
        f"🎁 <b>可领取:</b> +{mp_reward} MP ({claimable_minutes}分钟)\n"
        f"📅 <b>每日上限:</b> {DAILY_MAX_MINUTES}分钟 (剩余{remaining_daily}分钟)\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📺 <b>累计观影:</b> {total_watch} 分钟 ({total_watch//60}小时)\n"
        f"🏆 <b>首播奖励:</b> {early_birds} 次\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{newbie_hint}"
        f"💡 <b>{minutes_per_mp}分钟 = 1 MP</b> | VIP ×{VIP_BONUS_MULTIPLIER}\n"
    )

    if mp_reward > 0:
        keyboard = [[InlineKeyboardButton(f"🎁 领取 {mp_reward} MP", callback_data=f"claim_watch_reward")]]
        await msg.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    else:
        await reply_with_auto_delete(msg, text + f"\n<i>\"去看电影吧，Master~(｡•̀ᴗ-)✧\"</i>")


async def cmd_weekly_watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """每周观影排行榜"""
    msg = update.effective_message
    if not msg:
        return

    with get_session() as session:
        # 获取所有有 Emby 绑定的用户
        users = session.query(UserBinding).filter(
            UserBinding.emby_account != None,
            UserBinding.emby_account != ""
        ).all()

        # 按 total_watch_minutes 排序
        sorted_users = sorted(
            [u for u in users if hasattr(u, 'total_watch_minutes') and u.total_watch_minutes],
            key=lambda x: x.total_watch_minutes or 0,
            reverse=True
        )[:10]

    if not sorted_users:
        await reply_with_auto_delete(
            msg,
            "🏆 <b>【 观 影 排 行 榜 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "暂无观影记录喵~"
        )
        return

    lines = [
        "🏆 <b>【 观 影 排 行 榜 】</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"📊 统计截止: {datetime.now().strftime('%m-%d %H:%M')}",
        "━━━━━━━━━━━━━━━━━━",
    ]

    for i, user in enumerate(sorted_users, 1):
        minutes = user.total_watch_minutes or 0
        hours = minutes // 60
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i:2}."
        name = user.emby_account or f"用户{str(user.tg_id)[-4:]}"
        vip_tag = "👑" if user.is_vip else ""

        lines.append(f"{medal} {name}{vip_tag}: {hours}小时{minutes%60}分钟")

    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("<i>\"多看电影，既能娱乐又能赚 MP~(｡•̀ᴗ-)✧\"</i>")

    await reply_with_auto_delete(msg, "\n".join(lines))


async def claim_watch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """领取观影奖励回调"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    has_emby, emby_account = await check_emby_binding(user_id)
    if not has_emby:
        await query.edit_message_text(await get_unbound_message(), parse_mode='HTML')
        return

    # 获取观影数据
    emby_users = await get_emby_users()
    emby_user_id = emby_users.get(emby_account)

    if not emby_user_id:
        await query.edit_message_text("💔 未找到 Emby 账号")
        return

    today_minutes = await get_user_watch_time(emby_user_id)

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        daily_watch = getattr(user, 'daily_watch_minutes', 0)
        total_watch = getattr(user, 'total_watch_minutes', 0)

        # 计算可领取
        claimable_minutes = max(0, today_minutes - daily_watch)
        claimable_minutes = min(claimable_minutes, DAILY_MAX_MINUTES - daily_watch)

        if claimable_minutes <= 0:
            await query.edit_message_text(
                f"🎬 <b>【 观 影 奖 励 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💔 今天还没有新的观影记录喵~\n\n"
                f"📊 今日已观影: {today_minutes} 分钟\n"
                f"💰 已领取: {daily_watch // get_minutes_per_mp(user)} MP",
                parse_mode='HTML'
            )
            return

        # 新手期使用更快的兑换率
        minutes_per_mp = get_minutes_per_mp(user)
        mp_reward = claimable_minutes // minutes_per_mp

        if user.is_vip:
            mp_reward = int(mp_reward * VIP_BONUS_MULTIPLIER)

        # 更新数据
        user.daily_watch_minutes = daily_watch + claimable_minutes
        user.total_watch_minutes = (total_watch or 0) + claimable_minutes
        user.last_watch_claimed = datetime.now()
        user.points += mp_reward
        session.commit()

    await query.edit_message_text(
        f"🎬 <b>【 观 影 奖 励 领 取 成 功 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✨ 观影时长: +{claimable_minutes} 分钟\n"
        f"💰 获得: +{mp_reward} MP\n"
        f"{'👑 VIP加成 ×1.5' if user.is_vip else ''}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 余额: {user.points} MP\n"
        f"📊 今日观影: {today_minutes} 分钟\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"感谢使用 Emby 影音服务喵~\"</i>",
        parse_mode='HTML'
    )


async def process_watch_rewards_job(context):
    """定时任务：处理观影奖励（每小时执行一次）"""
    logger.info("开始处理观影奖励...")

    with get_session() as session:
        users = session.query(UserBinding).filter(
            UserBinding.emby_account != None,
            UserBinding.emby_account != ""
        ).all()

        emby_users = await get_emby_users()
        processed = 0

        for user in users:
            emby_user_id = emby_users.get(user.emby_account)
            if not emby_user_id:
                continue

            # 获取今日观影时长
            today_minutes = await get_user_watch_time(emby_user_id)
            if today_minutes == 0:
                continue

            daily_watch = getattr(user, 'daily_watch_minutes', 0)

            # 只有当有新观影时长时才更新
            if today_minutes > daily_watch:
                claimable_minutes = min(
                    today_minutes - daily_watch,
                    DAILY_MAX_MINUTES - daily_watch
                )

                if claimable_minutes >= MINUTES_PER_MP:
                    # 新手期使用更快的兑换率
                    minutes_per_mp = get_minutes_per_mp(user)
                    mp_reward = claimable_minutes // minutes_per_mp
                    if user.is_vip:
                        mp_reward = int(mp_reward * VIP_BONUS_MULTIPLIER)

                    user.daily_watch_minutes = daily_watch + claimable_minutes
                    user.total_watch_minutes = (user.total_watch_minutes or 0) + claimable_minutes
                    user.points += mp_reward

                    logger.info(f"用户 {user.tg_id} 观影奖励: +{mp_reward} MP ({claimable_minutes}分钟)")
                    processed += 1

        session.commit()
        logger.info(f"观影奖励处理完成: {processed} 人")


async def cmd_early_bird(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """首播冲刺活动面板"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    has_emby, emby_account = await check_emby_binding(user_id)
    if not has_emby:
        await reply_with_auto_delete(msg, await get_unbound_message())
        return

    # 获取新片列表
    recent_media = await get_recently_added_media(limit=20)

    # 获取当前用户的Emby ID
    emby_users = await get_emby_users()
    emby_user_id = emby_users.get(emby_account)

    if not emby_user_id:
        await reply_with_auto_delete(
            msg,
            f"🎬 【首播冲刺】\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💔 未找到 Emby 用户: {emby_account}\n\n"
            f"请确认用户名是否正确喵~"
        )
        return

    # 获取用户已观看的媒体
    headers = {
        "X-Emby-Token": EMBY_API_KEY,
        "Accept": "application/json",
        "User-Agent": "curl/7.68.0"
    }

    user_watched_ids = set()
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{EMBY_URL}/Users/{emby_user_id}/Items"
            params = {
                "Filters": "IsPlayed",
                "Limit": 1000,
                "IncludeItemTypes": "Movie,Episode"
            }
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    user_watched_ids = {item['Id'] for item in data.get('Items', [])}
    except Exception as e:
        logger.error(f"获取用户观看记录失败: {e}")

    # 获取用户已领取奖励的媒体
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        claimed_ids = set()
        if user and user.claimed_early_bird_items:
            claimed_ids = set(user.claimed_early_bird_items.split(',')) if user.claimed_early_bird_items else set()
        is_vip = user.is_vip if user else False
        early_birds = user.early_bird_wins or 0 if user else 0

    vip_badge = " 👑" if is_vip else ""

    # 构建活动列表
    lines = [
        "🏁 <b>【 新 片 首 播 冲 刺 】</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"👤 <b>玩家:</b> {emby_account}{vip_badge}",
        "━━━━━━━━━━━━━━━━━━",
        f"<i>🎬 新片上线{NEW_RELEASE_TIME_LIMIT_HOURS}小时内看完，前{NEW_RELEASE_LIMIT}名得奖励喵~</i>",
        "━━━━━━━━━━━━━━━━━━",
    ]

    now = datetime.now(timezone.utc)
    has_active_races = False

    for media in recent_media[:10]:
        item_id = media.get('Id')
        item_name = media.get('Name', '未知')
        item_type = media.get('Type', '')
        premiere_date = media.get('DateCreated', '')

        # 计算发布时间
        try:
            from datetime import datetime as dt
            if isinstance(premiere_date, str):
                premiere_time = dt.fromisoformat(premiere_date.replace('Z', '+00:00'))
            else:
                premiere_time = premiere_date
        except:
            continue

        hours_since = (now - premiere_time).total_seconds() / 3600

        # 只显示24小时内的新片
        if hours_since > NEW_RELEASE_TIME_LIMIT_HOURS:
            continue

        has_active_races = True

        # 判断状态
        has_watched = item_id in user_watched_ids
        has_claimed = item_id in claimed_ids

        # 类型图标
        type_icon = "🎬" if item_type == "Movie" else "📺"

        # 时间显示
        if hours_since < 1:
            time_str = "刚刚上线"
        elif hours_since < 24:
            time_str = f"{int(hours_since)}小时前"

        # 状态
        if has_claimed:
            status = "✅ 已领取"
        elif has_watched:
            status = "🎁 可领取"
        else:
            status = "🔴 未观看"

        # 奖励提示
        reward_text = f"({NEW_RELEASE_REWARD} MP)" if not has_claimed else ""

        lines.append(f"\n{type_icon} <b>{item_name}</b>")
        lines.append(f"   📅 {time_str} | {status} {reward_text}")

        if has_watched and not has_claimed:
            # 添加领取按钮
            lines.append(f"   <code>/claim_bird {item_id[:8]}</code>")

    if not has_active_races:
        # 空状态 - 显示说明和用户统计
        lines.append("\n📭 <b>当前没有进行中的首播冲刺</b>")
        lines.append("\n💡 <b>什么是首播冲刺？</b>")
        lines.append("新片上线后48小时内，前10名看完的用户可得奖励！")
        lines.append("\n🎁 <b>奖励规则:</b>")
        lines.append(f"   • 前{NEW_RELEASE_LIMIT}名: {NEW_RELEASE_REWARD} MP")
        lines.append(f"   • VIP用户: {int(NEW_RELEASE_REWARD * 1.5)} MP (×1.5)")
        lines.append(f"   • 时限: {NEW_RELEASE_TIME_LIMIT_HOURS}小时内")
        lines.append("\n📢 <b>开启推送:</b>")
        lines.append("联系管理员在群开启新片推送，有新片会自动通知！")
        lines.append(f"\n📊 <b>你的首播成绩:</b>")
        lines.append(f"   🏆 已获得: {early_birds} 次奖励")
        lines.append(f"   💰 累计奖励: {early_birds * NEW_RELEASE_REWARD} MP")
    else:
        lines.append("\n━━━━━━━━━━━━━━━━━━")
        lines.append(f"🎁 <b>奖励:</b> 前{NEW_RELEASE_LIMIT}名看完得 {NEW_RELEASE_REWARD} MP")
        lines.append(f"⏰ <b>时限:</b> 新片发布后 {NEW_RELEASE_TIME_LIMIT_HOURS} 小时内")

    lines.append("\n━━━━━━━━━━━━━━━━━━")
    lines.append(f"<i>\"拼手速的时候到了喵！(｡•̀ᴗ-)✧\"</i>")

    await reply_with_auto_delete(msg, "\n".join(lines))


async def cmd_claim_early_bird(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """领取首播冲刺奖励"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    has_emby, emby_account = await check_emby_binding(user_id)
    if not has_emby:
        await reply_with_auto_delete(msg, await get_unbound_message())
        return

    # 获取参数
    if not context.args or len(context.args) < 1:
        await reply_with_auto_delete(
            msg,
            "🎁 <b>【首播奖励领取】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💡 使用方法: <code>/claim_bird 媒体ID前8位</code>\n"
            "从首播冲刺面板中获取ID喵~"
        )
        return

    short_id = context.args[0]

    # 获取新片列表找到完整ID
    recent_media = await get_recently_added_media(limit=50)
    target_item = None
    for media in recent_media:
        if media.get('Id', '').startswith(short_id):
            target_item = media
            break

    if not target_item:
        await reply_with_auto_delete(
            msg,
            f"🎁 <b>【首播奖励领取】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💔 未找到媒体: {short_id}\n\n"
            f"请确认ID是否正确喵~"
        )
        return

    item_id = target_item['Id']
    item_name = target_item.get('Name', '未知')
    premiere_date = target_item.get('DateCreated', '')

    # 检查是否在24小时内
    now = datetime.now(timezone.utc)
    try:
        if isinstance(premiere_date, str):
            premiere_time = datetime.fromisoformat(premiere_date.replace('Z', '+00:00'))
        else:
            premiere_time = premiere_date
        hours_since = (now - premiere_time).total_seconds() / 3600
    except:
        hours_since = 999

    if hours_since > NEW_RELEASE_TIME_LIMIT_HOURS:
        await reply_with_auto_delete(
            msg,
            f"🎁 <b>【首播奖励领取】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💔 <b>{item_name}</b> 的首播活动已结束\n\n"
            f"下次要更快喵~"
        )
        return

    # 获取用户Emby ID
    emby_users = await get_emby_users()
    emby_user_id = emby_users.get(emby_account)

    if not emby_user_id:
        await reply_with_auto_delete(msg, "💔 未找到 Emby 账号")
        return

    # 检查是否看过
    headers = {
        "X-Emby-Token": EMBY_API_KEY,
        "Accept": "application/json",
        "User-Agent": "curl/7.68.0"
    }

    has_watched = False
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{EMBY_URL}/Users/{emby_user_id}/Items"
            params = {
                "Filters": "IsPlayed",
                "Ids": item_id,
                "Limit": 1
            }
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    has_watched = len(data.get('Items', [])) > 0
    except Exception as e:
        logger.error(f"检查观看状态失败: {e}")

    if not has_watched:
        await reply_with_auto_delete(
            msg,
            f"🎁 <b>【首播奖励领取】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💔 你还没看过 <b>{item_name}</b> 喵\n\n"
            f"先去看完再来领取吧~"
        )
        return

    # 检查和发放奖励
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not user:
            await reply_with_auto_delete(msg, "💔 用户不存在")
            return

        claimed_ids = set()
        if user.claimed_early_bird_items:
            claimed_ids = set(user.claimed_early_bird_items.split(',')) if user.claimed_early_bird_items else set()

        if item_id in claimed_ids:
            await reply_with_auto_delete(
                msg,
                f"🎁 <b>【首播奖励领取】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✅ <b>{item_name}</b> 的奖励已领取过\n\n"
                f"每个媒体只能领取一次喵~"
            )
            return

        # 统计当前有多少人看过了
        played_users = await get_item_played_users(item_id)
        current_rank = len(played_users)

        if current_rank > NEW_RELEASE_LIMIT:
            await reply_with_auto_delete(
                msg,
                f"🎁 <b>【首播奖励领取】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💔 <b>{item_name}</b> 的奖励名额已满\n\n"
                f"前{NEW_RELEASE_LIMIT}名已领完，下次要更快喵~\n"
                f"你的排名: 第{current_rank}名"
            )
            return

        # 发放奖励
        reward = NEW_RELEASE_REWARD
        if user.is_vip:
            reward = int(reward * 1.5)

        # 更新已领取列表
        claimed_ids.add(item_id)
        user.claimed_early_bird_items = ','.join(claimed_ids)
        user.early_bird_wins = (user.early_bird_wins or 0) + 1
        user.points += reward
        user.total_earned = (user.total_earned or 0) + reward
        session.commit()

        rank_emoji = ["🥇", "🥈", "🥉"][current_rank - 1] if current_rank <= 3 else f"#{current_rank}"

        await reply_with_auto_delete(
            msg,
            f"🎉 <b>【 首 播 冲 刺 成 功 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏁 <b>{item_name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{rank_emoji} 你的排名: <b>第 {current_rank} 名</b>\n"
            f"🎁 获得奖励: <b>+{reward} MP</b>\n"
            f"{'👑 VIP加成 ×1.5' if user.is_vip else ''}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏆 累计首播奖励: {user.early_bird_wins} 次\n"
            f"💰 余额: {user.points} MP\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>\"手速不错嘛 Master！(｡•̀ᴗ-)✧\"</i>"
        )


async def cmd_watch_recommend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """观影推荐 - 随机推荐一部精彩影片"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    has_emby, emby_account = await check_emby_binding(user_id)
    if not has_emby:
        await reply_with_auto_delete(msg, await get_unbound_message())
        return

    # 获取随机媒体
    headers = {
        "X-Emby-Token": EMBY_API_KEY,
        "Accept": "application/json",
        "User-Agent": "curl/7.68.0"
    }

    try:
        async with aiohttp.ClientSession() as session:
            # 获取电影和剧集总数
            url = f"{EMBY_URL}/Items"
            params = {
                "IncludeItemTypes": "Movie,Episode",
                "Recursive": True,
                "Limit": 1
            }
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    raise Exception("获取媒体失败")
                data = await resp.json()
                total_count = data.get('TotalRecordCount', 0)

            if total_count == 0:
                await reply_with_auto_delete(msg, "📭 媒体库空空如也喵~")
                return

            # 随机选取
            import random
            random_offset = random.randint(0, max(0, total_count - 1))

            params = {
                "IncludeItemTypes": "Movie,Episode",
                "Recursive": True,
                "StartIndex": random_offset,
                "Limit": 1
            }
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    raise Exception("获取推荐失败")
                data = await resp.json()
                items = data.get('Items', [])
                if not items:
                    await reply_with_auto_delete(msg, "📭 推荐获取失败喵~")
                    return

                item = items[0]
                item_name = item.get('Name', '未知')
                item_type = item.get('Type', '')
                production_year = item.get('ProductionYear', '')
                genres = item.get('Genres', [])
                overview = item.get('Overview', '')

                type_icon = "🎬" if item_type == "Movie" else "📺"
                genre_text = f"{' | '.join(genres[:3])}" if genres else "未分类"

                # 截断简介
                if overview and len(overview) > 100:
                    overview = overview[:100] + "..."

                lines = [
                    f"🎲 <b>【 今 日 观 影 推 荐 】</b>",
                    "━━━━━━━━━━━━━━━━━━",
                    f"{type_icon} <b>{item_name}</b>",
                    f"📅 {production_year}" if production_year else "",
                    f"🏷️ {genre_text}" if genre_text else "",
                    "━━━━━━━━━━━━━━━━━━",
                ]

                if overview:
                    lines.append(f"📝 {overview}")
                    lines.append("━━━━━━━━━━━━━━━━━━")

                lines.append(f"<i>\"今天就看这个吧 Master！(｡•̀ᴗ-)✧\"</i>")

                await reply_with_auto_delete(msg, "\n".join(lines))

    except Exception as e:
        logger.error(f"观影推荐失败: {e}")
        await reply_with_auto_delete(msg, f"💔 推荐获取失败: {str(e)}")


async def cmd_watch_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """观影统计报告"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    has_emby, emby_account = await check_emby_binding(user_id)
    if not has_emby:
        await reply_with_auto_delete(msg, await get_unbound_message())
        return

    emby_users = await get_emby_users()
    emby_user_id = emby_users.get(emby_account)

    if not emby_user_id:
        await reply_with_auto_delete(msg, "💔 未找到 Emby 账号")
        return

    # 获取用户统计数据
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user:
            await reply_with_auto_delete(msg, "💔 用户不存在")
            return

        total_watch = user.total_watch_minutes or 0
        early_birds = user.early_bird_wins or 0
        is_vip = user.is_vip
        registered_date = user.registered_date
        checkin_days = user.total_checkin_days or 0

    # 计算观影数据
    hours = total_watch // 60
    minutes = total_watch % 60

    # 计算会员天数
    member_days = 0
    if registered_date:
        member_days = (datetime.now() - registered_date.replace(tzinfo=None)).days + 1

    # 获取用户观看的媒体数量
    headers = {
        "X-Emby-Token": EMBY_API_KEY,
        "Accept": "application/json",
        "User-Agent": "curl/7.68.0"
    }

    movies_watched = 0
    episodes_watched = 0
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{EMBY_URL}/Users/{emby_user_id}/Items"
            params = {
                "Filters": "IsPlayed",
                "Limit": 10000
            }
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get('Items', []):
                        if item.get('Type') == 'Movie':
                            movies_watched += 1
                        elif item.get('Type') == 'Episode':
                            episodes_watched += 1
    except Exception as e:
        logger.error(f"获取观看统计失败: {e}")

    vip_badge = " 👑" if is_vip else ""

    # 计算等级
    watch_level = 1
    watch_exp = total_watch // 60  # 1小时=1经验
    if watch_exp >= 1000:
        watch_level = 10
    elif watch_exp >= 500:
        watch_level = 9
    elif watch_exp >= 300:
        watch_level = 8
    elif watch_exp >= 200:
        watch_level = 7
    elif watch_exp >= 150:
        watch_level = 6
    elif watch_exp >= 100:
        watch_level = 5
    elif watch_exp >= 50:
        watch_level = 4
    elif watch_exp >= 20:
        watch_level = 3
    elif watch_exp >= 10:
        watch_level = 2

    level_titles = {
        1: "见习观众",
        2: "初级观众", 3: "进阶观众", 4: "资深观众",
        5: "影迷", 6: "资深影迷", 7: "影评人",
        8: "影视专家", 9: "鉴赏大师", 10: "观影之神"
    }

    lines = [
        "📊 <b>【 观 影 统 计 报 告 】</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"👤 <b>观众:</b> {emby_account}{vip_badge}",
        f"🎖️ <b>等级:</b> LV.{watch_level} {level_titles.get(watch_level, '观众')}",
        f"📅 <b>入会:</b> {member_days} 天 | 签到 {checkin_days} 次",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "📺 <b>观影数据</b>",
        f"   🎬 电影: {movies_watched} 部",
        f"   📺 剧集: {episodes_watched} 集",
        f"   ⏱️ 总时长: {hours}小时{minutes}分钟",
        "",
        "🏆 <b>成就数据</b>",
        f"   🏁 首播奖励: {early_birds} 次",
        f"   💎 观影经验: {watch_exp} 点",
        "",
        "💡 <b>观影建议</b>",
    ]

    # 根据数据给出建议
    if total_watch < 60:
        lines.append("   多看点片，提升等级喵~")
    elif total_watch < 300:
        lines.append("   继续保持，即将升级！")
    elif early_birds >= 5:
        lines.append("   你是抢片达人！")
    else:
        lines.append("   观影量不错，继续加油！")

    lines.extend([
        "━━━━━━━━━━━━━━━━━━",
        f"<i>\"感谢使用云海影视服务喵！(｡•̀ᴗ-)✧\"</i>"
    ])

    await reply_with_auto_delete(msg, "\n".join(lines))


# ==================== 观影成就系统 ====================

WATCH_ACHIEVEMENTS = {
    "watch_1h": {"name": "观影新手", "desc": "累计观影1小时", "target_minutes": 60, "reward": 50},
    "watch_5h": {"name": "初级影迷", "desc": "累计观影5小时", "target_minutes": 300, "reward": 100},
    "watch_10h": {"name": "进阶影迷", "desc": "累计观影10小时", "target_minutes": 600, "reward": 200},
    "watch_50h": {"name": "资深影迷", "desc": "累计观影50小时", "target_minutes": 3000, "reward": 500},
    "watch_100h": {"name": "观影达人", "desc": "累计观影100小时", "target_minutes": 6000, "reward": 1000},
    "watch_500h": {"name": "影视专家", "desc": "累计观影500小时", "target_minutes": 30000, "reward": 5000},
    "movies_10": {"name": "十部佳片", "desc": "观看10部电影", "target_movies": 10, "reward": 100},
    "movies_50": {"name": "电影收藏家", "desc": "观看50部电影", "target_movies": 50, "reward": 500},
    "early_bird_5": {"name": "抢片达人", "desc": "获得5次首播奖励", "target_early_bird": 5, "reward": 200},
    "early_bird_20": {"name": "首播之王", "desc": "获得20次首播奖励", "target_early_bird": 20, "reward": 1000},
    "weekly_10": {"name": "挑战勇士", "desc": "完成10次周挑战", "target_weekly": 10, "reward": 500},
}


async def check_watch_achievements(user, session, emby_user_id=None):
    """检查并发放观影成就"""
    new_achievements = []

    claimed = set()
    if user.watch_achievements:
        claimed = set(user.watch_achievements.split(',')) if user.watch_achievements else set()

    total_minutes = user.total_watch_minutes or 0
    early_birds = user.early_bird_wins or 0
    weekly_completed = user.weekly_challenge_completed or 0

    # 获取观看的电影数量
    movies_count = 0
    if emby_user_id:
        try:
            headers = {
                "X-Emby-Token": EMBY_API_KEY,
                "Accept": "application/json",
                "User-Agent": "curl/7.68.0"
            }
            async with aiohttp.ClientSession() as session_http:
                url = f"{EMBY_URL}/Users/{emby_user_id}/Items"
                params = {"Filters": "IsPlayed", "Limit": 10000, "IncludeItemTypes": "Movie"}
                async with session_http.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        movies_count = len(data.get('Items', []))
        except Exception:
            pass

    for ach_id, ach_data in WATCH_ACHIEVEMENTS.items():
        if ach_id in claimed:
            continue

        unlocked = False
        if "target_minutes" in ach_data and total_minutes >= ach_data["target_minutes"]:
            unlocked = True
        elif "target_movies" in ach_data and movies_count >= ach_data["target_movies"]:
            unlocked = True
        elif "target_early_bird" in ach_data and early_birds >= ach_data["target_early_bird"]:
            unlocked = True
        elif "target_weekly" in ach_data and weekly_completed >= ach_data["target_weekly"]:
            unlocked = True

        if unlocked:
            claimed.add(ach_id)
            user.watch_achievements = ','.join(claimed)
            user.points += ach_data["reward"]
            user.total_earned = (user.total_earned or 0) + ach_data["reward"]
            session.commit()
            new_achievements.append({
                "id": ach_id,
                "name": ach_data["name"],
                "desc": ach_data["desc"],
                "reward": ach_data["reward"]
            })

    return new_achievements


async def cmd_watch_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看观影成就"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    has_emby, emby_account = await check_emby_binding(user_id)
    if not has_emby:
        await reply_with_auto_delete(msg, await get_unbound_message())
        return

    emby_users = await get_emby_users()
    emby_user_id = emby_users.get(emby_account)

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user:
            await reply_with_auto_delete(msg, "💔 用户不存在")
            return

        total_minutes = user.total_watch_minutes or 0
        early_birds = user.early_bird_wins or 0
        weekly_completed = user.weekly_challenge_completed or 0
        is_vip = user.is_vip

        claimed = set()
        if user.watch_achievements:
            claimed = set(user.watch_achievements.split(',')) if user.watch_achievements else set()

    # 获取观看的电影数量
    movies_count = 0
    if emby_user_id:
        try:
            headers = {
                "X-Emby-Token": EMBY_API_KEY,
                "Accept": "application/json",
                "User-Agent": "curl/7.68.0"
            }
            async with aiohttp.ClientSession() as session_http:
                url = f"{EMBY_URL}/Users/{emby_user_id}/Items"
                params = {"Filters": "IsPlayed", "Limit": 10000, "IncludeItemTypes": "Movie"}
                async with session_http.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        movies_count = len(data.get('Items', []))
        except Exception:
            pass

    vip_badge = " 👑" if is_vip else ""

    lines = [
        "🏆 <b>【 观 影 成 就 殿 堂 】</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"👤 <b>观众:</b> {emby_account}{vip_badge}",
        f"📊 已解锁: <b>{len(claimed)}/{len(WATCH_ACHIEVEMENTS)}</b>",
        "━━━━━━━━━━━━━━━━━━",
    ]

    for ach_id, ach_data in WATCH_ACHIEVEMENTS.items():
        is_unlocked = ach_id in claimed

        # 计算进度
        progress = 0
        if "target_minutes" in ach_data:
            progress = min(100, int(total_minutes / ach_data["target_minutes"] * 100))
            current = f"{total_minutes // 60}h"
            target = f"{ach_data['target_minutes'] // 60}h"
        elif "target_movies" in ach_data:
            progress = min(100, int(movies_count / ach_data["target_movies"] * 100))
            current = str(movies_count)
            target = str(ach_data["target_movies"])
        elif "target_early_bird" in ach_data:
            progress = min(100, int(early_birds / ach_data["target_early_bird"] * 100))
            current = str(early_birds)
            target = str(ach_data["target_early_bird"])
        elif "target_weekly" in ach_data:
            progress = min(100, int(weekly_completed / ach_data["target_weekly"] * 100))
            current = str(weekly_completed)
            target = str(ach_data["target_weekly"])

        if is_unlocked:
            status = "✅"
            reward_text = f"(+{ach_data['reward']}MP)"
        else:
            status = "🔒"
            reward_text = ""

        lines.append(f"\n{status} <b>{ach_data['name']}</b> {reward_text}")
        lines.append(f"   {ach_data['desc']}")
        if not is_unlocked:
            lines.append(f"   进度: {current}/{target} ({progress}%)")

    lines.append("\n━━━━━━━━━━━━━━━━━━")
    total_reward = sum(a["reward"] for a in WATCH_ACHIEVEMENTS.values())
    claimed_reward = sum(WATCH_ACHIEVEMENTS[aid]["reward"] for aid in claimed if aid in WATCH_ACHIEVEMENTS)
    lines.append(f"💰 奖励: {claimed_reward}/{total_reward} MP")
    lines.append("\n<i>\"继续观影，解锁更多成就喵！(｡•̀ᴗ-)✧\"</i>")

    await reply_with_auto_delete(msg, "\n".join(lines))


# ==================== 每周观影挑战 ====================

async def cmd_weekly_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """每周观影挑战"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    has_emby, emby_account = await check_emby_binding(user_id)
    if not has_emby:
        await reply_with_auto_delete(msg, await get_unbound_message())
        return

    emby_users = await get_emby_users()
    emby_user_id = emby_users.get(emby_account)

    if not emby_user_id:
        await reply_with_auto_delete(msg, "💔 未找到 Emby 账号")
        return

    # 获取本周开始时间（周一0点）
    from datetime import timedelta as td
    now = datetime.now()
    weekday = now.weekday()  # 0=周一, 6=周日
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - td(days=weekday)
    week_end = week_start + td(days=7)

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user:
            await reply_with_auto_delete(msg, "💔 用户不存在")
            return

        is_vip = user.is_vip
        completed_count = user.weekly_challenge_completed or 0

        # 初始化本周挑战
        if not user.weekly_challenge_target:
            # 新用户默认30分钟目标（降低门槛）
            user.weekly_challenge_target = 30
            session.commit()

        target = user.weekly_challenge_target
        progress = user.weekly_challenge_progress or 0
        reward_claimed = user.weekly_challenge_reward_claimed

        # 检查是否需要重置（新的一周）
        if user.task_date:
            last_task = user.task_date.replace(tzinfo=None)
            if last_task < week_start:
                # 新的一周，重置进度
                user.weekly_challenge_progress = 0
                user.weekly_challenge_reward_claimed = False
                # 根据上周完成情况调整目标
                if progress >= target:
                    user.weekly_challenge_target = min(600, target + 30)  # 增加目标，最多600分钟
                else:
                    user.weekly_challenge_target = max(30, target - 15)  # 降低目标，最少30分钟
                session.commit()
                target = user.weekly_challenge_target
                progress = 0
                reward_claimed = False

        # 更新任务日期
        user.task_date = now
        session.commit()

    # 获取本周实际观影时长（从Emby）
    headers = {
        "X-Emby-Token": EMBY_API_KEY,
        "Accept": "application/json",
        "User-Agent": "curl/7.68.0"
    }

    week_watch_minutes = 0
    try:
        async with aiohttp.ClientSession() as session_http:
            url = f"{EMBY_URL}/Users/{emby_user_id}/Items"
            params = {
                "Filters": "IsPlayed",
                "MinDatePlayed": week_start.isoformat(),
                "Limit": 1000
            }
            async with session_http.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get('Items', []):
                        if item.get('RunTimeTicks'):
                            week_watch_minutes += (item['RunTimeTicks'] // 10000000) // 60
    except Exception as e:
        logger.error(f"获取本周观影数据失败: {e}")

    # 更新进度
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        user.weekly_challenge_progress = week_watch_minutes
        session.commit()

    progress_pct = min(100, int(week_watch_minutes / target * 100)) if target > 0 else 0
    is_completed = week_watch_minutes >= target

    vip_badge = " 👑" if is_vip else ""

    # 计算奖励
    base_reward = target // 2  # 目标的一半作为奖励
    if is_vip:
        base_reward = int(base_reward * 1.5)

    # 进度条
    bars = "█" * (progress_pct // 5) + "░" * (20 - progress_pct // 5)

    lines = [
        "🎯 <b>【 每 周 观 影 挑 战 】</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"👤 <b>挑战者:</b> {emby_account}{vip_badge}",
        f"📅 <b>本周:</b> {week_start.strftime('%m-%d')} - {week_end.strftime('%m-%d')}",
        "━━━━━━━━━━━━━━━━━━",
        "",
        f"🎯 <b>本周目标:</b> {target} 分钟观影",
        f"📊 <b>当前进度:</b> {week_watch_minutes} / {target} 分钟",
        f"   {bars} {progress_pct}%",
        "",
    ]

    if is_completed:
        if reward_claimed:
            lines.append("✅ <b>本周挑战已完成并领取奖励！</b>")
        else:
            lines.append(f"🎉 <b>挑战完成！可领取 {base_reward} MP</b>")
            lines.append("发送 <code>/claim_weekly</code> 领取奖励")
    else:
        remaining = target - week_watch_minutes
        lines.append(f"💪 <b>还需观看:</b> {remaining} 分钟")

    lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━",
        f"🏆 累计完成: {completed_count} 次周挑战",
        "━━━━━━━━━━━━━━━━━━",
        "<i>\"每周观影，健康生活喵！(｡•̀ᴗ-)✧\"</i>"
    ])

    await reply_with_auto_delete(msg, "\n".join(lines))


async def cmd_claim_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """领取周挑战奖励"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    has_emby, emby_account = await check_emby_binding(user_id)
    if not has_emby:
        await reply_with_auto_delete(msg, await get_unbound_message())
        return

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user:
            await reply_with_auto_delete(msg, "💔 用户不存在")
            return

        target = user.weekly_challenge_target or 60
        progress = user.weekly_challenge_progress or 0
        reward_claimed = user.weekly_challenge_reward_claimed

        if progress < target:
            await reply_with_auto_delete(
                msg,
                f"🎯 <b>【周挑战】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💔 挑战未完成\n\n"
                f"进度: {progress}/{target} 分钟\n"
                f"还差 {target - progress} 分钟喵~"
            )
            return

        if reward_claimed:
            await reply_with_auto_delete(
                msg,
                f"🎯 <b>【周挑战】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✅ 本周奖励已领取过\n\n"
                f"下周再来吧喵~"
            )
            return

        # 发放奖励
        base_reward = target // 2
        if user.is_vip:
            base_reward = int(base_reward * 1.5)

        user.weekly_challenge_reward_claimed = True
        user.weekly_challenge_completed = (user.weekly_challenge_completed or 0) + 1
        user.points += base_reward
        user.total_earned = (user.total_earned or 0) + base_reward
        session.commit()

        await reply_with_auto_delete(
            msg,
            f"🎉 <b>【 周 挑 战 成 功 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ 目标: {target} 分钟\n"
            f"✅ 完成: {progress} 分钟\n"
            f"💰 奖励: +{base_reward} MP\n"
            f"{'👑 VIP加成 ×1.5' if user.is_vip else ''}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏆 累计完成: {user.weekly_challenge_completed} 次\n"
            f"💰 余额: {user.points} MP\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>\"下周目标会更高，加油喵！(｡•̀ᴗ-)✧\"</i>"
        )

        # 检查成就
        emby_users = await get_emby_users()
        emby_user_id = emby_users.get(emby_account)
        new_achievements = await check_watch_achievements(user, session, emby_user_id)


# ==================== VIP观影特权 ====================

async def cmd_vip_watch_benefits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """VIP观影特权面板"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    has_emby, emby_account = await check_emby_binding(user_id)
    if not has_emby:
        await reply_with_auto_delete(msg, await get_unbound_message())
        return

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user:
            await reply_with_auto_delete(msg, "💔 用户不存在")
            return

        is_vip = user.is_vip

    if is_vip:
        lines = [
            "👑 <b>【 V I P 观 影 特 权 】</b>",
            "━━━━━━━━━━━━━━━━━━",
            f"👤 <b>VIP会员:</b> {emby_account}",
            "✅ <b>已激活所有特权</b>",
            "━━━━━━━━━━━━━━━━━━",
            "",
            "🎁 <b>专属特权:</b>",
            "",
            "   📺 <b>观影收益 ×1.5</b>",
            "      每日观影奖励加成50%",
            "",
            "   🏁 <b>首播奖励 ×1.5</b>",
            "      新片冲刺奖励加成50%",
            "",
            "   🎯 <b>周挑战奖励 ×1.5</b>",
            "      每周挑战奖励加成50%",
            "",
            "   🍬 <b>每日签到 ×1.5</b>",
            "      每日签到奖励加成50%",
            "",
            "   ⚒️ <b>锻造费用 ×0.5</b>",
            "      武器锻造享受5折优惠",
            "",
            "━━━━━━━━━━━━━━━━━━",
            "<i>\"尊贵VIP，专属礼遇喵！(｡•̀ᴗ-)✧\"</i>"
        ]
    else:
        lines = [
            "👑 <b>【 V I P 观 影 特 权 】</b>",
            "━━━━━━━━━━━━━━━━━━",
            f"👤 <b>用户:</b> {emby_account}",
            "🔒 <b>未开通VIP</b>",
            "━━━━━━━━━━━━━━━━━━",
            "",
            "🎁 <b>VIP专属特权:</b>",
            "",
            "   📺 <b>观影收益 ×1.5</b>",
            "      每日观影奖励加成50%",
            "",
            "   🏁 <b>首播奖励 ×1.5</b>",
            "      新片冲刺奖励加成50%",
            "",
            "   🎯 <b>周挑战奖励 ×1.5</b>",
            "      每周挑战奖励加成50%",
            "",
            "   🍬 <b>每日签到 ×1.5</b>",
            "      每日签到奖励加成50%",
            "",
            "   ⚒️ <b>锻造费用 ×0.5</b>",
            "      武器锻造享受5折优惠",
            "",
            "━━━━━━━━━━━━━━━━━━",
            "💡 <b>如何开通VIP?</b>",
            "联系管理员申请开通喵~",
            "━━━━━━━━━━━━━━━━━━",
            "<i>\"成为VIP，享受更多特权喵！(｡•̀ᴗ-)✧\"</i>"
        ]

    await reply_with_auto_delete(msg, "\n".join(lines))


# ==================== 新片自动推送 ====================

async def check_and_announce_new_releases(context):
    """定时检查并推送新片到配置的群组"""
    if not EMBY_URL or not EMBY_API_KEY:
        return

    if not NOTIFICATION_CHATS:
        return

    try:
        # 获取最近添加的媒体（最近24小时）
        recent_media = await get_recently_added_media(limit=50)

        now = datetime.now(timezone.utc)
        new_items = []

        for media in recent_media:
            item_id = media.get('Id')
            item_name = media.get('Name', '未知')
            item_type = media.get('Type', '')
            premiere_date = media.get('DateCreated', '')
            production_year = media.get('ProductionYear', '')
            genres = media.get('Genres', [])
            overview = media.get('Overview', '')

            # 跳过已推送的
            if item_id in announced_items:
                continue

            # 检查是否是48小时内的新片
            try:
                if isinstance(premiere_date, str):
                    premiere_time = datetime.fromisoformat(premiere_date.replace('Z', '+00:00'))
                else:
                    premiere_time = premiere_date
                hours_since = (now - premiere_time).total_seconds() / 3600
            except:
                continue

            if hours_since > NEW_RELEASE_TIME_LIMIT_HOURS:
                continue

            # 只推送电影和剧集
            if item_type not in ['Movie', 'Episode']:
                continue

            new_items.append({
                'id': item_id,
                'name': item_name,
                'type': item_type,
                'year': production_year,
                'genres': genres,
                'overview': overview,
                'premiere_time': premiere_time
            })

            # 标记为已推送
            announced_items.add(item_id)

        # 如果有新片，发送通知
        if new_items:
            for item in new_items:
                await send_new_release_notification(context, item)

            logger.info(f"推送了 {len(new_items)} 部新片")

    except Exception as e:
        logger.error(f"检查新片失败: {e}")


async def send_new_release_notification(context, item):
    """发送新片通知到配置的群组"""
    type_icon = "🎬" if item['type'] == "Movie" else "📺"
    type_name = "电影" if item['type'] == "Movie" else "剧集"

    # 构建类型标签
    genre_text = f"{' | '.join(item['genres'][:3])}" if item['genres'] else "未分类"

    # 截断简介
    overview = item.get('overview', '')
    if overview and len(overview) > 80:
        overview = overview[:80] + "..."

    # 计算发布时间
    hours_ago = int((datetime.now(timezone.utc) - item['premiere_time']).total_seconds() / 3600)
    time_str = f"{hours_ago}小时前" if hours_ago > 0 else "刚刚"

    text = (
        f"🎉 <b>【 新 片 上 线 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{type_icon} <b>{item['name']}</b>\n"
        f"📅 {item['year']} | {type_name} | {time_str}\n"
        f"🏷️ {genre_text}\n"
    )

    if overview:
        text += f"\n📝 {overview}\n"

    text += (
        f"\n━━━━━━━━━━━━━━━━━━\n"
        f"🏁 <b>首播冲刺进行中！</b>\n"
        f"前10名看完得 <b>{NEW_RELEASE_REWARD} MP</b>\n"
        f"48小时内有效 | 发送 <code>/early_bird</code> 查看\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"拼手速的时候到了喵！(｡•̀ᴗ-)✧\"</i>"
    )

    # 发送到所有配置的群组
    for chat_id in NOTIFICATION_CHATS:
        try:
            chat_id = chat_id.strip()
            if not chat_id:
                continue
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        except Exception as e:
            logger.error(f"发送通知到群组 {chat_id} 失败: {e}")


async def cmd_notify_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """配置/查看新片推送设置"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    # 简单的管理员检查（这里可以加强）
    # 暂时只显示配置状态

    lines = [
        "📢 <b>【 新 片 推 送 设 置 】</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
    ]

    if NOTIFICATION_CHATS:
        lines.append(f"✅ <b>已启用推送</b>\n")
        lines.append(f"📱 推送群组 ({len(NOTIFICATION_CHATS)}个):")
        for chat in NOTIFICATION_CHATS:
            lines.append(f"   • {chat.strip()}")
    else:
        lines.append("❌ <b>未启用推送</b>\n")
        lines.append("💡 <b>如何启用：</b>")
        lines.append("在 docker-compose.yml 中设置:")
        lines.append("<code>EMBY_NOTIFY_CHATS=-1001234567890,-1009876543210</code>")
        lines.append("\n多个群组用逗号分隔")

    lines.extend([
        "\n━━━━━━━━━━━━━━━━━━",
        f"⏰ 检查频率: 每{CHECK_NEW_RELEASES_INTERVAL//60}分钟",
        f"🕐 推送窗口: 新片{NEW_RELEASE_TIME_LIMIT_HOURS}小时内",
        "\n<i>\"有新片上线时会自动推送喵~(｡•̀ᴗ-)✧\"</i>"
    ])

    await reply_with_auto_delete(msg, "\n".join(lines))


def register(app):
    # 观影状态和排行榜
    app.add_handler(CommandHandler("watch_status", cmd_watch_status))
    app.add_handler(CommandHandler("weekly_watch", cmd_weekly_watch))
    app.add_handler(CommandHandler("watch_rank", cmd_weekly_watch))

    # 首播冲刺系统
    app.add_handler(CommandHandler("early_bird", cmd_early_bird))
    app.add_handler(CommandHandler("sprint", cmd_early_bird))
    app.add_handler(CommandHandler("new_release", cmd_early_bird))
    app.add_handler(CommandHandler("claim_bird", cmd_claim_early_bird))

    # 观影推荐
    app.add_handler(CommandHandler("recommend", cmd_watch_recommend))
    app.add_handler(CommandHandler("movie", cmd_watch_recommend))
    app.add_handler(CommandHandler("watch_recommend", cmd_watch_recommend))

    # 观影统计
    app.add_handler(CommandHandler("watch_stats", cmd_watch_stats))
    app.add_handler(CommandHandler("my_stats", cmd_watch_stats))

    # 观影成就
    app.add_handler(CommandHandler("watch_achievements", cmd_watch_achievements))
    app.add_handler(CommandHandler("watch_ach", cmd_watch_achievements))
    app.add_handler(CommandHandler("watch_badge", cmd_watch_achievements))

    # 每周观影挑战
    app.add_handler(CommandHandler("weekly_challenge", cmd_weekly_challenge))
    app.add_handler(CommandHandler("week_challenge", cmd_weekly_challenge))
    app.add_handler(CommandHandler("weekly", cmd_weekly_challenge))
    app.add_handler(CommandHandler("claim_weekly", cmd_claim_weekly))

    # VIP观影特权
    app.add_handler(CommandHandler("vip_watch", cmd_vip_watch_benefits))
    app.add_handler(CommandHandler("vip_benefit", cmd_vip_watch_benefits))

    # 新片推送配置
    app.add_handler(CommandHandler("notify_config", cmd_notify_config))
    app.add_handler(CommandHandler("notify", cmd_notify_config))

    # 观影奖励回调
    app.add_handler(CallbackQueryHandler(claim_watch_callback, pattern="^claim_watch_reward$"))

    # 注册定时任务（检查新片推送）
    # 注意：需要在主程序中配置 job queue
    if hasattr(app, 'job_queue') and app.job_queue:
        app.job_queue.run_repeating(check_and_announce_new_releases, CHECK_NEW_RELEASES_INTERVAL, first=10)
        logger.info(f"新片推送任务已启动: 每{CHECK_NEW_RELEASES_INTERVAL//60}分钟检查一次")
    else:
        logger.warning("Job queue 未启用，新片推送功能不可用")
