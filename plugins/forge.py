"""
魔法少女炼金系统 (Forge)
- 消耗 MP 锻造魔法武器，获得战力加成
- VIP 用户享受 5 折优惠
- 锻造后可选择是否装备新武器
- 全面正面反馈增强
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding
from utils import reply_with_auto_delete, edit_with_auto_delete
from plugins.feedback_utils import detailed_power_change, success_burst, get_rarity_effect, random_loading
from plugins.quotes import get_forge_success_quote, get_forge_fail_comfort, random_cute_emoji
from plugins.lucky_events import calculate_lucky_reward, check_random_drop
import random


# 导入活动追踪函数
async def track_activity_wrapper(user_id: int, activity_type: str):
    """包装函数，延迟导入避免循环依赖"""
    from plugins.unified_mission import track_and_check_task
    await track_and_check_task(user_id, activity_type)


# 词缀库：决定魔法武器的稀有度和名字
PREFIXES = [
    "破碎的", "生锈的", "练习用的", "普通的", "精良的",
    "稀有的", "史诗的", "传说的", "神话的", "被诅咒的",
    "真·", "极·", "终焉之", "创世的"
]
ELEMENTS = ["火焰", "冰霜", "雷霆", "暗影", "神圣", "虚空", "可爱", "用来做蛋糕的"]
TYPES = ["魔法杖", "魔导书", "法杖", "魔剑", "平底锅", "咸鱼", "魔法棒", "加特林", "圣剑"]


def _generate_weapon(boost_rarity=False, pity_counter=0):
    """生成随机魔法武器名称和战力

    Args:
        boost_rarity: 是否提升稀有度概率（大锻造锤）
        pity_counter: 保底计数（连续低品质次数）
    """
    # 保底系统：10次必出R+，30次必出SR+
    # 根据保底计算最低稀有度
    min_rarity = 0  # 0=任意, 1=精良以上, 2=稀有以上
    if pity_counter >= 30:
        min_rarity = 2  # 保证稀有的或更高
    elif pity_counter >= 10:
        min_rarity = 1  # 保证精良的或更高

    # 高稀有度模式：提升好词缀概率
    if boost_rarity:
        # SSR/神器概率调整 (降低)
        roll = random.random()
        if roll < 0.03:  # 3% 神器 (从15%降低)
            p = random.choice(["神话的", "终焉之", "创世的", "真·"])
        elif roll < 0.12:  # 9% 传说 (从25%降低)
            p = random.choice(["传说的", "极·"])
        elif roll < 0.32:  # 20% 史诗 (保持)
            p = random.choice(["史诗的", "稀有的"])
        elif roll < 0.87:  # 55% 普通 (从35%提升)
            p = random.choice(["精良的", "普通的", "练习用的"])
        else:  # 13% 咸鱼 (从5%提升)
            p = random.choice(["破碎的", "生锈的"])
    else:
        # 普通锻造（应用保底）
        if min_rarity >= 2:
            # 保底：稀有的或更高
            high_tier = ["稀有的", "史诗的", "传说的", "神话的", "真·", "极·", "终焉之", "创世的"]
            p = random.choice(high_tier)
        elif min_rarity >= 1:
            # 保底：精良的或更高
            mid_tier = ["精良的", "稀有的", "史诗的", "传说的", "神话的", "真·", "极·", "终焉之", "创世的"]
            p = random.choice(mid_tier)
        else:
            p = random.choice(PREFIXES)

    e = random.choice(ELEMENTS)
    t = random.choice(TYPES)
    name = f"{p}{e}{t}"

    # 战力计算
    base_atk = random.randint(10, 100)

    # 稀有度加成
    if "神话" in p or "终焉" in p or "创世" in p:
        base_atk += random.randint(500, 1000)
        rank = "🌈 <b>SSR (神器)</b>"
        rarity_tier = 3  # 最高
    elif "传说" in p or "真·" in p or "极·" in p:
        base_atk += random.randint(200, 500)
        rank = "🟡 <b>SR (史诗)</b>"
        rarity_tier = 2
    elif "稀有的" in p or "史诗的" in p:
        base_atk += random.randint(50, 150)
        rank = "🟣 <b>R+ (精锐)</b>"
        rarity_tier = 1
    elif "精良的" in p:
        base_atk += random.randint(20, 50)
        rank = "🔵 <b>R (精良)</b>"
        rarity_tier = 1
    elif "咸鱼" in t:
        base_atk = 1
        rank = "🐟 <b>咸鱼</b>"
        rarity_tier = 0
    else:
        rank = "⚪ <b>R (普通)</b>"
        rarity_tier = 0

    return name, base_atk, rank, rarity_tier


async def forge_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = getattr(update, "callback_query", None)
    msg = update.effective_message
    if not msg:
        return
    """开始锻造 - 第一步：扣费并生成武器"""
    msg = update.effective_message
    query = update.callback_query if hasattr(update, 'callback_query') and update.callback_query else None

    if not msg and not query:
        return

    user = query.from_user if query else update.effective_user
    user_id = user.id

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not u or not u.emby_account:
            target = query.edit_message_text if query else msg.reply_html
            await target("👻 <b>请先 /bind 缔结魔法契约喵！</b>", parse_mode='HTML')
            return

        # 检查锻造券
        has_big_ticket = u.free_forges_big and u.free_forges_big > 0
        has_small_ticket = (not has_big_ticket) and u.free_forges and u.free_forges > 0

        base_cost = 150  # 降低门槛，让新手更容易体验
        if has_big_ticket:
            cost = 0  # 大锻造锤免费
            boost_rarity = True
            used_ticket = "大锻造锤"
        elif has_small_ticket:
            cost = 0  # 小锻造锤免费
            boost_rarity = False
            used_ticket = "小锻造锤"
        else:
            cost = int(base_cost * 0.5) if u.is_vip else base_cost
            boost_rarity = False
            used_ticket = None

        if not used_ticket and u.points < cost:
            points = u.points
            is_vip = u.is_vip
            if is_vip:
                text = (
                    f"⚒️ <b>【 皇 家 · 炼 金 工 坊 】</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🔥 <b>魔法炉火熄灭了...</b>\n\n"
                    f"魔力不足喵！锻造需要 <b>{cost} MP</b>~\n"
                    f"当前余额：{points} MP\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"<i>\"去签到攒点魔力再来吧 Master...(｡•́︿•̀｡)\"</i>"
                )
            else:
                text = (
                    f"⚒️ <b>【 魔 法 学 院 · 炼 金 工 坊 】</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🔥 <b>魔法炉火熄灭了...</b>\n\n"
                    f"魔力不足喵！锻造需要 <b>{cost} MP</b>~\n"
                    f"当前余额：{points} MP\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"<i>💡 提示：VIP 锻造享受 <b>5 折</b> 优惠哦！</i>"
                )
            target = query.edit_message_text if query else msg.reply_html
            await target(text, parse_mode='HTML')
            return

        # 初始化保底相关变量
        pity_text = ""
        pity_next = 0
        pity_reset = False

        # 扣除费用或券
        if used_ticket == "大锻造锤":
            u.free_forges_big -= 1
            remaining = u.free_forges_big
        elif used_ticket == "小锻造锤":
            u.free_forges -= 1
            remaining = u.free_forges
        else:
            u.points -= cost
            remaining = 0

        # 获取保底计数
        pity_counter = u.forge_pity_counter or 0

        # 生成魔法武器（应用保底）
        new_name, base_atk, rank, rarity_tier = _generate_weapon(boost_rarity=boost_rarity, pity_counter=pity_counter)

        # 更新保底计数
        if rarity_tier >= 1:  # R 精良或以上
            u.forge_pity_counter = 0  # 重置计数
            pity_reset = True
            pity_next = 0
        else:
            u.forge_pity_counter = (u.forge_pity_counter or 0) + 1
            pity_next = u.forge_pity_counter

        # 保存临时数据到 bot_data (用于回调时获取)
        import uuid
        forge_id = str(uuid.uuid4())[:8]
        if not context.bot_data:
            context.bot_data = {}
        if "forge_temp" not in context.bot_data:
            context.bot_data["forge_temp"] = {}

        context.bot_data["forge_temp"][forge_id] = {
            "new_name": new_name,
            "base_atk": base_atk,
            "rank": rank,
            "used_ticket": used_ticket,
            "cost": cost,
            "remaining": remaining,
            "boost_rarity": boost_rarity,
            "rarity_tier": rarity_tier,
        }

        session.commit()

        # 获取用户信息
        vip_badge = " 👑" if u.is_vip else ""
        emby_account = u.emby_account
        old_weapon = u.weapon if u.weapon else "无"
        old_atk = u.attack if u.attack else 0

    # 构建消耗文本
    if used_ticket:
        if used_ticket == "大锻造锤":
            cost_text = f"🎟️ 消耗：<b>{used_ticket}</b> (稀有度UP!)\n"
        else:
            cost_text = f"🎟️ 消耗：<b>{used_ticket}</b>\n"
        if remaining > 0:
            cost_text += f"📋 剩余券数：{remaining} 张\n"
    else:
        cost_text = f"🔥 消耗魔力：<b>-{cost} MP</b>\n"

    # 保底显示
    pity_text = ""
    if pity_reset:
        pity_text = f"🎉 <b>保底触发已重置！</b>\n"
    elif pity_next >= 5:
        pity_text = f"📊 <b>保底计数：</b> {pity_next}/10 (R+)\n"
    elif pity_next >= 8:
        pity_text = f"📊 <b>保底计数：</b> {pity_next}/10 (R+)\n"

    # 战力对比
    atk_diff = base_atk - old_atk
    if atk_diff > 0:
        atk_compare = f"📈 <b>战力变化：</b> +{atk_diff} ▲"
    elif atk_diff < 0:
        atk_compare = f"📉 <b>战力变化：</b> {atk_diff} ▼"
    else:
        atk_compare = f"➡️ <b>战力变化：</b> 持平"

    # 计算稀有度特效
    if "SSR" in rank or "神器" in rank:
        rarity_effect = get_rarity_effect("SSR")
        title = f"⚒️🔥 【 锻 造 完 成 】🔥⚒️"
    elif "SR" in rank or "史诗" in rank:
        rarity_effect = get_rarity_effect("SR")
        title = f"⚒️✨ 【 锻 造 完 成 】✨⚒️"
    else:
        rarity_effect = ""
        title = f"⚒️ <b>【 锻 造 完 成 】</b>"

    # 战力对比（详细版）
    if atk_diff > 0:
        bolts = "⚡" * min(5, 1 + atk_diff // 50)
        power_detail = f"📈⬆️ 战力提升：+{atk_diff} {bolts}"
    elif atk_diff < 0:
        power_detail = f"📉⬇️ 战力变化：{atk_diff}"
    else:
        power_detail = f"➡️ 战力持平"

    txt = (
        f"{title}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{cost_text}"
        f"👤 锻造者：{emby_account}{vip_badge}\n"
        f"{pity_text}"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗡️ <b>当前装备：</b> {old_weapon} (ATK: {old_atk})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{rarity_effect}\n"
        f"✨ <b>新锻造武器：</b> <b>{new_name}</b>\n"
        f"📊 <b>武器评级：</b> {rank}\n"
        f"⚔️ <b>战力评估：</b> <b>{base_atk}</b>\n"
        f"{power_detail}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>是否要装备这把新武器？{random_cute_emoji()}</i>"
    )

    buttons = [
        [
            InlineKeyboardButton("✅ 装备", callback_data=f"forge_equip_{forge_id}"),
            InlineKeyboardButton("❌ 丢弃", callback_data=f"forge_discard_{forge_id}")
        ]
    ]

    if query:
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
    else:
        await msg.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))


async def forge_result_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理锻造结果选择回调"""
    query = update.callback_query
    await query.answer()

    # 解析回调数据
    data = query.data
    parts = data.split('_')
    action = parts[1]  # equip 或 discard
    forge_id = parts[2]  # 8位ID

    user = query.from_user

    # 获取临时数据
    if not context.bot_data or "forge_temp" not in context.bot_data:
        await query.edit_message_text("⚠️ <b>锻造数据已过期</b>", parse_mode='HTML')
        return

    forge_data = context.bot_data["forge_temp"].get(forge_id)
    if not forge_data:
        await query.edit_message_text("⚠️ <b>锻造数据已过期</b>", parse_mode='HTML')
        return

    new_name = forge_data["new_name"]
    base_atk = forge_data["base_atk"]
    rank = forge_data["rank"]
    used_ticket = forge_data["used_ticket"]
    cost = forge_data["cost"]
    remaining = forge_data["remaining"]

    # 清理临时数据
    context.bot_data["forge_temp"].pop(forge_id, None)

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user.id).first()

        if not u:
            await query.edit_message_text("👻 <b>用户不存在</b>", parse_mode='HTML')
            return

        old_weapon = u.weapon if u.weapon else "无"
        old_atk = u.attack if u.attack else 0

        if action == "equip":
            # 装备新武器
            u.weapon = new_name
            u.attack = base_atk
            await track_activity_wrapper(user.id, "forge")

            # [新增] 自动收藏高稀有度武器 (SR及以上)
            collection_msg = ""
            if rarity_tier >= 2:  # SR 或 SSR
                # 添加到收藏
                current_collection = u.weapon_collection if u.weapon_collection else ""
                if current_collection:
                    u.weapon_collection = current_collection + "," + new_name
                else:
                    u.weapon_collection = new_name

                if rarity_tier == 3:  # SSR
                    collection_msg = "\n🏆 <b>已自动收藏到武器馆！</b>"
                else:  # SR
                    collection_msg = "\n✨ <b>已收藏到武器馆</b>"

            # [新增] 检查战力成就
            achievement_msgs = []
            from plugins.achievement import check_and_award_achievement
            for ach_id in ["power_100", "power_500", "power_1000", "power_5000", "power_10000"]:
                result = check_and_award_achievement(u, ach_id, session)
                if result["new"]:
                    achievement_msgs.append(f"🎉 {result['emoji']} {result['name']} (+{result['reward']}MP)")

            session.commit()

            vip_badge = " 👑" if u.is_vip else ""
            emby_account = u.emby_account

            atk_diff = base_atk - old_atk

            # === 正面反馈增强 ===
            # 根据稀有度和战力变化生成特效
            is_high_rarity = "SSR" in rank or "SR" in rank or "神器" in rank or "史诗" in rank
            is_power_up = atk_diff > 0

            if is_high_rarity:
                title_effect = f"✅🔥 【 装 备 成 功 】🔥✅"
                success_anim = success_burst(3)
            else:
                title_effect = f"✅ <b>【 装 备 成 功 】</b>"
                success_anim = success_burst(2)

            # 战力变化详细显示
            if atk_diff > 0:
                bolts = "⚡" * min(5, 1 + atk_diff // 50)
                result_lines = [
                    f"📊 战力变化：",
                    f"   旧战力：{old_atk} ⬇️",
                    f"   新战力：{base_atk} ⬆️",
                    f"   🚀 提升：+{atk_diff} {bolts}"
                ]
            elif atk_diff < 0:
                result_lines = [
                    f"📊 战力变化：",
                    f"   旧战力：{old_atk} ⬆️",
                    f"   新战力：{base_atk} ⬇️",
                    f"   📉 变化：{atk_diff}"
                ]
            else:
                result_lines = [f"➡️ 战力持平"]

            # 获取祝贺台词
            if is_high_rarity and atk_diff > 0:
                quote = get_forge_success_quote(emby_account, rank)
            else:
                quote = f"\"新武器感觉怎么样？{random_cute_emoji()}\""

            # 成就消息
            achievement_text = ""
            if achievement_msgs:
                achievement_text = "\n" + "\n".join(achievement_msgs) + "\n"

            txt = (
                f"{title_effect}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{success_anim}\n"
                f"👤 {emby_account}{vip_badge}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🗑️ <b>已卸下：</b> {old_weapon} (ATK: {old_atk})\n"
                f"✨ <b>已装备：</b> <b>{new_name}</b>\n"
                f"📊 <b>评级：</b> {rank}\n"
                f"⚔️ <b>战力：</b> <b>{base_atk}</b>\n"
                f"\n"
                f"\n".join(result_lines) + "\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{achievement_text}"
                f"{collection_msg}\n"
                f"<i>{quote}</i>"
            )
        else:  # discard
            # 保留旧武器，新武器丢弃
            vip_badge = " 👑" if u.is_vip else ""

            txt = (
                f"🗑️ <b>【 已 选 择 保 留 旧 武 器 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🗡️ <b>当前装备：</b> {old_weapon} (ATK: {old_atk})\n"
                f"🗑️ <b>已丢弃：</b> {new_name} (ATK: {base_atk})\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>\"继续锻造吧 Master！(｡•̀ᴗ-)✧\"</i>"
            )

    buttons = [[InlineKeyboardButton("🔄 继续锻造", callback_data="forge_start")]]

    await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')


async def my_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看当前装备"""
    msg = update.effective_message
    if not msg:
        return

    user = update.effective_user

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user.id).first()

        if not u or not u.emby_account:
            await reply_for_callback(update, "👻 <b>请先 /bind 缔结魔法契约喵！</b>")
            return

        weapon = u.weapon if u.weapon else "赤手空拳"
        attack = u.attack if u.attack else 10
        is_vip = u.is_vip
        emby_account = u.emby_account

    vip_badge = " 👑" if is_vip else ""

    txt = (
        f"⚔️ <b>【 魔 法 武 器 栏 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>持有者：</b> {emby_account}{vip_badge}\n"
        f"🗡️ <b>当前武器：</b> <b>{weapon}</b>\n"
        f"💪 <b>战力评估：</b> <b>{attack}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"使用 /forge 可以锻造新武器哦喵~(｡•̀ᴗ-)✧\"</i>"
    )

    await reply_with_auto_delete(msg, txt)


async def weapon_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看武器收藏"""
    msg = update.effective_message
    query = getattr(update, "callback_query", None)

    if not msg and not query:
        return

    user_id = update.effective_user.id

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not u or not u.emby_account:
            target = query.edit_message_text if query else msg.reply_html
            await target("💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        # 获取收藏的武器
        raw_collection = u.weapon_collection if u.weapon_collection else ""

        if not raw_collection.strip():
            collection_display = "🍃 <i>还没有收藏任何武器...\n去锻造一些精品武器吧喵~(｡･ω･｡)</i>"
        else:
            # 解析收藏列表
            weapons = raw_collection.split(",") if raw_collection else []
            # 按稀有度排序
            from collections import Counter
            weapon_counts = Counter(weapons)

            # 按稀有度分组
            rarity_groups = {
                "🌈": [],  # SSR 神器
                "🟡": [],  # SR 史诗
                "🟣": [],  # R+ 精锐
                "🔵": [],  # R 精良
                "⚪": [],  # R 普通
            }

            for weapon_name, count in weapon_counts.items():
                # 判断稀有度
                if any(k in weapon_name for k in ["神话", "终焉", "创世"]):
                    rarity_groups["🌈"].append((weapon_name, count))
                elif any(k in weapon_name for k in ["传说", "真·", "极·"]):
                    rarity_groups["🟡"].append((weapon_name, count))
                elif any(k in weapon_name for k in ["稀有的", "史诗的"]):
                    rarity_groups["🟣"].append((weapon_name, count))
                elif "精良的" in weapon_name:
                    rarity_groups["🔵"].append((weapon_name, count))
                else:
                    rarity_groups["⚪"].append((weapon_name, count))

            # 构建显示文本
            collection_display = ""
            for emoji, group in rarity_groups.items():
                if group:
                    collection_display += f"\n{emoji} <b>"
                    if emoji == "🌈":
                        collection_display += "SSR 神器</b>："
                    elif emoji == "🟡":
                        collection_display += "SR 史诗</b>："
                    elif emoji == "🟣":
                        collection_display += "R+ 精锐</b>："
                    elif emoji == "🔵":
                        collection_display += "R 精良</b>："
                    else:
                        collection_display += "R 普通</b>："

                    # 最多显示3个
                    if len(group) > 3:
                        display_items = group[:3]
                        collection_display += f" {', '.join([f'{n}×{c}' for n, c in display_items])} 等{len(group)}种"
                    else:
                        collection_display += f" {', '.join([f'{n}×{c}' for n, c in group])}"

        vip_badge = " 👑" if u.is_vip else ""

        txt = (
            f"🏆 <b>【 武 器 收 藏 馆 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>{u.emby_account}</b>{vip_badge}\n"
            f"📊 收藏数：{len(raw_collection.split(',')) if raw_collection else 0} 件\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{collection_display}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>\"💡 SR及以上稀有度武器会自动收藏哦~\"</i>"
        )

        buttons = [[InlineKeyboardButton("🔙 返回", callback_data="collection_back")]]

        if query:
            await query.edit_message_text(
                txt,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode='HTML'
            )
        else:
            await msg.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))


async def collection_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """返回收藏界面"""
    query = update.callback_query
    await query.answer()
    await weapon_collection(update, context)


def register(app):
    """注册插件处理器"""
    app.add_handler(CommandHandler("forge", forge_start))
    app.add_handler(CommandHandler("weapon", forge_start))
    app.add_handler(CommandHandler("myweapon", my_weapon))
    app.add_handler(CommandHandler("collection", weapon_collection))
    app.add_handler(CommandHandler("weapon_collection", weapon_collection))
    # 锻造回调
    app.add_handler(CallbackQueryHandler(forge_start, pattern="^forge_start$"))
    app.add_handler(CallbackQueryHandler(forge_result_callback, pattern=r"^forge_(equip|discard)_.{8}$"))
    app.add_handler(CallbackQueryHandler(collection_back_callback, pattern="^collection_back$"))
