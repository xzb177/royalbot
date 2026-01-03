"""
Emby 媒体库监控模块 - 仅推送 REMUX 电影入库
"""
import asyncio
import logging
import os
import tempfile
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CommandHandler, ContextTypes, CallbackContext, CallbackQueryHandler
from config import Config
from utils import reply_with_auto_delete
from database import get_session, UserBinding

logger = logging.getLogger(__name__)

# Emby API 配置
EMBY_URL = Config.EMBY_URL.rstrip('/')
EMBY_API_KEY = Config.EMBY_API_KEY
EMBY_USER_ID = "f622565cba214bfca04609d32d5d26d0"  # 默认用户ID

# 推送记录文件路径
PUSHED_ITEMS_FILE = "data/pushed_emby_items.txt"

# === 📦 全局存储（从 reward_push.py 导入共享变量） ===
# 注意：导入后使用 reward_push.ACTIVE_PUSHES 来访问
from plugins import reward_push
ACTIVE_PUSHES = reward_push.ACTIVE_PUSHES
LAST_REWARD_TIME = reward_push.LAST_REWARD_TIME


def load_pushed_items() -> set:
    """从文件加载已推送的媒体ID集合"""
    pushed = set()
    try:
        if os.path.exists(PUSHED_ITEMS_FILE):
            with open(PUSHED_ITEMS_FILE, 'r') as f:
                for line in f:
                    item_id = line.strip()
                    if item_id:
                        pushed.add(item_id)
            logger.info(f"已加载 {len(pushed)} 条已推送记录")
    except Exception as e:
        logger.error(f"加载推送记录失败: {e}")
    return pushed


def save_pushed_item(item_id: str):
    """保存新推送的媒体ID到文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(PUSHED_ITEMS_FILE), exist_ok=True)
        with open(PUSHED_ITEMS_FILE, 'a') as f:
            f.write(f"{item_id}\n")
    except Exception as e:
        logger.error(f"保存推送记录失败: {e}")


# 启动时加载已推送记录
pushed_items = load_pushed_items()

# REMUX 检测关键词（不区分大小写）
REMUX_KEYWORDS = ['REMUX', 'Remux', 'remux']


async def download_image(url: str) -> Optional[str]:
    """
    下载图片到临时文件

    Args:
        url: 图片URL

    Returns:
        临时文件路径，失败返回 None
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=get_emby_headers(), ssl=False, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    # 读取图片数据
                    data = await resp.read()

                    # 创建临时文件
                    suffix = '.jpg'
                    fd, path = tempfile.mkstemp(suffix=suffix)
                    with os.fdopen(fd, 'wb') as f:
                        f.write(data)

                    return path
    except Exception as e:
        logger.error(f"下载图片失败 {url}: {e}")

    return None


def get_emby_headers():
    """获取 Emby API 请求头"""
    return {
        "X-Emby-Token": EMBY_API_KEY,
        "Accept": "application/json",
        "User-Agent": "curl/7.68.0"
    }


def is_remux(item: Dict, details: Dict) -> bool:
    """
    检测是否为 REMUX 格式

    Args:
        item: 媒体项目基本信息
        details: 媒体项目详细信息

    Returns:
        True 如果是 REMUX 格式
    """
    # 检查文件名
    file_name = item.get('Name', '') or details.get('FileName', '')
    for keyword in REMUX_KEYWORDS:
        if keyword in file_name:
            return True

    # 检查路径（如果有的话）
    path = details.get('Path', '')
    for keyword in REMUX_KEYWORDS:
        if keyword in path:
            return True

    return False


def get_image_url(item_id: str, image_tag: str = None, image_type: str = "Primary") -> str:
    """获取图片URL（Emby 服务器允许公开访问图片）"""
    # 不需要 image_tag 和 api_key，直接返回基础 URL
    return f"{EMBY_URL}/Items/{item_id}/Images/{image_type}"


async def fetch_latest_items(limit: int = 10, days: int = 1) -> List[Dict]:
    """
    获取最新入库的电影项目（仅电影）

    Args:
        limit: 获取数量
        days: 获取最近几天的内容

    Returns:
        媒体项目列表
    """
    if not EMBY_URL or not EMBY_API_KEY:
        logger.warning("Emby 配置不完整")
        return []

    items = []
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    try:
        async with aiohttp.ClientSession() as session:
            # 只获取电影类型
            url = (
                f"{EMBY_URL}/Users/{EMBY_USER_ID}/Items"
                f"?SortBy=DateCreated"
                f"&SortOrder=Descending"
                f"&MinDateCreated={cutoff}"
                f"&Recursive=true"
                f"&IncludeItemTypes=Movie"
                f"&Limit={limit}"
            )
            async with session.get(url, headers=get_emby_headers(), ssl=False) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get('Items', [])

    except Exception as e:
        logger.error(f"获取 Emby 最新项目失败: {e}")

    return items


async def fetch_item_details(item_id: str) -> Optional[Dict]:
    """
    获取媒体项目详细信息（含码率、评分等）

    Args:
        item_id: 媒体项目ID

    Returns:
        详细信息字典
    """
    if not EMBY_URL or not EMBY_API_KEY:
        return None

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{EMBY_URL}/Users/{EMBY_USER_ID}/Items/{item_id}"
            async with session.get(url, headers=get_emby_headers(), ssl=False) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logger.error(f"获取项目 {item_id} 详情失败: {e}")

    return None


def build_showcase_message(item: Dict, details: Dict, index: int = 0) -> Tuple[str, Optional[str]]:
    """
    构建 REMUX 电影推送消息（甜蜜约会风，与手动推送统一）

    Returns:
        (消息文本, 海报URL)
    """
    name = item.get('Name', '未知')
    year = item.get('ProductionYear', '????')

    # 评分
    rating = details.get('CommunityRating')
    rating_text = f"{rating:.1f}" if rating else "N/A"

    # 获取视频规格
    specs = get_video_specs(item, details)
    spec_tags = " | ".join([f"<code>{s}</code>" for s in specs])

    # 获取类型/标签
    genres = details.get('Genres', [])
    genre_text = "/".join(genres[:2]) if genres else "未分类"

    # 海报URL
    image_tags = details.get('ImageTags', {})
    poster_url = None
    if image_tags.get('Primary'):
        poster_url = get_image_url(item.get('Id'), image_tags['Primary'])

    # 甜蜜约会风推送消息
    msg = (
        f"💌 <b>Master... 馆藏更新啦！</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🌸 <b>本周主打推荐：</b>\n"
        f"🎬 <b>《 {name} 》 ({year})</b>\n\n"
        f"✨ <b>视听规格鉴定：</b>\n"
        f"🏷️ {spec_tags} | ⭐ <code>{rating_text}分</code>\n"
        f"🍿 类型： <code>{genre_text}</code>\n\n"
        f"<i>「早就帮您准备好了最佳观影位...\n"
        f"那个... 要一起看吗？(⁄ ⁄•⁄ω⁄•⁄ ⁄)」</i>\n"
    )

    return msg, poster_url


def get_video_specs(item: Dict, details: Dict) -> List[str]:
    """
    获取视频规格信息

    Args:
        item: 媒体项目基本信息
        details: 媒体项目详细信息

    Returns:
        规格标签列表
    """
    specs = []

    if details.get('MediaSources'):
        source = details['MediaSources'][0]
        if source.get('MediaStreams'):
            video = next((s for s in source['MediaStreams'] if s['Type'] == 'Video'), None)
            if video:
                # 分辨率
                width = video.get('Width', 0)
                if width >= 3800:
                    specs.append("4K UHD")
                elif width >= 1900:
                    specs.append("1080P")
                elif width >= 1200:
                    specs.append("720P")

                # 编码
                codec = video.get('Codec', '').upper()
                if codec == 'HEVC':
                    specs.append("HEVC")
                elif codec == 'H264':
                    specs.append("H.264")
                elif codec == 'AV1':
                    specs.append("AV1")

                # HDR
                video_range = video.get('VideoRange', '')
                if 'HDR' in video_range or video.get('HdrFormat'):
                    hdr_format = video.get('HdrFormat', '')
                    if hdr_format:
                        specs.append(hdr_format.upper())
                    else:
                        specs.append("HDR")

                # 色深
                bit_depth = video.get('BitDepth', 0)
                if bit_depth >= 10:
                    specs.append(f"{bit_depth}bit")

    return specs if specs else ["高清资源"]


async def cmd_push_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    通过 Emby Item ID 手动推送指定媒体（仅管理员）
    用法: /share 114514 或 /pushid 114514
    """
    msg = update.effective_message
    user = msg.from_user

    # 权限检查
    if user.id != Config.OWNER_ID:
        await reply_with_auto_delete(msg, "🚫 <b>无权操作！</b>\n只有馆长才能发布新片喵~")
        return

    # 获取参数
    if not context.args:
        await reply_with_auto_delete(
            msg,
            "⚠️ <b>用法错误！</b>\n请提供 Emby Item ID：\n<code>/share 114514</code>"
        )
        return

    item_id = context.args[0]
    await reply_with_auto_delete(msg, f"🔍 <b>正在检索 ID: {item_id} ...</b>")

    # 查询 Emby API
    try:
        async with aiohttp.ClientSession() as session:
            url = (
                f"{EMBY_URL}/Items"
                f"?Ids={item_id}"
                f"&Fields=Path,Genres,Overview,OfficialRating,CommunityRating,MediaSources,ProductionYear"
            )
            async with session.get(url, headers=get_emby_headers(), ssl=False, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    await reply_with_auto_delete(msg, f"❌ 连接 Emby 失败 (HTTP {resp.status})")
                    return
                data = await resp.json()

        if not data or not data.get("Items"):
            await reply_with_auto_delete(msg, "❌ 未找到该 ID 对应的媒体！")
            return

        item = data["Items"][0]
        item_id_internal = item.get('Id')

        # 获取详细信息
        details = await fetch_item_details(item_id_internal)
        if not details:
            details = item

        # 构建推送内容
        title = item.get('Name', '未知')
        year = item.get('ProductionYear', '????')
        rating = details.get('CommunityRating')
        rating_text = f"{rating:.1f}" if rating else "N/A"

        # 获取视频规格
        specs = get_video_specs(item, details)
        spec_tags = " | ".join([f"<code>{s}</code>" for s in specs])

        # 获取类型
        genres = details.get('Genres', [])
        genre_text = "/".join(genres[:2]) if genres else "未分类"

        # 获取海报 URL
        poster_url = get_image_url(item_id_internal)

        # 构建甜蜜约会风文案
        caption = (
            f"💌 <b>Master... 馆藏更新啦！</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"🌸 <b>本周主打推荐：</b>\n"
            f"🎬 <b>《 {title} 》 ({year})</b>\n\n"
            f"✨ <b>视听规格鉴定：</b>\n"
            f"🏷️ {spec_tags} | ⭐ <code>{rating_text}分</code>\n"
            f"🍿 类型： <code>{genre_text}</code>\n\n"
            f"<i>「早就帮您准备好了最佳观影位...\n"
            f"那个... 要一起看吗？(⁄ ⁄•⁄ω⁄•⁄ ⁄)」</i>\n"
            f"━━━━━━━━━━━━━━\n"
            f"🎁 <b>观影小彩蛋：</b>\n"
            f"👇 <b>回复</b> 这条消息，领取今日份的魔力补给！"
        )

        # 下载海报并发送
        photo_path = await download_image(poster_url) if poster_url else None

        if photo_path:
            with open(photo_path, 'rb') as f:
                push_msg = await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=f,
                    caption=caption,
                    parse_mode='HTML'
                )
            try:
                os.unlink(photo_path)
            except:
                pass
        else:
            push_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=caption,
                parse_mode='HTML'
            )

        # 注册到互动挖矿系统（使用全局变量）
        push_id = f"manual_{push_msg.message_id}_{int(datetime.now().timestamp())}"
        ACTIVE_PUSHES[push_msg.message_id] = {
            'chat_id': update.effective_chat.id,
            'push_id': push_id,
            'claimed_users': set(),
            'created_at': datetime.now(),
            'is_manual_push': True
        }

        await reply_with_auto_delete(msg, "✅ <b>推送成功！</b>\n已自动开启互动挖矿喵~")

    except aiohttp.ClientError as e:
        await reply_with_auto_delete(msg, f"❌ 连接 Emby 失败: {str(e)}")
    except Exception as e:
        logger.error(f"推送失败: {e}")
        await reply_with_auto_delete(msg, f"❌ 推送失败：{str(e)}")


async def cmd_emby_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看最新入库的电影（仅管理员）"""
    msg = update.effective_message
    user = msg.from_user

    if user.id != Config.OWNER_ID:
        await reply_with_auto_delete(msg, "⛔ <b>权限不足</b>\n此命令仅限管理员使用喵~")
        return

    limit = 10
    if context.args and context.args[0].isdigit():
        limit = min(int(context.args[0]), 50)

    await reply_with_auto_delete(msg, f"🔄 <b>正在获取最新入库...</b>\n请稍候喵~")

    items = await fetch_latest_items(limit)

    if not items:
        await reply_with_auto_delete(msg, "📭 <b>暂无新内容</b>\n最近没有新增电影喵~")
        return

    # 获取详细信息检查 REMUX
    lines = [f"🎬 <b>【 Emby 最新电影入库 】</b>\n━━━━━━━━━━━━━━━━━━"]
    remux_count = 0

    for item in items:
        item_id = item.get('Id')
        name = item.get('Name', '未知')
        year = item.get('ProductionYear', '')
        year_str = f" ({year})" if year else ""

        # 检查是否已推送
        status = ""
        if item_id in pushed_items:
            status = " ✅已推送"
        elif item_id:
            details = await fetch_item_details(item_id)
            is_r = is_remux(item, details) if details else False
            if is_r:
                status = " 🔥REMUX"
                remux_count += 1

        lines.append(f"🎬 {name}{year_str}{status}")

    lines.append(f"\n━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 共 {len(items)} 部电影，其中 {remux_count} 部 REMUX")
    lines.append(f"💡 使用 /new 查看可推送的 REMUX 电影")

    await reply_with_auto_delete(msg, "\n".join(lines))


async def cmd_new_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    显示最新入库的 REMUX 电影列表（未推送的）
    管理员可点击按钮直接推送
    """
    msg = update.effective_message
    user = msg.from_user
    query = update.callback_query

    if user.id != Config.OWNER_ID:
        if query:
            await query.answer("⛔ 权限不足")
        else:
            await reply_with_auto_delete(msg, "⛔ <b>权限不足</b>\n此命令仅限管理员使用喵~")
        return

    # 获取最新 REMUX 电影
    items = await fetch_latest_items(limit=20, days=1)

    if not items:
        text = "📭 <b>暂无新内容</b>\n最近没有新增电影喵~"
        if query:
            await query.edit_message_text(text, parse_mode='HTML')
        else:
            await reply_with_auto_delete(msg, text)
        return

    # 构建按钮列表
    keyboard = []
    remux_items = []

    for item in items:
        item_id = item.get('Id')
        if not item_id:
            continue

        # 跳过已推送的
        if item_id in pushed_items:
            continue

        details = await fetch_item_details(item_id)
        if not details:
            continue

        # 只显示 REMUX
        if not is_remux(item, details):
            continue

        name = item.get('Name', '未知')
        year = item.get('ProductionYear', '')
        year_str = f" ({year})" if year else ""

        # 截断过长的名称
        display_name = f"{name}{year_str}"[:25] + "..." if len(f"{name}{year_str}") > 25 else f"{name}{year_str}"
        remux_items.append((item_id, display_name))

    if not remux_items:
        text = "📭 <b>没有新的 REMUX 电影</b>\n所有 REMUX 电影都已推送喵~"
        if query:
            await query.edit_message_text(text, parse_mode='HTML')
        else:
            await reply_with_auto_delete(msg, text)
        return

    # 构建按钮（每行2个）
    for i in range(0, len(remux_items), 2):
        row = []
        for item_id, name in remux_items[i:i+2]:
            row.append(InlineKeyboardButton(f"📤 {name}", callback_data=f"emby_push_{item_id}"))
        keyboard.append(row)

    # 添加刷新按钮
    keyboard.append([InlineKeyboardButton("🔄 刷新列表", callback_data="emby_refresh_new")])

    text = (
        f"🎬 <b>【 待推送 REMUX 电影 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 共 <b>{len(remux_items)}</b> 部待推送\n"
        f"点击按钮立即推送喵~"
    )

    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await msg.reply_html(text, reply_markup=reply_markup)


async def emby_push_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理推送按钮回调"""
    query = update.callback_query
    user = query.from_user

    if user.id != Config.OWNER_ID:
        await query.answer("⛔ 权限不足")
        return

    # 解析 item_id
    callback_data = query.data
    if callback_data == "emby_refresh_new":
        await query.answer()
        await cmd_new_list(update, context)
        return

    if not callback_data.startswith("emby_push_"):
        await query.answer("❌ 无效的按钮")
        return

    item_id = callback_data.replace("emby_push_", "")
    await query.answer(f"🔄 正在推送...")

    try:
        # 获取媒体信息
        async with aiohttp.ClientSession() as session:
            url = (
                f"{EMBY_URL}/Items"
                f"?Ids={item_id}"
                f"&Fields=Path,Genres,Overview,OfficialRating,CommunityRating,MediaSources,ProductionYear"
            )
            async with session.get(url, headers=get_emby_headers(), ssl=False, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    await query.edit_message_text(f"❌ 连接 Emby 失败 (HTTP {resp.status})")
                    return
                data = await resp.json()

        if not data or not data.get("Items"):
            await query.edit_message_text("❌ 未找到该媒体")
            return

        item = data["Items"][0]
        item_id_internal = item.get('Id')

        # 获取详细信息
        details = await fetch_item_details(item_id_internal)
        if not details:
            details = item

        # 构建推送内容
        title = item.get('Name', '未知')
        year = item.get('ProductionYear', '????')
        rating = details.get('CommunityRating')
        rating_text = f"{rating:.1f}" if rating else "N/A"

        specs = get_video_specs(item, details)
        spec_tags = " | ".join([f"<code>{s}</code>" for s in specs])

        genres = details.get('Genres', [])
        genre_text = "/".join(genres[:2]) if genres else "未分类"

        poster_url = get_image_url(item_id_internal)

        caption = (
            f"💌 <b>Master... 馆藏更新啦！</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"🌸 <b>本周主打推荐：</b>\n"
            f"🎬 <b>《 {title} 》 ({year})</b>\n\n"
            f"✨ <b>视听规格鉴定：</b>\n"
            f"🏷️ {spec_tags} | ⭐ <code>{rating_text}分</code>\n"
            f"🍿 类型： <code>{genre_text}</code>\n\n"
            f"<i>「早就帮您准备好了最佳观影位...\n"
            f"那个... 要一起看吗？(⁄ ⁄•⁄ω⁄•⁄ ⁄)」</i>\n"
            f"━━━━━━━━━━━━━━\n"
            f"🎁 <b>观影小彩蛋：</b>\n"
            f"👇 <b>回复</b> 这条消息，领取今日份的魔力补给！"
        )

        # 下载海报并发送到群组
        photo_path = await download_image(poster_url) if poster_url else None

        if photo_path:
            with open(photo_path, 'rb') as f:
                push_msg = await context.bot.send_photo(
                    chat_id=Config.GROUP_ID,
                    photo=f,
                    caption=caption,
                    parse_mode='HTML'
                )
            try:
                os.unlink(photo_path)
            except:
                pass
        else:
            push_msg = await context.bot.send_message(
                chat_id=Config.GROUP_ID,
                text=caption,
                parse_mode='HTML'
            )

        # 注册到互动挖矿系统
        push_id = f"manual_{push_msg.message_id}_{int(datetime.now().timestamp())}"
        ACTIVE_PUSHES[push_msg.message_id] = {
            'chat_id': Config.GROUP_ID,
            'push_id': push_id,
            'claimed_users': set(),
            'created_at': datetime.now(),
            'is_manual_push': True
        }

        # 标记为已推送
        global pushed_items
        pushed_items.add(item_id_internal)
        save_pushed_item(item_id_internal)

        # 刷新列表
        await cmd_new_list(update, context)

    except Exception as e:
        logger.error(f"推送回调失败: {e}")
        await query.edit_message_text(f"❌ 推送失败: {str(e)}")


async def auto_emby_check(context: CallbackContext):
    """
    定时检查 Emby REMUX 电影入库，自动推送到群组
    每30分钟检查一次，只推送 REMUX 格式电影
    """
    if not EMBY_URL or not EMBY_API_KEY:
        logger.warning("Emby 配置不完整，跳过自动检查")
        return

    if not Config.GROUP_ID:
        logger.warning("未配置群组 ID，跳过自动推送")
        return

    global pushed_items

    try:
        # 获取最新电影
        items = await fetch_latest_items(limit=50, days=1)

        if not items:
            return

        new_push_count = 0

        for item in items:
            item_id = item.get('Id')
            if not item_id:
                continue

            # 跳过已推送的
            if item_id in pushed_items:
                continue

            details = await fetch_item_details(item_id)
            if not details:
                continue

            # 只推送 REMUX 格式
            if not is_remux(item, details):
                # 标记为已检查（避免重复检查非 REMUX）
                pushed_items.add(item_id)
                continue

            # 构建推送消息
            text_msg, poster_url = build_showcase_message(item, details)
            text_msg += (
                f"\n━━━━━━━━━━━━━━\n"
                f"✨ <b>互动有礼：</b>\n"
                f"👇 动动手指 <b>回复</b> 一下，试试看能爆出多少魔力？<i>(每人限领一次喵!)</i>"
            )

            try:
                # 下载海报并发送
                if poster_url:
                    photo_path = await download_image(poster_url)
                    if photo_path:
                        with open(photo_path, 'rb') as f:
                            push_msg = await context.bot.send_photo(
                                chat_id=Config.GROUP_ID,
                                photo=f,
                                caption=text_msg,
                                parse_mode='HTML'
                            )
                        try:
                            os.unlink(photo_path)
                        except:
                            pass
                    else:
                        push_msg = await context.bot.send_message(
                            chat_id=Config.GROUP_ID,
                            text=text_msg,
                            parse_mode='HTML'
                        )
                else:
                    push_msg = await context.bot.send_message(
                        chat_id=Config.GROUP_ID,
                        text=text_msg,
                        parse_mode='HTML'
                    )

                # 记录到 active_pushes 用于回复领奖（使用全局变量）
                push_id = f"emby_auto_{push_msg.message_id}_{int(datetime.now().timestamp())}"
                ACTIVE_PUSHES[push_msg.message_id] = {
                    'chat_id': Config.GROUP_ID,
                    'push_id': push_id,
                    'claimed_users': set(),
                    'created_at': datetime.now(),
                    'is_emby_push': True
                }

                # 标记为已推送（持久化到文件）
                pushed_items.add(item_id)
                save_pushed_item(item_id)
                new_push_count += 1
                logger.info(f"自动推送 REMUX 电影: {item.get('Name')} (ID: {item_id})")

            except Exception as e:
                logger.error(f"自动推送失败: {e}")

        if new_push_count > 0:
            logger.info(f"Emby 自动检查完成，推送了 {new_push_count} 部 REMUX 电影")

    except Exception as e:
        logger.error(f"Emby 自动检查出错: {e}")


def register(app):
    """注册命令处理器和定时任务"""
    # 注册命令
    app.add_handler(CommandHandler("emby_list", cmd_emby_list))
    app.add_handler(CommandHandler("new", cmd_new_list))
    # 通过 ID 手动推送（两个别名命令）
    app.add_handler(CommandHandler(["share", "pushid"], cmd_push_by_id))

    # 注册 Emby 推送按钮回调
    app.add_handler(CallbackQueryHandler(emby_push_callback, pattern="^emby_push_"))
    app.add_handler(CallbackQueryHandler(emby_push_callback, pattern="^emby_refresh_new$"))

    # 注册定时任务：每30分钟检查一次 REMUX 电影
    if EMBY_URL and EMBY_API_KEY:
        app.job_queue.run_repeating(auto_emby_check, interval=1800, first=10)
        logger.info("✨ Emby REMUX 电影自动推送任务已注册（每30分钟检查一次）")
