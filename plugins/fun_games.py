"""
娱乐功能模块 - 魔法少女版
- 🎰 命运盲盒 (Emby电影抽取)
- ⚔️ 魔法少女决斗 (PVP互动)

盲盒系统：
- 从 Emby 媒体库随机抽取电影
- 根据评分+随机因素判定稀有度
- 抽到的电影存入背包
- UR/SSR 返利 MP
- 每日免费一次，额外抽取消耗 MP
"""
import random
import uuid
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from database import get_session, UserBinding
from utils import reply_with_auto_delete
from config import Config

# 正面反馈增强
from plugins.feedback_utils import get_crit_effect, success_burst, get_rarity_effect
from plugins.quotes import get_duel_victory_quote, get_duel_defeat_comfort, random_cute_emoji
from plugins.lucky_events import check_lucky_with_streak, calculate_lucky_reward

logger = logging.getLogger(__name__)


# ==========================================
# 任务追踪包装函数
# ==========================================
async def track_activity_wrapper(user_id: int, activity_type: str):
    """包装函数，延迟导入避免循环依赖"""
    from plugins.unified_mission import track_and_check_task
    await track_and_check_task(user_id, activity_type)


# Emby API 配置
EMBY_URL = Config.EMBY_URL.rstrip('/')
EMBY_API_KEY = Config.EMBY_API_KEY
EMBY_USER_ID = "f622565cba214bfca04609d32d5d26d0"  # 默认用户ID

# ==========================================
# 🔮 Emby API 工具函数
# ==========================================

def get_emby_headers():
    """获取 Emby API 请求头"""
    return {
        "X-Emby-Token": EMBY_API_KEY,
        "Accept": "application/json",
        "User-Agent": "curl/7.68.0"
    }

async def fetch_random_movie() -> dict:
    """从 Emby 获取随机电影（使用 aiohttp）"""
    import aiohttp
    import warnings
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    if not EMBY_URL or not EMBY_API_KEY:
        logger.error("Emby 配置不完整")
        return None

    url = (
        f"{EMBY_URL}/Users/{EMBY_USER_ID}/Items"
        f"?SortBy=Random"
        f"&Recursive=true"
        f"&IncludeItemTypes=Movie"
        f"&Limit=50"
        f"&Fields=CommunityRating,ProductionYear,Genres,Overview"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=get_emby_headers(), ssl=False, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Emby API 返回状态码: {resp.status}, 响应: {text[:200]}")
                    return None
                data = await resp.json()
                items = data.get('Items', [])
                if not items:
                    logger.warning("Emby 媒体库为空")
                    return None
                return random.choice(items)
    except asyncio.TimeoutError:
        logger.error("Emby API 请求超时")
        return None
    except Exception as e:
        logger.error(f"Emby API 请求失败: {e}", exc_info=True)
        return None


def calculate_rarity(item: dict) -> tuple:
    """
    根据评分 + 随机因素计算稀有度（手游风格爆率）

    爆率参考：
    - UR: ~1% (评分8.5+ + 5%暴击)
    - SSR: ~4% (评分7.5+ + 10%暴击)
    - SR: ~15% (评分6.5+ + 25%暴击)
    - R: ~40%
    - N: ~40%

    返回: (稀有度代码, emoji, 名称, 返利MP)
    """
    score = item.get('CommunityRating') or 5.0

    # UR: 评分 ≥ 8.5 + 5% 暴击
    if score >= 8.5 and random.random() < 0.05:
        return "UR", "🌈", "UR (Ultra Rare)", 500
    # SSR: 评分 ≥ 7.5 + 10% 暴击
    if score >= 7.5 and random.random() < 0.10:
        return "SSR", "🟡", "SSR (Super Super Rare)", 100
    # SR: 评分 ≥ 6.5 + 25% 暴击
    if score >= 6.5 and random.random() < 0.25:
        return "SR", "🟣", "SR (Super Rare)", 20
    # R: 评分 ≥ 4.0
    if score >= 4.0:
        return "R", "🔵", "R (Rare)", 0
    # N: 评分 < 4.0 (小概率变 CURSED)
    if score < 4.0 and random.random() < 0.15:
        return "CURSED", "💀", "CURSED (诅咒)", 0
    return "N", "⚪", "N (Normal)", 0


def get_rarity_comment(rarity: str, score: float) -> str:
    """根据稀有度获取看板娘点评"""
    comments = {
        "UR": "⚡ <b>金光一闪！这是传世神作啊 Master！</b>",
        "SSR": "哇！这张卡牌散发着迷人的光芒！",
        "SR": "看起来是一部值得回味的良作呢。",
        "R": "普普通通的日常收藏~",
        "N": "emmm...下次会更好的喵！",
        "CURSED": "呃... 这股不详的气息... 是烂片之王吗？"
    }
    return comments.get(rarity, "普普通通...")


# ==========================================
# 🎰 命运盲盒系统
# ==========================================

async def blind_box_gacha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    命运盲盒 - 统一抽取系统
    """
    logger.info("[gacha] 命令被调用")
    query = getattr(update, "callback_query", None)
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    logger.info(f"[gacha] 用户ID: {user_id}")

    # 回调模式：显示加载状态
    if query:
        try:
            await query.edit_message_text("🔮 <b>命运之轮正在转动...</b>\n<i>(正在从星海中抽取您的专属卡牌)</i>", parse_mode='HTML')
        except Exception:
            pass
    else:
        # 命令模式：发送加载消息
        loading_msg = await msg.reply_html("🎰 <b>命运之轮正在转动...</b>\n<i>(正在从星海中抽取您的专属卡牌)</i>")
    logger.info("[gacha] loading_msg 已发送")

    with get_session() as session:
        logger.info("[gacha] 数据库 session 已获取")
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        logger.info(f"[gacha] 用户查询完成: {user}")

        # 检查是否已绑定
        if not user or not user.emby_account:
            error_text = "💔 <b>请先绑定账号喵！</b>\n使用 <code>/bind 账号</code> 绑定后再来~"
            if query:
                await query.edit_message_text(error_text, parse_mode='HTML')
            else:
                await loading_msg.edit_text(error_text)
            return

        # 检查是否有免费次数（每日一次）
        now = datetime.now()
        today = now.date()
        last_tarot_date = user.last_tarot.date() if user.last_tarot else None

        has_free = last_tarot_date is None or last_tarot_date < today
        has_extra = user.extra_gacha and user.extra_gacha > 0

        # 计算消耗
        if has_free:
            cost = 0
            cost_type = "每日免费"
        elif has_extra:
            cost = 0
            cost_type = "盲盒券"
        else:
            cost = 25 if user.is_vip else 50
            cost_type = "魔力"

        # 检查余额
        if cost > 0 and user.points < cost:
            error_text = (
                f"💸 <b>魔力不足喵！</b>\n\n"
                f"抽取需要 <b>{cost} MP</b>\n"
                f"您当前余额：<b>{user.points} MP</b>\n\n"
                f"<i>\"快去签到攒钱吧喵！(ง •_•)ง\"</i>"
            )
            if query:
                await query.edit_message_text(error_text, parse_mode='HTML')
            else:
                await loading_msg.edit_text(error_text)
            return

        logger.info("[gacha] 开始获取电影")
        # 从 Emby 获取随机电影（异步版本）
        movie = await fetch_random_movie()
        if not movie:
            error_text = "💨 <b>虚空中什么也没有...</b>\n\n<i>(Emby 连接失败或媒体库为空)</i>"
            if query:
                await query.edit_message_text(error_text, parse_mode='HTML')
            else:
                await loading_msg.edit_text(error_text)
            return

        logger.info(f"[gacha] 获取到电影: {movie.get('Name')}")

        # 计算稀有度
        rarity_code, rarity_emoji, rarity_name, bonus = calculate_rarity(movie)

        # 构建物品名称（存入背包）
        title = movie.get('Name', '未知电影')
        year = movie.get('ProductionYear', '????')
        item_name = f"{rarity_emoji} {title} ({rarity_code})"

        # 扣费
        if has_free:
            user.last_tarot = now
        elif has_extra:
            user.extra_gacha -= 1
        else:
            user.points -= cost

        # 返利
        if bonus > 0:
            user.points += bonus

        # 存入背包
        current_items = user.items or ""
        if current_items:
            user.items = current_items + "," + item_name
        else:
            user.items = item_name

        # 更新每日计数
        user.daily_tarot_count = (user.daily_tarot_count or 0) + 1

        # 保存需要用于显示的值
        points = user.points
        user_id = user.tg_id
        session.commit()
        logger.info("[gacha] 数据库提交完成")

    # 追踪任务进度（在 with 块外）
    await track_activity_wrapper(user_id, "poster")

    # 构建卡片消息（在 with 块外）
    score = movie.get('CommunityRating') or 0
    genres = movie.get('Genres', [])
    genre_text = " / ".join(genres)[:30] if genres else "未知"

    # 看板娘点评
    comment = get_rarity_comment(rarity_code, score)

    # 海报 URL
    item_id = movie.get('Id')
    poster_url = f"{EMBY_URL}/Items/{item_id}/Images/Primary?maxHeight=900&maxWidth=600&quality=90"

    # 构建标题
    caption = (
        f"🎰 <b>【 命 运 盲 盒 · 开 启 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎬 <b>{title}</b> ({year})\n\n"
        f"🏅 <b>稀有度：</b> {rarity_emoji} <b>{rarity_name}</b>\n"
        f"⭐ <b>评分：</b> <code>{score}</code>\n"
        f"🏷️ <b>标签：</b> {genre_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>消耗：</b> {cost if cost > 0 else '免费'} {cost_type}\n"
        f"💼 <b>余额：</b> {points} MP\n"
    )

    # 返利提示
    if bonus > 0:
        caption += f"🎁 <b>返利：</b> +{bonus} MP\n"

    caption += (
        f"📦 <i>物品已存入背包！使用 /bag 查看</i>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💬 <b>看板娘点评：</b>\n"
        f"{comment}"
    )

    # 按钮
    buttons = [
        [InlineKeyboardButton("🔄 再抽一次 (25/50 MP)", callback_data="gacha_retry"),
         InlineKeyboardButton("🎒 查看背包", callback_data="view_bag")]
    ]

    logger.info("[gacha] 发送结果消息")

    # 回调模式：编辑原消息；命令模式：删除加载消息并发新消息
    if query:
        await query.edit_message_text(caption, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
    else:
        await loading_msg.delete()
        await msg.reply_html(caption, reply_markup=InlineKeyboardMarkup(buttons))

    # 异步发送图片（仅命令模式）
    if not query:
        try:
            import asyncio
            await asyncio.wait_for(
                msg.reply_photo(
                    photo=poster_url,
                    caption=f"🎬 {title} ({year}) - {rarity_emoji} {rarity_name}",
                    parse_mode='HTML'
                ),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            logger.warning(f"图片发送超时: {poster_url}")
        except Exception as e:
            logger.error(f"图片发送失败: {e}")


async def gacha_retry_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """再抽一次按钮回调"""
    query = update.callback_query
    await query.answer("🔄 命运转动中...")

    # 创建一个伪造的 update 对象，包含 callback_query 以支持编辑模式
    fake_update = type('Update', (), {
        'effective_message': query.message,
        'effective_user': query.from_user,
        'message': query.message,
        'callback_query': query,
    })()

    await blind_box_gacha(fake_update, context)


async def view_bag_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看背包按钮回调"""
    query = update.callback_query
    await query.answer()

    # 导入 bag 模块的显示函数
    from plugins.bag import bag_main
    fake_update = type('Update', (), {
        'effective_message': query.message,
        'effective_user': query.from_user,
    })()
    await bag_main(fake_update, context)


# ==========================================
# ⚔️ 玩法二：魔法少女决斗 (PVP 互动)
# ==========================================
# 决斗数据存储结构: context.bot_data["duels"] = { duel_id: { ... } }
# 决斗统计结构: context.bot_data["duel_stats"] = { user_id: {"wins": int, "losses": int} }

def get_duel_data(context: ContextTypes.DEFAULT_TYPE, duel_id: str):
    """安全获取决斗数据"""
    if not context.bot_data:
        logger.error("bot_data 未初始化")
        return None
    if "duels" not in context.bot_data:
        context.bot_data["duels"] = {}
    return context.bot_data["duels"].get(duel_id)

def save_duel_data(context: ContextTypes.DEFAULT_TYPE, duel_id: str, data: dict):
    """安全保存决斗数据"""
    if not context.bot_data:
        context.bot_data = {}
    if "duels" not in context.bot_data:
        context.bot_data["duels"] = {}
    context.bot_data["duels"][duel_id] = data

def delete_duel_data(context: ContextTypes.DEFAULT_TYPE, duel_id: str):
    """安全删除决斗数据"""
    if context.bot_data and "duels" in context.bot_data:
        context.bot_data["duels"].pop(duel_id, None)

def update_duel_stats(context: ContextTypes.DEFAULT_TYPE, user_id: int, won: bool):
    """更新决斗统计"""
    if not context.bot_data:
        return
    if "duel_stats" not in context.bot_data:
        context.bot_data["duel_stats"] = {}
    if user_id not in context.bot_data["duel_stats"]:
        context.bot_data["duel_stats"][user_id] = {"wins": 0, "losses": 0}
    if won:
        context.bot_data["duel_stats"][user_id]["wins"] += 1
    else:
        context.bot_data["duel_stats"][user_id]["losses"] += 1

def get_duel_stats(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> dict:
    """获取决斗统计"""
    if not context.bot_data or "duel_stats" not in context.bot_data:
        return {"wins": 0, "losses": 0}
    return context.bot_data["duel_stats"].get(user_id, {"wins": 0, "losses": 0})

async def duel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发起魔法少女决斗"""
    logger.info(f"[/duel] ===== 命令被调用 =====")
    logger.info(f"[/duel] 用户: {update.effective_user.id if update.effective_user else 'Unknown'}")
    logger.info(f"[/duel] context.args: {context.args}")
    logger.info(f"[/duel] 有效消息: {update.effective_message}")
    logger.info(f"[/duel] 回复消息: {update.effective_message.reply_to_message if update.effective_message else 'N/A'}")
    msg = update.effective_message
    if not msg:
        logger.warning("[/duel] effective_message 为空")
        return

    challenger = update.effective_user
    logger.info(f"[/duel] challenger: {challenger.id}, has reply_to_message: {msg.reply_to_message is not None}")

    # 尝试获取对手：优先使用回复消息，其次解析 @username
    opponent = None
    target_msg = msg.reply_to_message
    bet = 50  # 默认赌注

    # 方式1: 通过回复消息获取对手
    if target_msg and target_msg.from_user:
        opponent = target_msg.from_user
        logger.info(f"[/duel] 从回复消息获取对手: {opponent.id if opponent else 'None'}")
        # 解析金额
        if context.args and len(context.args) > 0:
            try:
                bet = int(context.args[0])
            except ValueError:
                await msg.reply_html("⚠️ <b>格式错误</b>\n\n金额必须是数字")
                return

    # 方式2: 通过 @username 获取对手
    elif context.args and len(context.args) >= 2:
        # 格式: /duel @username 金额 或 /duel 金额 @username
        username_or_bet = context.args[0]
        logger.info(f"[/duel] 尝试解析参数: {username_or_bet}")

        # 检查群组成员找到匹配的用户
        if hasattr(update, 'effective_chat'):
            chat = update.effective_chat
            # 尝试从参数中提取 @username
            for arg in context.args:
                if arg.startswith('@'):
                    username = arg[1:]  # 去掉 @
                    # 从缓存中查找用户（需要管理员权限才能获取完整成员列表）
                    # 这里我们只能等待被挑战者主动触发
                    await msg.reply_html(
                        "⚔️ <b>决斗发起方式</b>\n\n"
                        f"由于 iOS 客户端限制，请使用以下方式：\n"
                        f"1. 回复对方消息后输入 <code>/duel 金额</code>\n"
                        f"2. 或让对方向你发起决斗\n\n"
                        f"<i>\"这是 Telegram 的限制喵！\"</i>"
                    )
                    return
                else:
                    try:
                        bet = int(arg)
                    except ValueError:
                        pass

    if not opponent:
        # 使用普通回复，不自删除（让用户看到使用说明）
        await msg.reply_html(
            "⚔️ <b>发起决斗</b>\n\n"
            f"<b>方式1（推荐）：</b>回复对方消息，输入 <code>/duel 金额</code>\n"
            f"<b>方式2：</b>让对方向你发起决斗\n\n"
            f"<i>\"iOS 用户请使用方式1，确保命令在消息开头喵！\"</i>"
        )
        return

    logger.info(f"[/duel] opponent: {opponent.id if opponent else 'None'}, is_bot: {opponent.is_bot if opponent else 'N/A'}")

    # 检查是否在挑战自己
    if opponent.id == challenger.id:
        logger.info(f"[/duel] 挑战自己，返回提示")
        await msg.reply_html("🤔 <b>不能和自己打架哦喵！</b>\n\n<i>\"再怎么想赢也不能这样啦！\"</i>")
        return

    # 检查是否在挑战机器人
    if opponent.is_bot:
        logger.info(f"[/duel] 挑战机器人，返回提示")
        await msg.reply_html("🤖 <b>看板娘是裁判，不能下场比赛的喵！</b>\n\n<i>\"找真人决斗吧！\"</i>")
        return

    # 解析金额
    logger.info(f"[/duel] 开始解析金额, args: {context.args}")
    try:
        bet = int(context.args[0]) if context.args else 50
        logger.info(f"[/duel] 金额解析成功: {bet}")
        if bet < 10:
            await msg.reply_html("⚠️ <b>赌注太小啦喵！</b>\n\n起步价 <b>10 MP</b>。")
            return
        if bet > 10000:
            await msg.reply_html("⚠️ <b>赌注太大啦喵！</b>\n\n单次决斗上限 <b>10000 MP</b>。")
            return
    except (IndexError, ValueError) as e:
        logger.info(f"[/duel] 金额解析失败: {e}")
        await msg.reply_html(
            "⚠️ <b>格式错误</b>\n\n"
            f"请使用：<code>/duel 金额</code>\n"
            f"例如：<code>/duel 100</code>"
        )
        return

    logger.info(f"[/duel] 开始查询数据库")
    with get_session() as session:
        # 检查发起者是否绑定
        u_challenger = session.query(UserBinding).filter_by(tg_id=challenger.id).first()
        if not u_challenger or not u_challenger.emby_account:
            await msg.reply_html("💔 <b>您还未绑定账号喵！</b>\n\n使用 <code>/bind 账号</code> 绑定后再来决斗。")
            return

        # 检查发起者余额
        if u_challenger.points < bet:
            cha_points = u_challenger.points
            await msg.reply_html(
                f"💸 <b>魔力不足喵！</b>\n\n"
                f"只有 {cha_points} MP，无法发起 {bet} MP 的决斗！"
            )
            return

        # 检查应战者是否绑定
        u_opponent = session.query(UserBinding).filter_by(tg_id=opponent.id).first()
        if not u_opponent or not u_opponent.emby_account:
            await msg.reply_html("💔 <b>对方还未绑定账号喵！</b>\n\n<i>\"不能欺负没绑定的路人哦！\"</i>")
            return

        # 获取双方战力用于显示
        cha_atk = u_challenger.attack if u_challenger.attack is not None else 10
        opp_atk = u_opponent.attack if u_opponent.attack is not None else 10
        cha_wep = u_challenger.weapon or "赤手空拳"
        opp_wep = u_opponent.weapon or "赤手空拳"
        cha_is_vip = u_challenger.is_vip
        opp_is_vip = u_opponent.is_vip

    # 生成唯一决斗ID
    duel_id = str(uuid.uuid4())[:8]

    # 存储决斗数据
    duel_data = {
        "challenger_id": challenger.id,
        "challenger_name": challenger.first_name or "挑战者",
        "challenger_attack": cha_atk,
        "challenger_weapon": cha_wep,
        "challenger_is_vip": cha_is_vip,
        "opponent_id": opponent.id,
        "opponent_name": opponent.first_name or "应战者",
        "opponent_attack": opp_atk,
        "opponent_weapon": opp_wep,
        "opponent_is_vip": opp_is_vip,
        "bet": bet,
        "chat_id": update.effective_chat.id,
        "message_id": None,
        "created_at": datetime.now()
    }

    # 保存决斗数据
    save_duel_data(context, duel_id, duel_data)
    logger.info(f"决斗发起: duel_id={duel_id}, challenger={challenger.id}, opponent={opponent.id}")

    # 构造按钮
    keyboard = [
        [
            InlineKeyboardButton("🔥 接受挑战", callback_data=f"duel_accept_{duel_id}"),
            InlineKeyboardButton("🏳️ 认怂", callback_data=f"duel_reject_{duel_id}")
        ],
        [InlineKeyboardButton("❌ 取消(仅发起者)", callback_data=f"duel_cancel_{duel_id}")]
    ]

    # 战力对比指示
    if cha_atk > opp_atk * 1.5:
        adv_emoji = "🔥"
        adv_text = "挑战者压倒性优势"
    elif cha_atk > opp_atk:
        adv_emoji = "⚔️"
        adv_text = "挑战者略占上风"
    elif opp_atk > cha_atk * 1.5:
        adv_emoji = "🛡️"
        adv_text = "应战者压倒性优势"
    elif opp_atk > cha_atk:
        adv_emoji = "🛡️"
        adv_text = "应战者略占上风"
    else:
        adv_emoji = "⚖️"
        adv_text = "势均力敌"

    # VIP 标记
    cha_vip_badge = "👑 " if cha_is_vip else ""
    opp_vip_badge = "👑 " if opp_is_vip else ""

    # 决斗邀请消息不自毁（需要对方点击按钮）
    sent_msg = await msg.reply_html(
        f"⚔️ <b>【 魔 法 少 女 · 决 斗 展 开 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔴 <b>挑战者：</b> {cha_vip_badge}{challenger.first_name or '神秘人'}\n"
        f"    ⚡ 战力: <code>{cha_atk}</code> | 🗡️ {cha_wep}\n"
        f"\n"
        f"🔵 <b>应战者：</b> {opp_vip_badge}{opponent.first_name or '神秘人'}\n"
        f"    ⚡ 战力: <code>{opp_atk}</code> | 🗡️ {opp_wep}\n"
        f"\n"
        f"💰 <b>赌注金额：</b> <code>{bet}</code> MP\n"
        f"{adv_emoji} <i>{adv_text}</i>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"气氛焦灼起来了！应战者请在 60秒 内做出选择喵！\"</i>",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # 保存消息ID用于后续更新
    duel_data["message_id"] = sent_msg.message_id
    save_duel_data(context, duel_id, duel_data)


async def duel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理决斗按钮回调"""
    query = update.callback_query
    if not query:
        return

    logger.info(f"决斗回调触发: data={query.data}, from={query.from_user.id}")

    # 先 answer 防止按钮转圈
    try:
        await query.answer()
    except Exception:
        pass

    # 解析: duel_action_xxxxx 或 duel_reject_xxxxx
    parts = query.data.split('_')
    # parts[0]="duel", parts[1]="accept/reject/cancel", parts[2]=duel_id
    if len(parts) < 3:
        await query.edit_message_text("⚠️ <b>决斗数据错误喵！</b>", parse_mode='HTML')
        return

    action = parts[1]  # "accept", "reject", 或 "cancel"
    duel_id = parts[2]  # 决斗ID

    # 安全获取决斗数据
    duel_data = get_duel_data(context, duel_id)
    if not duel_data:
        await query.edit_message_text("⏰ <b>这场决斗已经过期啦喵！</b>\n\n<i>\"可能被取消了，或者服务器重启了喵~\"</i>", parse_mode='HTML')
        return

    user = query.from_user

    # 检查决斗是否过期 (60秒)
    if (datetime.now() - duel_data["created_at"]).total_seconds() > 60:
        await query.edit_message_text("⏰ <b>决斗已超时喵！</b>\n\n<i>\"犹豫就会败北...\"</i>", parse_mode='HTML')
        delete_duel_data(context, duel_id)
        return

    # 处理取消（仅发起者可操作）
    if action == "cancel":
        if user.id != duel_data["challenger_id"]:
            await query.answer("只有发起者才能取消决斗喵！", show_alert=True)
            return
        await query.edit_message_text(
            "❌ <b>决斗已取消</b>\n\n<i>\"发起者主动取消了这场决斗...\"</i>",
            parse_mode='HTML'
        )
        delete_duel_data(context, duel_id)
        return

    # 只有应战者能操作接受/拒绝
    if user.id != duel_data["opponent_id"]:
        await query.answer("这不是你的决斗喵！吃瓜群众请后退！", show_alert=True)
        return

    if action == "reject":
        # 认怂，挑战者获得少量安慰奖
        consolation = max(5, duel_data["bet"] // 10)  # 10% 安慰奖
        try:
            with get_session() as session:
                u_cha = session.query(UserBinding).filter_by(tg_id=duel_data["challenger_id"]).first()
                if u_cha:
                    u_cha.points += consolation
                    session.commit()

            await query.edit_message_text(
                f"🏳️ <b>决斗取消</b>\n\n"
                f"{user.first_name or '应战者'} 选择了认怂...\n"
                f"💰 <b>{duel_data['challenger_name']}</b> 获得 <code>{consolation}</code> MP 安慰奖\n"
                f"<i>\"没有人受伤，就是有点没面子喵...\"</i>",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"决斗认怂处理失败: {e}", exc_info=True)
            await query.edit_message_text(
                f"🏳️ <b>决斗取消</b>\n\n"
                f"{user.first_name or '应战者'} 选择了认怂...\n"
                f"<i>\"没有人受伤，就是有点没面子喵...\"</i>",
                parse_mode='HTML'
            )
        finally:
            delete_duel_data(context, duel_id)
        return

    if action == "accept":
        await process_duel_battle(query, context, duel_data, duel_id, user)


async def process_duel_battle(query, context: ContextTypes.DEFAULT_TYPE, duel_data: dict, duel_id: str, user):
    """处理决斗战斗逻辑"""
    try:
        with get_session() as session:
            # 重新查询双方数据
            u_opp = session.query(UserBinding).filter_by(tg_id=user.id).first()
            u_cha = session.query(UserBinding).filter_by(tg_id=duel_data["challenger_id"]).first()

            bet = duel_data["bet"]

            # 再次检查余额
            if not u_opp or u_opp.points < bet:
                await query.edit_message_text(
                    f"💸 <b>决斗取消</b>\n\n"
                    f"{user.first_name or '应战者'} 的钱不够付赌注喵！\n"
                    f"<i>\"好尴尬啊...\"</i>",
                    parse_mode='HTML'
                )
                delete_duel_data(context, duel_id)
                return

            if not u_cha or u_cha.points < bet:
                await query.edit_message_text(
                    f"💸 <b>决斗取消</b>\n\n"
                    f"{duel_data['challenger_name']} 的钱已经花光了喵！\n"
                    f"<i>\"发起者破产了，决斗无效！\"</i>",
                    parse_mode='HTML'
                )
                delete_duel_data(context, duel_id)
                return

            # 获取战斗属性（优先使用缓存的值，避免重新查询数据库）
            cha_attack = duel_data.get("challenger_attack", u_cha.attack or 10)
            opp_attack = duel_data.get("opponent_attack", u_opp.attack or 10)
            cha_weapon = duel_data.get("challenger_weapon", u_cha.weapon or "赤手空拳")
            opp_weapon = duel_data.get("opponent_weapon", u_opp.weapon or "赤手空拳")
            cha_is_vip = duel_data.get("challenger_is_vip", u_cha.is_vip)
            opp_is_vip = duel_data.get("opponent_is_vip", u_opp.is_vip)

            # ===== 决斗战斗计算 =====
            # 计算基础胜率（基于战力差距）
            attack_diff = cha_attack - opp_attack
            attack_bonus = max(-0.25, min(0.25, attack_diff / 3000))

            # VIP 加成
            vip_bonus = 0.0
            if cha_is_vip:
                vip_bonus += 0.05  # 挑战者VIP +5%
            if opp_is_vip:
                vip_bonus -= 0.03  # 应战者VIP -3%

            # 武器加成（稀有度额外加成）
            cha_weapon_bonus = get_weapon_rarity_bonus(cha_weapon)
            opp_weapon_bonus = get_weapon_rarity_bonus(opp_weapon)

            # 最终胜率计算
            win_chance = 0.5 + attack_bonus + vip_bonus + (cha_weapon_bonus - opp_weapon_bonus) / 100
            win_chance = max(0.15, min(0.85, win_chance))  # 限制在15%-85%之间

            winner_is_challenger = random.random() < win_chance

            # 生成战斗过程文本
            battle_text = generate_battle_text(
                duel_data["challenger_name"], cha_attack, cha_weapon,
                duel_data["opponent_name"], opp_attack, opp_weapon,
                winner_is_challenger, win_chance
            )

            if winner_is_challenger:
                winner, loser = u_cha, u_opp
                win_name = duel_data["challenger_name"]
                lose_name = duel_data["opponent_name"]
                win_id = duel_data["challenger_id"]
                lose_id = duel_data["opponent_id"]
            else:
                winner, loser = u_opp, u_cha
                win_name = duel_data["opponent_name"]
                lose_name = duel_data["challenger_name"]
                win_id = duel_data["opponent_id"]
                lose_id = duel_data["challenger_id"]

            # === 连胜系统 ===
            winner_streak = (winner.win_streak or 0) + 1
            winner.win_streak = winner_streak
            winner.last_win_streak_date = datetime.now()

            # 败者重置连胜
            loser.win_streak = 0
            loser.lose_streak = (loser.lose_streak or 0) + 1

            # 资金转移
            winner.points += bet
            winner.win += 1
            winner.lose_streak = 0  # 重置连败

            # 更新每日决斗计数
            now = datetime.now()
            today = now.date()

            # 检查胜者的计数器是否需要重置
            if winner.last_duel_date:
                last_date = winner.last_duel_date.date() if isinstance(winner.last_duel_date, datetime) else winner.last_duel_date
                if last_date < today:
                    winner.daily_duel_count = 1
                else:
                    winner.daily_duel_count = (winner.daily_duel_count or 0) + 1
            else:
                winner.daily_duel_count = 1
            winner.last_duel_date = now

            # 检查败者的计数器是否需要重置
            if loser.last_duel_date:
                last_date = loser.last_duel_date.date() if isinstance(loser.last_duel_date, datetime) else loser.last_duel_date
                if last_date < today:
                    loser.daily_duel_count = 1
                else:
                    loser.daily_duel_count = (loser.daily_duel_count or 0) + 1
            else:
                loser.daily_duel_count = 1
            loser.last_duel_date = now

            # 财富追踪：胜者获得赌注
            winner.total_earned = (winner.total_earned or 0) + bet

            # 连败安慰机制
            lose_streak = loser.lose_streak
            loser.lost += 1

            # 败者安慰奖（赌注的10%，上限20）
            consolation = min(bet // 10, 20)
            consolation_extra = 30 if lose_streak >= 3 else 0  # 连败3次以上额外安慰
            total_consolation = consolation + consolation_extra

            # 败者财富追踪
            loser.total_earned = (loser.total_earned or 0) + total_consolation

            # 检查防御卷轴效果（失败不掉钱）
            shield_protected = False
            if loser.shield_active:
                shield_protected = True
                loser.shield_active = False  # 消耗防御卷轴
                # 防御卷轴：不扣赌注，但获得安慰奖
                loser.points += total_consolation
            else:
                # 无防御卷轴：扣除赌注，但返还安慰奖
                loser.points -= bet
                loser.points += total_consolation
                # 财富追踪：败者失去赌注（净消费）
                loser.total_spent = (loser.total_spent or 0) + bet

            # 胜者可能获得战力提升（小概率）
            power_up = 0
            if random.random() < 0.15:  # 15%概率
                power_up = random.randint(1, 3)
                winner.attack = (winner.attack or 0) + power_up

            # 连胜额外奖励
            streak_bonus = 0
            if winner_streak >= 5:
                streak_bonus = winner_streak * 5  # 每连胜场数×5 MP
                winner.points += streak_bonus
                winner.total_earned = (winner.total_earned or 0) + streak_bonus

            session.commit()

            # 更新内存中的决斗统计
            update_duel_stats(context, win_id, True)
            update_duel_stats(context, lose_id, False)

            # 检查成就（决斗相关）
            from plugins.achievement import check_and_award_achievement
            achievement_msgs = []
            for ach_id in ["duel_1", "duel_10", "duel_50", "duel_100", "win_streak_5", "win_streak_10",
                           "power_100", "power_500", "power_1000", "power_5000", "power_10000"]:
                result = check_and_award_achievement(winner, ach_id, session)
                if result["new"]:
                    achievement_msgs.append(f"🎉 {result['emoji']} {result['name']} (+{result['reward']}MP)")

            if achievement_msgs:
                session.commit()

            # 追踪每日任务进度（决斗）
            await track_activity_wrapper(win_id, "duel")
            await track_activity_wrapper(lose_id, "duel")

            # 保存需要在session关闭后使用的值
            power_up_text_value = f"\n⬆️ <b>{win_name}</b> 战力 +{power_up}！战斗经验提升了喵！" if power_up else ""

            # 败者安慰奖文本
            if total_consolation > 0:
                if consolation_extra > 0:
                    consolation_text = f"💝 <b>败者安慰：</b> {lose_name} 获得 {total_consolation} MP (连败{lose_streak}次额外+30)"
                else:
                    consolation_text = f"💝 <b>败者安慰：</b> {lose_name} 获得 {total_consolation} MP"
            else:
                consolation_text = ""

            # 防御卷轴效果文本
            if shield_protected:
                lose_text = f"🛡️ <b>败者：</b> {lose_name} 的防御卷轴生效了！没有损失 MP！"
                if total_consolation > 0:
                    lose_text += f"\n{consolation_text}"
            else:
                lose_text = f"💀 <b>败者：</b> {lose_name} 失去 {bet} MP"
                if total_consolation > 0:
                    lose_text += f"\n{consolation_text}"

            streak_bonus_text = f"\n🎁 <b>连胜奖励：</b> +{streak_bonus} MP！" if streak_bonus > 0 else ""

        # === 正面反馈增强：连胜暴击检测 ===
        lucky_result = check_lucky_with_streak(winner_streak, winner.is_vip)
        crit_effect = ""
        crit_bonus = 0

        if lucky_result["triggered"]:
            crit_multiplier = lucky_result["multiplier"]
            crit_effect = lucky_result["effect"]
            crit_bonus = bet * (crit_multiplier - 1)
            # 额外奖励（需要在新的 session 中添加）
            with get_session() as bonus_session:
                bonus_winner = bonus_session.query(UserBinding).filter_by(tg_id=win_id).first()
                if bonus_winner:
                    bonus_winner.points += crit_bonus
                    bonus_winner.total_earned = (bonus_winner.total_earned or 0) + crit_bonus
                    bonus_session.commit()

        # 在with块外发送消息（增强版）
        # 构建增强的决斗结束消息
        title_effect = success_burst(2) if lucky_result["triggered"] else ""
        duel_end_title = f"⚔️💥 【 决 斗 结 束 】💥⚔️" if lucky_result["triggered"] else "⚔️ <b>【 决 斗 结 束 】</b>"

        message_lines = [
            duel_end_title,
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🌟 战斗过程 🌟",
            battle_text,
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🏆 <b>胜者：</b> {win_name}",
            f"🔥 <b>连胜：</b> {winner_streak} 场！",
            f"💰 <b>收益：</b> +{bet} MP{power_up_text_value}",
        ]

        # 添加暴击效果
        if crit_effect:
            message_lines.append(f"\n{title_effect}")
            message_lines.append(f"{crit_effect}")
            message_lines.append(f"💰💰💰 额外 +{crit_bonus} MP 💰💰💰")
            message_lines.append(f"💰 总计收益：+{bet + crit_bonus} MP")
        elif streak_bonus > 0:
            message_lines.append(streak_bonus_text)

        message_lines.append(f"\n{lose_text}")

        if achievement_msgs:
            message_lines.append(f"\n🏆 " + "\n".join(achievement_msgs[:2]))

        message_lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            get_duel_victory_quote(win_name) if lucky_result["triggered"] else f"<i>\"多么精彩的战斗！看板娘看得热血沸腾喵！{random_cute_emoji()}\"</i>"
        ])

        await query.edit_message_text(
            "\n".join(message_lines),
            parse_mode='HTML'
        )
        delete_duel_data(context, duel_id)
        logger.info(f"决斗结束: duel_id={duel_id}, winner={win_name}, streak={winner_streak}, crit={crit_effect}")

    except Exception as e:
        logger.error(f"决斗处理失败: {e}", exc_info=True)
        try:
            await query.edit_message_text(
                f"⚠️ <b>决斗出错</b>\n\n<i>\"魔法阵不稳定...决斗已取消，请稍后再试喵！\"</i>",
                parse_mode='HTML'
            )
        except Exception:
            pass
        delete_duel_data(context, duel_id)


async def duel_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看决斗统计"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    stats = get_duel_stats(context, user_id)
    wins = stats["wins"]
    losses = stats["losses"]
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0

    # 从数据库获取更详细的数据
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if user:
            db_wins = user.win or 0
            db_losses = user.lost or 0
            db_streak = user.win_streak or 0
            attack = user.attack or 0
            weapon = user.weapon or "赤手空拳"
        else:
            db_wins = db_losses = db_streak = attack = 0
            weapon = "赤手空拳"

    txt = (
        f"📊 <b>【 决 斗 统 计 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>魔法少女：</b> {update.effective_user.first_name or '神秘人'}\n"
        f"⚔️ <b>装备武器：</b> {weapon}\n"
        f"⚡ <b>当前战力：</b> {attack}\n"
        f"\n"
        f"🏆 <b>胜场：</b> {db_wins}\n"
        f"💀 <b>败场：</b> {db_losses}\n"
        f"🔥 <b>当前连胜：</b> {db_streak}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"继续努力，成为最强的魔导士喵！(｡•̀ᴗ-)✧\"</i>"
    )
    await reply_with_auto_delete(msg, txt)


def get_weapon_rarity_bonus(weapon: str) -> int:
    """根据武器稀有度返回战力加成"""
    if not weapon:
        return 0
    weapon_upper = weapon.upper()
    if "SSR" in weapon_upper or "神器" in weapon_upper:
        return 15
    elif "SR" in weapon_upper or "史诗" in weapon_upper:
        return 10
    elif "R" in weapon_upper or "稀有" in weapon_upper or "普通" in weapon_upper:
        return 5
    elif "咸鱼" in weapon_upper:
        return -5  # 咸鱼武器扣分哈哈
    return 0


def generate_battle_text(cha_name: str, cha_atk: int, cha_wep: str,
                         opp_name: str, opp_atk: int, opp_wep: str,
                         cha_wins: bool, win_chance: float) -> str:
    """生成决斗过程的描述文本"""
    # 武器显示
    cha_weapon = cha_wep if cha_wep else "赤手空拳"
    opp_weapon = opp_wep if opp_wep else "赤手空拳"

    # 战力对比文本
    if cha_atk > opp_atk * 1.5:
        adv_text = f"{cha_name} 压倒性优势！"
    elif cha_atk > opp_atk * 1.2:
        adv_text = f"{cha_name} 略占上风"
    elif opp_atk > cha_atk * 1.5:
        adv_text = f"{opp_name} 压倒性优势！"
    elif opp_atk > cha_atk * 1.2:
        adv_text = f"{opp_name} 略占上风"
    else:
        adv_text = "势均力敌！"

    # 战斗动作描述
    actions = [
        f"🌟 {cha_name} 以 {cha_atk} 战力，挥舞【{cha_weapon}】发起进攻！",
        f"⚡ {opp_name} 以 {opp_atk} 战力，装备【{opp_weapon}】迎击！",
    ]

    # 随机添加额外描述
    extra_moves = [
        "✨ 魔法阵光芒四射！",
        "💫 空间开始扭曲...",
        "🔥 炽热的魔力碰撞！",
        "❄️ 冰冷的杀气弥漫！",
        "🌈 彩虹般的能量爆发！",
    ]
    if len(extra_moves) > 0:
        actions.append(f"    {random.choice(extra_moves)}")

    if cha_wins:
        actions.append(f"🎯 <b>{cha_name}</b> 的攻击突破了防御！")
    else:
        actions.append(f"🎯 <b>{opp_name}</b> 的反击致命一击！")

    return "\n".join(actions) + f"\n\n📊 <i>({adv_text})</i>\n"


# ==========================================
# 🔌 注册模块
# ==========================================
def register(app):
    # 盲盒命令（poster 和 fate 均指向同一个函数）
    app.add_handler(CommandHandler("poster", blind_box_gacha))
    app.add_handler(CommandHandler("fate", blind_box_gacha))
    # 决斗命令
    app.add_handler(CommandHandler("duel", duel_start))
    app.add_handler(CommandHandler("duelstats", duel_stats))
    # 决斗回调：duel_accept_xxx, duel_reject_xxx, duel_cancel_xxx，xxx为8位字符
    app.add_handler(CallbackQueryHandler(duel_callback, pattern=r"^duel_(accept|reject|cancel)_\w{8}$"))
    # 盲盒回调
    app.add_handler(CallbackQueryHandler(gacha_retry_callback, pattern="^gacha_retry$"))
    app.add_handler(CallbackQueryHandler(view_bag_callback, pattern="^view_bag$"))
