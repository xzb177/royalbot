from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding
from utils import reply_with_auto_delete
from types import SimpleNamespace
import aiohttp
import re
import random
import os
import logging

logger = logging.getLogger(__name__)


# Emby 配置
EMBY_URL = os.getenv("EMBY_URL", "")
EMBY_API_KEY = os.getenv("EMBY_API_KEY", "")


class CallbackMessageEditor:
    """回调消息编辑器 - 统一处理所有按钮回调的响应"""

    def __init__(self, query, context):
        self.query = query
        self.context = context
        self.original_message = None
        self._captured = False

    async def edit(self, text, buttons=None, parse_mode='HTML'):
        """编辑原消息"""
        keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="back_menu")]] if buttons is None else buttons
        try:
            await self.query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=parse_mode)
            return True
        except Exception as e:
            logger.warning(f"编辑消息失败: {e}")
            return False

    async def send(self, text, buttons=None, parse_mode='HTML'):
        """发送新消息（仅当编辑失败时使用）"""
        keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="back_menu")]] if buttons is None else buttons
        try:
            await self.query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=parse_mode)
        except:
            pass


async def handle_plugin_callback(query, plugin_func, context, **kwargs):
    """
    统一处理插件回调 - 编辑原消息而不是发送新消息

    用法: await handle_plugin_callback(query, module.function, context)
    """
    # 临时保存原始消息发送方法
    original_reply = None
    original_reply_html = None
    captured_messages = []

    async def capture_reply(msg, text, **kwargs):
        """捕获回复消息"""
        captured_messages.append(('text', text, kwargs))
        # 不实际发送，稍后统一编辑

    async def capture_reply_html(msg, text, **kwargs):
        """捕获 HTML 回复消息"""
        captured_messages.append(('html', text, kwargs))

    # 创建 fake_update
    fake_update = make_fake_update(query, **kwargs)

    # 尝试调用插件函数，并拦截消息
    try:
        result = await plugin_func(fake_update, context)
    except Exception as e:
        logger.error(f"插件函数执行失败: {e}")
        await query.edit_message_text(f"⚠️ 操作失败: {str(e)}")
        return

    # 如果有捕获的消息，编辑原消息
    if captured_messages:
        for msg_type, text, kw in captured_messages:
            keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="back_menu")]]
            try:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
                break  # 只显示第一条消息
            except:
                continue


async def edit_callback_message(query, text, buttons=None, parse_mode='HTML'):
    """统一处理回调消息编辑，避免刷屏"""
    keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="back_menu")]] if buttons is None else buttons
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"编辑消息失败: {e}")
        # 如果编辑失败，尝试回复新消息（兼容性处理）
        try:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=parse_mode)
        except:
            pass


def make_fake_update(query, **kwargs):
    """创建 fake_update 对象，用于从回调调用命令函数"""
    defaults = {
        'effective_user': query.from_user,
        'effective_message': query.message,
        'message': query.message,
        'callback_query': query,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def get_menu_layout(is_vip: bool = False) -> list:
    """获取菜单按钮布局"""
    # 第一行：个人档案/成为VIP + 每日签到
    first_button_text = "📜 个人档案" if is_vip else "💎 成为 VIP"
    first_button_data = "me" if is_vip else "upgrade_vip"

    buttons = [
        # === 核心功能区 ===
        [InlineKeyboardButton(first_button_text, callback_data=first_button_data),
         InlineKeyboardButton("🍬 每日签到", callback_data="checkin")],

        # === 🎬 影音专区（Emby观影挖矿）===
        [InlineKeyboardButton("🎬 影音挖矿", callback_data="video_mining")],

        # === 每日必做 ===
        [InlineKeyboardButton("📋 每日任务", callback_data="daily_tasks"),
         InlineKeyboardButton("🎡 幸运转盘", callback_data="lucky_wheel")],

        # === 更多功能 ===
        [InlineKeyboardButton("🎮 更多功能", callback_data="menu_more")],
    ]
    return buttons


def get_more_menu_layout() -> list:
    """获取"更多功能"子菜单"""
    buttons = [
        [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")],
        [InlineKeyboardButton("⚔️ 决斗 & 战斗", callback_data="menu_combat"),
         InlineKeyboardButton("🔮 娱乐 & 抽卡", callback_data="menu_fun")],
        [InlineKeyboardButton("🏦 资产管理", callback_data="menu_asset"),
         InlineKeyboardButton("🎒 个人物品", callback_data="menu_personal")],
        [InlineKeyboardButton("📖 帮助 & 教程", callback_data="menu_help")],
    ]
    return buttons


def get_combat_menu_layout() -> list:
    """战斗功能子菜单"""
    buttons = [
        [InlineKeyboardButton("🔙 返回", callback_data="menu_more")],
        [InlineKeyboardButton("⚔️ 决斗场", callback_data="duel_info"),
         InlineKeyboardButton("🗼 通天塔", callback_data="tower")],
        [InlineKeyboardButton("🏆 排行榜", callback_data="hall")],
    ]
    return buttons


def get_fun_menu_layout() -> list:
    """娱乐功能子菜单"""
    buttons = [
        [InlineKeyboardButton("🔙 返回", callback_data="menu_more")],
        [InlineKeyboardButton("🎰 命运盲盒", callback_data="poster"),
         InlineKeyboardButton("⚒️ 灵装炼金", callback_data="forge")],
    ]
    return buttons


def get_asset_menu_layout() -> list:
    """资产管理子菜单"""
    buttons = [
        [InlineKeyboardButton("🔙 返回", callback_data="menu_more")],
        [InlineKeyboardButton("🏦 皇家银行", callback_data="bank"),
         InlineKeyboardButton("🛒 魔法商店", callback_data="shop")],
        [InlineKeyboardButton("💝 转赠魔力", callback_data="menu_gift")],
    ]
    return buttons


def get_personal_menu_layout() -> list:
    """个人物品子菜单"""
    buttons = [
        [InlineKeyboardButton("🔙 返回", callback_data="menu_more")],
        [InlineKeyboardButton("🎒 次源背包", callback_data="bag"),
         InlineKeyboardButton("📊 活跃度", callback_data="presence")],
        [InlineKeyboardButton("📈 进度预告", callback_data="progress_preview"),
         InlineKeyboardButton("🏆 成就殿堂", callback_data="menu_achievement")],
        [InlineKeyboardButton("🎬 观影记录", callback_data="watch_status")],
    ]
    return buttons


def get_help_menu_layout() -> list:
    """帮助功能子菜单"""
    buttons = [
        [InlineKeyboardButton("🔙 返回", callback_data="menu_more")],
        [InlineKeyboardButton("📖 魔法指南", callback_data="help_manual"),
         InlineKeyboardButton("🎓 新手教程", callback_data="tutorial_start")],
        [InlineKeyboardButton("❓ 常见问题", callback_data="help_faq")],
    ]
    return buttons


def get_user_progress_hint(user_data) -> str:
    """根据用户状态获取下一步提示"""
    if not user_data or not user_data.emby_account:
        return "📌 <b>下一步：</b> 发送 <code>/bind 用户名</code> 绑定账号，领取100MP新手礼包喵~"

    # 新手期提示 (注册7天内)
    if user_data.registered_date:
        from datetime import datetime, timedelta
        days_since = (datetime.now() - user_data.registered_date).days
        if days_since < 7:
            hints = [
                "📌 <b>新手任务：</b> ",
            ]
            if not user_data.last_checkin or user_data.last_checkin.date() < datetime.now().date():
                hints.append("🍬 先签到领MP")
            if (user_data.attack or 0) < 50:
                hints.append("⚒️ 锻造更强武器")
            if (user_data.total_checkin_days or 0) < 3:
                hints.append("📋 完成每日任务")
            return "".join(hints) if len(hints) > 1 else ""

    # 未签到提示
    if not user_data.last_checkin or user_data.last_checkin.date() < __import__('datetime').datetime.now().date():
        return "📌 <b>今日提示：</b> 还没签到哦，点击「每日签到」领取今日MP喵~"

    return ""


def get_menu_text(user, is_vip: bool = False, user_data=None) -> str:
    """获取菜单文本（支持动态引导）"""
    # 获取用户进度提示
    progress_hint = get_user_progress_hint(user_data) if user_data else ""

    if is_vip:
        base_text = (
            f"🌸 <b>【 魔 法 少 女 · 星 辰 殿 堂 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ <b>Welcome back, Master {user.first_name}</b> ✨\n"
            f"您的专属魔法少女看板娘已就位喵~\n\n"
            f"💎 <b>:: 皇 家 特 权 已 激 活 ::</b>\n"
            f"🚀 4K 极速通道 · <b>已开启</b>\n"
            f"🏰 皇家金库 · <b>已解锁</b>\n"
            f"💕 魔力加成 · <b>生效中</b>\n"
        )
        if progress_hint:
            base_text += f"\n{progress_hint}\n"
        base_text += (
            f"\n<i>\"只要Master开口，无论是摘星星还是捕月亮，\n"
            f"人家都会为您办到的~💖\"</i>\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        return base_text
    else:
        base_text = (
            f"🏰 <b>【 云 海 · 魔 法 学 院 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ <b>欢迎来到魔法世界，{user.first_name}酱！</b> ✨\n"
            f"我是你的魔法少女向导 <b>看板娘</b>喵~\n\n"
            f"🎀 <b>:: 当 前 状 态 ::</b>\n"
            f"🌱 身份：见习魔法少女\n"
            f"🔒 皇家特权：<b>未觉醒</b>\n"
        )
        if progress_hint:
            base_text += f"\n{progress_hint}\n"
        base_text += (
            f"\n<i>\"只要努力收集魔力结晶，\n"
            f"总有一天会变成大魔法少女的！\n"
            f"加油喵~！(≧◡≦)\"</i>\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        return base_text


async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user.id).first()
        is_vip = u.is_vip if u else False

    txt = get_menu_text(user, is_vip, u)
    buttons = get_menu_layout(is_vip)

    # 使用 smart_reply 并注册按钮所有者
    from utils import smart_reply, register_button_owner
    reply = await update.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))
    if reply:
        register_button_owner(context, reply.message_id, user.id)


async def help_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """帮助手册 - 使用统一的命令配置"""
    from config.commands import format_help_text

    txt = format_help_text()
    msg = update.effective_message
    if msg:
        await reply_with_auto_delete(msg, txt)


# ==================== Emby 菜单辅助函数 ====================

async def ensure_emby_bound(user_id: int, query) -> bool:
    """检查用户是否已绑定 Emby，未绑定则显示提示"""
    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        if not user or not user.emby_account:
            txt = """💔 <b>【 未 缔 契 约 】</b>

我看不到您的灵魂波长... (´;ω;`)

━━━━━━━━━━━━━━━━━━
📝 <b>请先发送：</b>
<code>/bind 你的Emby用户名</code>

🎁 <b>新手福利：</b>
• 💰 150 MP 魔力
• 🎰 3个盲盒券
• ⚒️ 1张锻造券
• 🗡️ 新手武器 (+10战力)
━━━━━━━━━━━━━━━━━━

<i>"绑定后即可开始冒险喵~(｡•̀ᴗ-)✧"</i>"""
            await edit_callback_message(query, txt)
            return False
        return True


async def handle_watch_recommend(query):
    """处理观影推荐"""
    if not await ensure_emby_bound(query.from_user.id, query):
        return

    if not EMBY_URL or not EMBY_API_KEY:
        await edit_callback_message(query, "📭 <b>Emby 未配置</b>\n\n请联系管理员喵~")
        return

    try:
        headers = {
            "X-Emby-Token": EMBY_API_KEY,
            "Accept": "application/json",
            "User-Agent": "curl/7.68.0"
        }

        async with aiohttp.ClientSession() as session:
            # 获取媒体总数
            async with session.get(f"{EMBY_URL}/Items", headers=headers,
                                   params={"IncludeItemTypes": "Movie,Episode", "Recursive": "true", "Limit": 1},
                                   timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    raise Exception("获取媒体失败")
                data = await resp.json()
                total_count = data.get('TotalRecordCount', 0)

            if total_count == 0:
                await edit_callback_message(query, "📭 媒体库空空如也喵~")
                return

            # 随机选取
            async with session.get(f"{EMBY_URL}/Items", headers=headers,
                                   params={"IncludeItemTypes": "Movie,Episode", "Recursive": "true",
                                           "StartIndex": random.randint(0, max(0, total_count - 1)), "Limit": 1},
                                   timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    raise Exception("获取推荐失败")
                data = await resp.json()
                items = data.get('Items', [])
                if not items:
                    await edit_callback_message(query, "📭 推荐获取失败喵~")
                    return

                item = items[0]
                item_type = str(item.get('Type', '')) if not isinstance(item.get('Type'), bool) else ''

                # 对于剧集，优先显示剧集名称
                if item_type == "Episode":
                    series_name = str(item.get('SeriesName', '')) if not isinstance(item.get('SeriesName'), bool) else ''
                    episode_name = str(item.get('Name', '')) if not isinstance(item.get('Name'), bool) else ''
                    item_name = f"{series_name} · {episode_name}" if series_name else (episode_name or '未知')
                else:
                    item_name = str(item.get('Name', '未知')) if not isinstance(item.get('Name'), bool) else '未知'

                production_year = item.get('ProductionYear')
                genres = item.get('Genres') or []
                overview = str(item.get('Overview', '')) if not isinstance(item.get('Overview'), bool) else ''

                type_icon = "🎬" if item_type == "Movie" else "📺"
                genre_text = f"{' | '.join(str(g) for g in genres[:3] if g and not isinstance(g, bool))}" if genres else "未分类"

                # 清理HTML标签
                if overview:
                    overview = re.sub(r'<[^>]+>', '', overview)
                    if len(overview) > 100:
                        overview = overview[:100] + "..."

                lines = [
                    f"🎲 <b>【 今 日 观 影 推 荐 】</b>",
                    "━━━━━━━━━━━━━━━━━━",
                    f"{type_icon} <b>{item_name}</b>",
                ]

                if production_year and isinstance(production_year, int):
                    lines.append(f"📅 {production_year}")
                if genre_text != "未分类":
                    lines.append(f"🏷️ {genre_text}")

                lines.append("━━━━━━━━━━━━━━━━━━")
                if overview:
                    lines.append(f"📝 {overview}")
                    lines.append("━━━━━━━━━━━━━━━━━━")
                lines.append(f"<i>\"今天就看这个吧 Master！(｡•̀ᴗ-)✧\"</i>")

                await edit_callback_message(query, "\n".join(lines))

    except Exception as e:
        logger.exception("观影推荐失败")
        await edit_callback_message(query, f"💔 推荐获取失败: {str(e)}")



async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理按钮点击事件"""
    query = update.callback_query
    await query.answer()

    # 权限检查：确保只有菜单发起者能点击按钮
    from utils import check_button_owner, deny_button_access
    if not check_button_owner(context, query):
        await deny_button_access(query)
        return

    data = query.data

    # 调试日志
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"button_callback received: {data}")

    # 返回菜单
    if data == "back_menu":
        user = query.from_user
        with get_session() as session:
            u = session.query(UserBinding).filter_by(tg_id=user.id).first()
            is_vip = u.is_vip if u else False

        txt = get_menu_text(user, is_vip, u)
        buttons = get_menu_layout(is_vip)
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))
        return

    # 个人档案
    if data == "me":
        from plugins.me import me_panel
        fake_update = make_fake_update(query, callback_query=query)
        await me_panel(fake_update, context)

    # 签到
    elif data == "checkin":
        from plugins.checkin_bind import checkin
        fake_update = make_fake_update(query)
        await checkin(fake_update, context)

    # 银行
    elif data == "bank":
        from plugins.bank import bank_panel
        fake_update = make_fake_update(query)
        await bank_panel(fake_update, context)

    # 商店
    elif data == "shop":
        from plugins.shop import shop_main
        fake_update = make_fake_update(query)
        await shop_main(fake_update, context)

    # 背包
    elif data == "bag":
        from plugins.bag import my_bag
        fake_update = make_fake_update(query)
        await my_bag(fake_update, context)

    # 排行榜
    if data == "hall":
        from plugins.hall import hall_leaderboard
        fake_update = make_fake_update(query)
        await hall_leaderboard(fake_update, context)

    # 活跃度
    elif data == "presence":
        from plugins.presence import presence_cmd
        fake_update = make_fake_update(query)
        await presence_cmd(fake_update, context)

    # 炼金
    elif data == "forge":
        from plugins.forge import forge_start
        fake_update = make_fake_update(query, callback_query=query)
        await forge_start(fake_update, context)

    # === 分层菜单导航 ===
    # 更多功能
    elif data == "menu_more":
        txt = (
            "🎮 <b>【 更 多 功 能 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "选择一个分类查看更多功能喵~\n"
        )
        buttons = get_more_menu_layout()
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 返回主菜单
    elif data == "back_main":
        user = query.from_user
        with get_session() as session:
            u = session.query(UserBinding).filter_by(tg_id=user.id).first()
            is_vip = u.is_vip if u else False

        txt = get_menu_text(user, is_vip, u)
        buttons = get_menu_layout(is_vip)
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 战斗功能子菜单
    elif data == "menu_combat":
        txt = (
            "⚔️ <b>【 决 斗 & 战 斗 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "选择战斗功能喵~\n"
        )
        buttons = get_combat_menu_layout()
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 娱乐功能子菜单
    elif data == "menu_fun":
        txt = (
            "🔮 <b>【 娱 乐 & 抽 卡 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "选择娱乐功能喵~\n"
        )
        buttons = get_fun_menu_layout()
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 资产管理子菜单
    elif data == "menu_asset":
        txt = (
            "🏦 <b>【 资 产 管 理 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "选择资产管理功能喵~\n"
        )
        buttons = get_asset_menu_layout()
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 个人物品子菜单
    elif data == "menu_personal":
        txt = (
            "🎒 <b>【 个 人 物 品 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "选择个人功能喵~\n"
        )
        buttons = get_personal_menu_layout()
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 帮助功能子菜单
    elif data == "menu_help":
        txt = (
            "📖 <b>【 帮 助 & 教 程 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "选择帮助功能喵~\n"
        )
        buttons = get_help_menu_layout()
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 转赠魔力 (资产管理子菜单功能)
    elif data == "menu_gift":
        txt = (
            "💝 <b>【 转 赠 魔 力 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "📝 <b>操作方法：</b>\n"
            "回复要转赠的小伙伴消息\n"
            "然后发送：<code>/gift 金额</code>\n\n"
            "💡 <b>VIP特权：</b>\n"
            "VIP用户转赠免手续费哦~\n\n"
            "<i>\"分享魔力，分享快乐喵！(｡•̀ᴗ-)✧\"</i>\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        buttons = [[InlineKeyboardButton("🔙 返回", callback_data="menu_asset")]]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 成就殿堂 (个人物品子菜单功能)
    elif data == "menu_achievement":
        from plugins.achievement import achievement_list
        fake_update = make_fake_update(query, callback_query=query)
        await achievement_list(fake_update, context)

    # 常见问题 (帮助子菜单功能)
    elif data == "help_faq":
        txt = (
            "❓ <b>【 常 见 问 题 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "🔹 <b>Q: 如何获得魔力？</b>\n"
            "A: 每日签到、完成任务、决斗获胜、转盘抽奖、观影挖矿\n\n"
            "🔹 <b>Q: 新手有什么福利？</b>\n"
            "A: 绑定账号送100MP+道具，前7天观影翻倍(5分钟=1MP)\n\n"
            "🔹 <b>Q: 什么是VIP？</b>\n"
            "A: VIP享受签到1.5倍、锻造5折、银行免手续费等特权\n\n"
            "🔹 <b>Q: 如何提高战力？</b>\n"
            "A: 使用 /forge 锻造武器，有保底机制(10次R+/30次SR+)\n\n"
            "🔹 <b>Q: 决斗输了会怎样？</b>\n"
            "A: 输掉赌注的魔力，但连胜有额外奖励加成喵~\n\n"
            "🔹 <b>Q: 影音挖矿是什么？</b>\n"
            "A: 绑定Emby后，观影10分钟=1MP(新手5分钟)，VIP1.5倍加成\n\n"
            "🔹 <b>Q: 各种概率是多少？</b>\n"
            "A: /shop 宝箱: 神话0.5%|传说1.5%|史诗5%|稀有18%\n"
            "   /wheel 转盘: 5MP(26%)|10MP(21%)|20MP(16%)|500MP(0.5%)\n"
            "   /forge 锻造: 保底10次R+精良，30次SR+稀有\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "<i>\"还有问题可以召唤看板娘哦！(｡•̀ᴗ-)✧\"</i>"
        )
        buttons = [[InlineKeyboardButton("🔙 返回", callback_data="menu_help")]]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 进度预告
    elif data == "progress_preview":
        from plugins.progress import progress_preview
        fake_update = make_fake_update(query, callback_query=query)
        await progress_preview(fake_update, context)

    # 每日任务
    elif data == "daily_tasks":
        from plugins.unified_mission import mission_main
        fake_update = make_fake_update(query, effective_chat=query.message.chat)
        await mission_main(fake_update, context, "daily")

    # 幸运转盘
    elif data == "lucky_wheel":
        from plugins.lucky_wheel import wheel_cmd
        fake_update = make_fake_update(query)
        await wheel_cmd(fake_update, context)

    # 命运盲盒
    elif data == "poster":
        from plugins.fun_games import blind_box_gacha
        fake_update = make_fake_update(query)
        await blind_box_gacha(fake_update, context)

    # 决斗说明
    elif data == "duel_info":
        txt = (
            "⚔️ <b>【 魔 法 少 女 · 决 斗 竞 技 场 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "📜 <b>决斗规则：</b>\n"
            "1️⃣ 回复要挑战的小伙伴消息\n"
            "2️⃣ 发送 <code>/duel 金额</code>\n"
            "3️⃣ 等待对方接受挑战喵~\n"
            "4️⃣ 胜者获得全部赌注！\n\n"
            "<i>\"想成为魔法少女决斗王吗？\n"
            "来试试吧！(｡･ω･｡)ﾉ♡\"</i>\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        buttons = [[InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # VIP中心
    elif data == "vip":
        user = query.from_user
        with get_session() as session:
            u = session.query(UserBinding).filter_by(tg_id=user.id).first()
            is_vip = u.is_vip if u else False

        if is_vip:
            txt = (
                "👑 <b>【 皇 家 · 星 辰 殿 堂 】</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "✨ <b>欢迎回来，尊贵的 Master~</b> ✨\n\n"
                "💠 <b>:: 已 觉 醒 之 力 ::</b>\n\n"
                "🚀 4K 极速通道 · <b>已开启</b>\n"
                "🏰 皇家金库 · <b>0 手续费</b>\n"
                "💰 魔力加成 · <b>签到 1.5x</b>\n"
                "⚒️ 炼金工坊 · <b>锻造 5 折</b>\n"
                "🔮 命运眷顾 · <b>塔罗 5 折</b>\n"
                "🎁 魔力转赠 · <b>免手续费</b>\n"
                "⚔️ 决斗祝福 · <b>+5% 胜率</b>\n"
                "🏆 星辰称号 · <b>尊贵头衔</b>\n"
                "🏦 银行利息 · <b>日息 1%</b>\n"
                "🛡️ 连败安慰 · <b>额外奖励</b>\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "<i>「星光永远照耀您~💖」</i>"
            )
        else:
            txt = (
                "🗝️ <b>【 觉 醒 之 门 】</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "✨ <b>准备好觉醒成为真正的皇家魔法少女了吗？</b> ✨\n\n"
                "💠 <b>:: 觉 醒 后 获 得 的 力 量 ::</b>\n\n"
                "🚀 4K 极速通道 · 画质飞跃\n"
                "🏰 皇家金库 · 0 手续费\n"
                "💰 魔力加成 · 签到 1.5x\n"
                "⚒️ 炼金工坊 · 锻造 5 折\n"
                "🔮 命运眷顾 · 塔罗 5 折\n"
                "🎁 魔力转赠 · 免手续费\n"
                "⚔️ 决斗祝福 · +5% 胜率\n"
                "🏆 星辰称号 · 尊贵头衔\n"
                "🏦 银行利息 · 日息 1%\n"
                "🛡️ 连败安慰 · 额外奖励\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "<i>「仅需一次证明材料，即可永久觉醒喵~(｡･ω･｡)ﾉ♡」</i>"
            )
        buttons = [[InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 升级VIP
    elif data == "upgrade_vip":
        txt = (
            "🗝️ <b>【 觉 醒 之 门 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "✨ <b>准备好觉醒成为真正的皇家魔法少女了吗？</b> ✨\n\n"
            "💠 <b>:: 觉 醒 后 获 得 的 力 量 ::</b>\n\n"
            "🚀 4K 极速通道 · 画质飞跃\n"
            "🏰 皇家金库 · 0 手续费\n"
            "💰 魔力加成 · 签到 1.5x\n"
            "⚒️ 炼金工坊 · 锻造 5 折\n"
            "🔮 命运眷顾 · 塔罗 5 折\n"
            "🎁 魔力转赠 · 免手续费\n"
            "⚔️ 决斗祝福 · +5% 胜率\n"
            "🏆 星辰称号 · 尊贵头衔\n"
            "🏦 银行利息 · 日息 1%\n"
            "🛡️ 连败安慰 · 额外奖励\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "<i>「仅需一次证明材料，即可永久觉醒喵~(｡･ω･｡)ﾉ♡」</i>"
        )
        buttons = [
            [InlineKeyboardButton("📩 申请觉醒", callback_data="apply_vip")],
            [InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]
        ]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 申请VIP
    elif data == "apply_vip":
        txt = (
            "📜 <b>【 V I P · 觉 醒 仪 式 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "请在 <b>私聊</b> 中使用以下命令申请觉醒喵~\n\n"
            "<code>/applyvip</code>\n\n"
            "📋 <b>觉醒步骤：</b>\n"
            "1️⃣ 私聊看板娘发送 <code>/applyvip</code>\n"
            "2️⃣ 发送证明材料喵\n"
            "3️⃣ 等待审核通过\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "<i>\"点击下方按钮直接跳转私聊哦 (｡•̀ᴗ-)✧\"</i>"
        )
        buttons = [
            [InlineKeyboardButton("📩 前往私聊申请", url=f"https://t.me/{context.bot.username}")],
            [InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]
        ]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 帮助手册
    elif data == "help_manual":
        from config.commands import format_help_text
        txt = format_help_text()
        buttons = [[InlineKeyboardButton("🔙 返回菜单", callback_data="back_menu")]]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 通天塔
    elif data == "tower":
        from plugins.tower import tower_panel
        fake_update = make_fake_update(query, callback_query=query)
        await tower_panel(fake_update, context)

    # === 🎬 Emby 观影挖矿系统 ===
    # 影音挖矿主菜单
    elif data == "video_mining":
        txt = (
            "🎬 <b>【 影 音 · 挖 矿 中 心 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "📺 <b>边看片边赚MP，观影也能薅羊毛！</b>\n\n"
            "💰 <b>奖励规则：</b>5分钟 = 1 MP | 每日最多36 MP\n"
            "👑 <b>VIP加成：</b>所有收益 ×1.5\n\n"
        )
        # 精简按钮布局，2列排列
        buttons = [
            [
                InlineKeyboardButton("📊 观影状态", callback_data="watch_status"),
                InlineKeyboardButton("🏆 排行榜", callback_data="weekly_watch")
            ],
            [
                InlineKeyboardButton("🏁 首播冲刺", callback_data="early_bird_menu"),
                InlineKeyboardButton("🎯 每周挑战", callback_data="weekly_challenge_menu")
            ],
            [
                InlineKeyboardButton("🏆 观影成就", callback_data="watch_ach_menu"),
                InlineKeyboardButton("📈 观影统计", callback_data="watch_stats_menu")
            ],
            [
                InlineKeyboardButton("🎲 观影推荐", callback_data="watch_rec_menu"),
                InlineKeyboardButton("👑 VIP特权", callback_data="vip_watch_menu")
            ],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")]
        ]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 首播冲刺菜单
    elif data == "early_bird_menu":
        from plugins.emby_watch import cmd_early_bird
        fake_update = make_fake_update(query, effective_message=query.message)
        await cmd_early_bird(fake_update, context)

    # 每周挑战菜单
    elif data == "weekly_challenge_menu":
        from plugins.emby_watch import cmd_weekly_challenge
        fake_update = make_fake_update(query, effective_message=query.message)
        await cmd_weekly_challenge(fake_update, context)

    # 观影成就菜单
    elif data == "watch_ach_menu":
        from plugins.emby_watch import cmd_watch_achievements
        fake_update = make_fake_update(query, effective_message=query.message)
        await cmd_watch_achievements(fake_update, context)

    # 观影推荐菜单
    elif data == "watch_rec_menu":
        await handle_watch_recommend(query)

    # 观影统计菜单
    elif data == "watch_stats_menu":
        from plugins.emby_watch import cmd_watch_stats
        fake_update = make_fake_update(query, effective_message=query.message)
        await cmd_watch_stats(fake_update, context)

    # VIP观影特权菜单
    elif data == "vip_watch_menu":
        from plugins.emby_watch import cmd_vip_watch_benefits
        fake_update = make_fake_update(query, effective_message=query.message)
        await cmd_vip_watch_benefits(fake_update, context)

    # 绑定Emby帮助
    elif data == "bind_emby_help":
        txt = (
            "🔗 <b>【 账 号 绑 定 】</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "📝 <b>绑定方法：</b>\n"
            "发送命令：<code>/bind Emby用户名</code>\n\n"
            "💡 <b>例如：</b>\n"
            "<code>/bind 张三</code>\n\n"
            "❓ <b>如何查看自己的Emby用户名？</b>\n"
            "1. 打开 Emby 网站/APP\n"
            "2. 点击左上角头像\n"
            "3. 查看显示的名称\n\n"
            "<i>\"绑定后就能签到领MP，观影还能赚MP啦~(｡•̀ᴗ-)✧\"</i>\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        buttons = [[InlineKeyboardButton("🔙 返回", callback_data="video_mining")]]
        try:
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
        except Exception:
            await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))

    # 观影状态
    elif data == "watch_status":
        from plugins.emby_watch import cmd_watch_status
        fake_update = make_fake_update(query, effective_message=query.message)
        await cmd_watch_status(fake_update, context)

    # 观影排行榜
    elif data == "weekly_watch":
        from plugins.emby_watch import cmd_weekly_watch
        fake_update = make_fake_update(query, effective_message=query.message)
        await cmd_weekly_watch(fake_update, context)


def register(app):
    app.add_handler(CommandHandler("start", start_menu))
    app.add_handler(CommandHandler("menu", start_menu))
    app.add_handler(CommandHandler("help", help_manual))

    # 直接列出需要处理的回调，使用多个简单的 pattern
    import sys
    print("🔧 start_menu: 注册主菜单回调 handlers", flush=True)
    sys.stdout.flush()

    # 主菜单按钮 - 使用 group=0 确保优先处理
    for data in ["me", "checkin", "bank", "shop", "bag", "hall", "presence", "forge", "video_mining",
                 "lucky_wheel", "daily_tasks", "menu_more", "back_menu", "back_main"]:
        app.add_handler(CallbackQueryHandler(button_callback, pattern=f"^{data}$"), group=0)
        print(f"  ✅ 注册: {data}", flush=True)

    # 子菜单按钮
    for data in ["menu_combat", "menu_fun", "menu_asset", "menu_personal", "menu_help",
                 "menu_gift", "menu_achievement", "progress_preview", "duel_info",
                 "vip", "upgrade_vip", "apply_vip", "help_manual", "help_faq"]:
        app.add_handler(CallbackQueryHandler(button_callback, pattern=f"^{data}$"), group=0)
        print(f"  ✅ 注册: {data}", flush=True)

    # Emby 观影挖矿相关
    for data in ["bind_emby_help", "watch_status", "weekly_watch",
                 "early_bird_menu", "weekly_challenge_menu", "watch_ach_menu",
                 "watch_rec_menu", "watch_stats_menu", "vip_watch_menu"]:
        app.add_handler(CallbackQueryHandler(button_callback, pattern=f"^{data}$"), group=0)
        print(f"  ✅ 注册: {data}", flush=True)

    # 娱乐功能（从 fun_games 导入）
    for data in ["poster"]:
        app.add_handler(CallbackQueryHandler(button_callback, pattern=f"^{data}$"), group=0)
        print(f"  ✅ 注册: {data}", flush=True)

    print("🎉 start_menu: 所有主菜单回调已注册", flush=True)
    sys.stdout.flush()
