"""
魔法商店系统 - 魔法少女版
- 购买各种道具和增益效果
- VIP 用户享受折扣优惠
- 支持参数购买和按钮购买
- 部分商品每日限购
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_session, UserBinding
from utils import reply_with_auto_delete, edit_with_auto_delete
from datetime import datetime, date
import random


# ==========================================
# 任务追踪包装函数
# ==========================================
async def track_activity_wrapper(user_id: int, activity_type: str):
    """包装函数，延迟导入避免循环依赖"""
    from plugins.unified_mission import track_and_check_task
    await track_and_check_task(user_id, activity_type)


# 辅助函数：获取今日日期（用于每日限购重置）
def get_today():
    """获取今日日期，用于每日重置判断"""
    return datetime.now().date()


def get_box_limit_status(user: UserBinding) -> tuple:
    """
    获取用户神秘宝箱限购状态
    返回：(今日已购买次数, 今日剩余次数, 是否需要重置)
    """
    today = get_today()
    need_reset = False

    # 检查是否需要重置（跨天）
    if user.last_box_buy_date:
        last_date = user.last_box_buy_date.date() if isinstance(user.last_box_buy_date, datetime) else user.last_box_buy_date
        if last_date < today:
            need_reset = True

    return user.daily_box_buy_count or 0, need_reset


# 商店商品配置
SHOP_ITEMS = {
    "tarot": {
        "name": "🔮 塔罗占卜券",
        "desc": "额外一次塔罗占卜机会",
        "price": 50,
        "vip_price": 25,
        "emoji": "🔮"
    },
    "gacha": {
        "name": "🎰 盲盒券",
        "desc": "抽取一次魔法盲盒",
        "price": 100,
        "vip_price": 50,
        "emoji": "🎰"
    },
    "forge_small": {
        "name": "⚒️ 锻造锤(小)",
        "desc": "免费锻造一次(普通价100MP)",
        "price": 50,
        "vip_price": 25,
        "emoji": "⚒️"
    },
    "forge_big": {
        "name": "⚒️ 锻造锤(大)",
        "desc": "免费锻造一次+高稀有度概率UP",
        "price": 500,
        "vip_price": 250,
        "emoji": "⚒️"
    },
    "lucky": {
        "name": "🍀 幸运草",
        "desc": "下次签到暴击率+50%",
        "price": 30,
        "vip_price": 15,
        "emoji": "🍀"
    },
    "energy": {
        "name": "⚡ 能量药水",
        "desc": "恢复300MP(净赚150)",
        "price": 150,
        "vip_price": 75,
        "emoji": "⚡"
    },
    "shield": {
        "name": "🛡️ 防御卷轴",
        "desc": "下次决斗失败不掉钱",
        "price": 80,
        "vip_price": 40,
        "emoji": "🛡️"
    },
    "box": {
        "name": "🎁 神秘宝箱",
        "desc": "随机开出100-300MP",
        "price": 100,
        "vip_price": 50,
        "emoji": "🎁",
        "daily_limit": 5  # 每日限购5次（普通用户3次，VIP5次）
    },
}


async def shop_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示商店主页"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not u or not u.emby_account:
            await reply_with_auto_delete(
                msg,
                "💔 <b>请先绑定账号喵！</b>\n\n"
                "使用 <code>/bind 账号</code> 绑定后再购物~"
            )
            return

        vip_badge = " 👑" if u.is_vip else ""
        discount = "5折" if u.is_vip else "原价"

        txt = (
            f"🛒 <b>【 魔 法 · 商 店 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>客人：</b> {u.emby_account}{vip_badge}\n"
            f"💎 <b>钱包：</b> {u.points} MP\n"
            f"🏷️ <b>折扣：</b> {discount}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📜 <b>使用 /buy 商品名 购买商品</b>\n"
            f"💡 <b>或点击下方按钮购买</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )

        # 构建商品列表
        shop_list = ""
        for item_id, item in SHOP_ITEMS.items():
            price = item["vip_price"] if u.is_vip else item["price"]
            line = f"{item['emoji']} <b>{item['name']}</b> — <b>{price} MP</b>"

            # 神秘宝箱显示限购信息
            if item_id == "box":
                bought_count, need_reset = get_box_limit_status(u)
                if need_reset:
                    bought_count = 0
                limit = 5 if u.is_vip else 3
                remaining = max(0, limit - bought_count)
                if remaining > 0:
                    line += f" <i>(今日可购 {remaining}/{limit})</i>"
                else:
                    line += f" <i>(今日已达上限)</i>"

            shop_list += line + "\n"

        txt += f"\n📦 <b>今日商品：</b>\n{shop_list}"
        txt += "\n━━━━━━━━━━━━━━━━━━\n"
        txt += "<i>\"欢迎光临！这里有你需要的所有魔法道具喵~(｡•̀ᴗ-)✧\"</i>"

        # 构建按钮
        buttons = []
        row = []
        for i, (item_id, item) in enumerate(SHOP_ITEMS.items()):
            price = item["vip_price"] if u.is_vip else item["price"]
            row.append(InlineKeyboardButton(f"{item['emoji']} {price}MP", callback_data=f"buy_{item_id}"))
            if len(row) == 2 or i == len(SHOP_ITEMS) - 1:
                buttons.append(row)
                row = []

    await msg.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))


async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str = None):
    """购买商品"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not u or not u.emby_account:
            await reply_with_auto_delete(
                msg,
                "💔 <b>请先绑定账号喵！</b>\n\n"
                "使用 <code>/bind 账号</code> 绑定后再购物~"
            )
            return

        # 从参数获取商品ID
        if not item_id and context.args:
            item_id = context.args[0].lower()

        if not item_id or item_id not in SHOP_ITEMS:
            items_list = ", ".join(SHOP_ITEMS.keys())
            await reply_with_auto_delete(
                msg,
                f"🛒 <b>【 商 店 】</b>\n\n"
                f"❓ 找不到这个商品喵~\n\n"
                f"📜 <b>可用商品：</b>\n"
                f"{items_list}\n\n"
                f"💡 使用 <code>/buy 商品名</code> 购买\n"
                f"或使用 <code>/shop</code> 查看商品列表"
            )
            return

        item = SHOP_ITEMS[item_id]
        price = item["vip_price"] if u.is_vip else item["price"]

        # 检查神秘宝箱限购
        if item_id == "box":
            bought_count, need_reset = get_box_limit_status(u)
            if need_reset:
                # 跨天了，重置计数
                u.daily_box_buy_count = 0
                bought_count = 0

            limit = 5 if u.is_vip else 3
            if bought_count >= limit:
                await reply_with_auto_delete(
                    msg,
                    f"🚫 <b>【 限 购 提 示 】</b>\n\n"
                    f"今日购买神秘宝箱已达上限喵~\n\n"
                    f"📊 <b>购买记录：</b> {bought_count}/{limit} 次\n"
                    f"{'👑 VIP 用户每日限购 5 次' if u.is_vip else '🌱 普通用户每日限购 3 次'}\n\n"
                    f"<i>\"明天再来碰运气吧！(｡･ω･｡)ﾉ♡\"</i>"
                )
                return

        if u.points < price:
            await reply_with_auto_delete(
                msg,
                f"💸 <b>【 魔 力 不 足 】</b>\n\n"
                f"钱包里只有 <b>{u.points} MP</b>\n"
                f"购买 {item['name']} 需要 <b>{price} MP</b> 喵~"
            )
            return

        # 扣除费用
        u.points -= price

        # 处理商品效果
        result_msg = ""
        if item_id == "energy":
            # 能量药水：直接获得300MP (从200提升)
            gain = 300
            u.points += gain
            result_msg = f"⚡ <b>获得 300 MP！(净赚150)</b>"

        elif item_id == "box":
            # 神秘宝箱：多种稀有度掉落
            # 稀有度: 普通75%, 稀有18%, 史诗5%, 传说1.5%, 神话0.5%
            roll = random.random() * 100
            rarity = ""
            rewards = []

            # 神话 (0.5%)
            if roll < 0.5:
                rarity = "🌸 神话"
                mythic_rewards = [
                    ("MP", random.randint(2000, 5000), "💎"),
                    ("free_forge_big", 2, "⚒️"),
                    ("extra_gacha", 5, "🎰"),
                ]
                rewards = [random.choice(mythic_rewards)]
            # 传说 (1.5%)
            elif roll < 2:
                rarity = "🌟 传说"
                legendary_rewards = [
                    ("MP", random.randint(800, 1500), "💎"),
                    ("free_forge_big", 1, "⚒️"),
                    ("extra_gacha", 3, "🎰"),
                    ("extra_tarot", 3, "🔮"),
                ]
                rewards = [random.choice(legendary_rewards)]
            # 史诗 (5%)
            elif roll < 7:
                rarity = "🟣 史诗"
                epic_rewards = [
                    ("MP", random.randint(300, 600), "💰"),
                    ("lucky_boost", 1, "🍀"),
                    ("shield_active", 1, "🛡️"),
                    ("extra_gacha", 2, "🎰"),
                    ("extra_tarot", 2, "🔮"),
                    ("free_forge_big", 1, "⚒️"),
                ]
                rewards = [random.choice(epic_rewards)]
            # 稀有 (18%)
            elif roll < 25:
                rarity = "🔵 稀有"
                rare_rewards = [
                    ("MP", random.randint(150, 300), "💰"),
                    ("extra_tarot", 1, "🔮"),
                    ("extra_gacha", 1, "🎰"),
                    ("free_forge_small", 1, "⚒️"),
                ]
                rewards = [random.choice(rare_rewards)]
            # 普通 (75%)
            else:
                rarity = "⚪ 普通"
                common_rewards = [
                    ("MP", random.randint(80, 150), "💰"),
                ]
                rewards = [random.choice(common_rewards)]

            # 发放奖励
            reward_texts = []
            for reward_type, amount, emoji in rewards:
                if reward_type == "MP":
                    u.points += amount
                    reward_texts.append(f"{emoji} {amount} MP")
                elif reward_type == "lucky_boost":
                    u.lucky_boost = True
                    reward_texts.append(f"{emoji} 幸运草")
                elif reward_type == "shield_active":
                    u.shield_active = True
                    reward_texts.append(f"{emoji} 防御卷轴")
                elif reward_type == "extra_tarot":
                    u.extra_tarot = (u.extra_tarot or 0) + amount
                    reward_texts.append(f"{emoji} 塔罗券×{amount}")
                elif reward_type == "extra_gacha":
                    u.extra_gacha = (u.extra_gacha or 0) + amount
                    reward_texts.append(f"{emoji} 盲盒券×{amount}")
                elif reward_type == "free_forge_small":
                    u.free_forges = (u.free_forges or 0) + amount
                    reward_texts.append(f"{emoji} 锻造锤(小)")
                elif reward_type == "free_forge_big":
                    u.free_forges_big = (u.free_forges_big or 0) + amount
                    reward_texts.append(f"{emoji} 锻造锤(大)")

            result_msg = f"{rarity}\n🎁 <b>获得：{', '.join(reward_texts)}</b>"
            # 更新限购计数
            u.daily_box_buy_count = (u.daily_box_buy_count or 0) + 1
            u.last_box_buy_date = datetime.now()
            limit = 5 if u.is_vip else 3
            remaining = limit - u.daily_box_buy_count
            if remaining > 0:
                result_msg += f"\n\n📊 <i>今日还可购买 {remaining}/{limit} 次</i>"
            else:
                result_msg += f"\n\n📊 <i>今日购买次数已用完</i>"

        elif item_id == "lucky":
            # 幸运草：设置幸运标记
            u.lucky_boost = True
            result_msg = "🍀 <b>下次签到暴击率+50%！</b>"

        elif item_id == "shield":
            # 防护卷轴：设置防护标记
            u.shield_active = True
            result_msg = "🛡️ <b>下次决斗失败不掉钱！</b>"

        elif item_id == "tarot":
            # 塔罗券：增加塔罗次数
            u.extra_tarot = (u.extra_tarot or 0) + 1
            result_msg = "🔮 <b>获得一次额外塔罗占卜！</b>"

        elif item_id == "gacha":
            # 盲盒券：增加盲盒次数
            u.extra_gacha = (u.extra_gacha or 0) + 1
            result_msg = "🎰 <b>获得一次额外盲盒抽取！</b>"

        elif item_id == "forge_small":
            # 小锻造锤：免费锻造
            u.free_forges = (u.free_forges or 0) + 1
            result_msg = "⚒️ <b>获得一张免费锻造券！</b>"

        elif item_id == "forge_big":
            # 大锻造锤：免费锻造+高稀有度
            u.free_forges_big = (u.free_forges_big or 0) + 1
            result_msg = "⚒️ <b>获得高级锻造券(稀有度UP)！</b>"

        session.commit()

        # 追踪任务进度
        await track_activity_wrapper(user_id, "shop")

        # 在关闭session前保存需要的值
        user_account = u.emby_account
        is_vip = u.is_vip
        remaining_points = u.points

    vip_badge = " 👑" if is_vip else ""

    txt = (
        f"🛒 <b>【 购 买 成 功 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>客人：</b> {user_account}{vip_badge}\n"
        f"✨ <b>购买：</b> {item['name']}\n"
        f"💸 <b>花费：</b> {price} MP\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{result_msg}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>剩余魔力：</b> {remaining_points} MP\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"感谢惠顾！期待您的下次光临喵~(｡•̀ᴗ-)✧\"</i>"
    )

    # 购买成功消息不自动删除，让用户看到结果
    await msg.reply_html(txt)


async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理商店按钮回调"""
    query = update.callback_query
    await query.answer()

    # 解析商品ID
    item_id = query.data.replace("buy_", "")

    user_id = query.from_user.id

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not u or not u.emby_account:
            await edit_with_auto_delete(query, "💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        if item_id not in SHOP_ITEMS:
            await edit_with_auto_delete(query, "❓ <b>商品不存在喵~</b>", parse_mode='HTML')
            return

        item = SHOP_ITEMS[item_id]
        price = item["vip_price"] if u.is_vip else item["price"]

        # 检查神秘宝箱限购
        if item_id == "box":
            bought_count, need_reset = get_box_limit_status(u)
            if need_reset:
                # 跨天了，重置计数
                u.daily_box_buy_count = 0
                bought_count = 0

            limit = 5 if u.is_vip else 3
            if bought_count >= limit:
                await edit_with_auto_delete(
                    query,
                    f"🚫 <b>【 限 购 提 示 】</b>\n\n"
                    f"今日购买神秘宝箱已达上限喵~\n\n"
                    f"📊 <b>购买记录：</b> {bought_count}/{limit} 次\n"
                    f"{'👑 VIP 用户每日限购 5 次' if u.is_vip else '🌱 普通用户每日限购 3 次'}\n\n"
                    f"<i>\"明天再来碰运气吧！(｡･ω･｡)ﾉ♡\"</i>",
                    parse_mode='HTML'
                )
                return

        if u.points < price:
            await edit_with_auto_delete(
                query,
                f"💸 <b>【 魔 力 不 足 】</b>\n\n"
                f"钱包里只有 <b>{u.points} MP</b>\n"
                f"购买 {item['name']} 需要 <b>{price} MP</b> 喵~",
                parse_mode='HTML'
            )
            return

        # 扣除费用
        u.points -= price

        # 处理商品效果
        result_msg = ""
        if item_id == "energy":
            gain = 300
            u.points += gain
            result_msg = f"⚡ <b>获得 300 MP！(净赚150)</b>"
        elif item_id == "box":
            # 神秘宝箱：多种稀有度掉落
            # 稀有度: 普通75%, 稀有18%, 史诗5%, 传说1.5%, 神话0.5%
            roll = random.random() * 100
            rarity = ""
            rewards = []

            # 神话 (0.5%)
            if roll < 0.5:
                rarity = "🌸 神话"
                mythic_rewards = [
                    ("MP", random.randint(2000, 5000), "💎"),
                    ("free_forge_big", 2, "⚒️"),
                    ("extra_gacha", 5, "🎰"),
                ]
                rewards = [random.choice(mythic_rewards)]
            # 传说 (1.5%)
            elif roll < 2:
                rarity = "🌟 传说"
                legendary_rewards = [
                    ("MP", random.randint(800, 1500), "💎"),
                    ("free_forge_big", 1, "⚒️"),
                    ("extra_gacha", 3, "🎰"),
                    ("extra_tarot", 3, "🔮"),
                ]
                rewards = [random.choice(legendary_rewards)]
            # 史诗 (5%)
            elif roll < 7:
                rarity = "🟣 史诗"
                epic_rewards = [
                    ("MP", random.randint(300, 600), "💰"),
                    ("lucky_boost", 1, "🍀"),
                    ("shield_active", 1, "🛡️"),
                    ("extra_gacha", 2, "🎰"),
                    ("extra_tarot", 2, "🔮"),
                    ("free_forge_big", 1, "⚒️"),
                ]
                rewards = [random.choice(epic_rewards)]
            # 稀有 (18%)
            elif roll < 25:
                rarity = "🔵 稀有"
                rare_rewards = [
                    ("MP", random.randint(150, 300), "💰"),
                    ("extra_tarot", 1, "🔮"),
                    ("extra_gacha", 1, "🎰"),
                    ("free_forge_small", 1, "⚒️"),
                ]
                rewards = [random.choice(rare_rewards)]
            # 普通 (75%)
            else:
                rarity = "⚪ 普通"
                common_rewards = [
                    ("MP", random.randint(80, 150), "💰"),
                ]
                rewards = [random.choice(common_rewards)]

            # 发放奖励
            reward_texts = []
            for reward_type, amount, emoji in rewards:
                if reward_type == "MP":
                    u.points += amount
                    reward_texts.append(f"{emoji} {amount} MP")
                elif reward_type == "lucky_boost":
                    u.lucky_boost = True
                    reward_texts.append(f"{emoji} 幸运草")
                elif reward_type == "shield_active":
                    u.shield_active = True
                    reward_texts.append(f"{emoji} 防御卷轴")
                elif reward_type == "extra_tarot":
                    u.extra_tarot = (u.extra_tarot or 0) + amount
                    reward_texts.append(f"{emoji} 塔罗券×{amount}")
                elif reward_type == "extra_gacha":
                    u.extra_gacha = (u.extra_gacha or 0) + amount
                    reward_texts.append(f"{emoji} 盲盒券×{amount}")
                elif reward_type == "free_forge_small":
                    u.free_forges = (u.free_forges or 0) + amount
                    reward_texts.append(f"{emoji} 锻造锤(小)")
                elif reward_type == "free_forge_big":
                    u.free_forges_big = (u.free_forges_big or 0) + amount
                    reward_texts.append(f"{emoji} 锻造锤(大)")

            result_msg = f"{rarity}\n🎁 <b>获得：{', '.join(reward_texts)}</b>"
            # 更新限购计数
            u.daily_box_buy_count = (u.daily_box_buy_count or 0) + 1
            u.last_box_buy_date = datetime.now()
            limit = 5 if u.is_vip else 3
            remaining = limit - u.daily_box_buy_count
            if remaining > 0:
                result_msg += f"\n\n📊 <i>今日还可购买 {remaining}/{limit} 次</i>"
            else:
                result_msg += f"\n\n📊 <i>今日购买次数已用完</i>"
        elif item_id == "lucky":
            u.lucky_boost = True
            result_msg = "🍀 <b>下次签到暴击率+50%！</b>"
        elif item_id == "shield":
            u.shield_active = True
            result_msg = "🛡️ <b>下次决斗失败不掉钱！</b>"
        elif item_id == "tarot":
            u.extra_tarot = (u.extra_tarot or 0) + 1
            result_msg = "🔮 <b>获得一次额外塔罗占卜！</b>"
        elif item_id == "gacha":
            u.extra_gacha = (u.extra_gacha or 0) + 1
            result_msg = "🎰 <b>获得一次额外盲盒抽取！</b>"
        elif item_id == "forge_small":
            u.free_forges = (u.free_forges or 0) + 1
            result_msg = "⚒️ <b>获得一张免费锻造券！</b>"
        elif item_id == "forge_big":
            u.free_forges_big = (u.free_forges_big or 0) + 1
            result_msg = "⚒️ <b>获得高级锻造券(稀有度UP)！</b>"

        session.commit()

        # 追踪任务进度
        await track_activity_wrapper(user_id, "shop")

        # 在session关闭前保存需要的值
        user_account = u.emby_account
        is_vip = u.is_vip
        remaining_points = u.points

    vip_badge = " 👑" if is_vip else ""

    txt = (
        f"🛒 <b>【 购 买 成 功 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>客人：</b> {user_account}{vip_badge}\n"
        f"✨ <b>购买：</b> {item['name']}\n"
        f"💸 <b>花费：</b> {price} MP\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{result_msg}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>剩余魔力：</b> {remaining_points} MP\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"感谢惠顾！期待您的下次光临喵~(｡•̀ᴗ-)✧\"</i>"
    )

    buttons = [[InlineKeyboardButton("🔙 返回商店", callback_data="shop_home")]]
    try:
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
    except Exception:
        await query.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(buttons))


async def shop_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """返回商店主页"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    with get_session() as session:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        if not u or not u.emby_account:
            await edit_with_auto_delete(query, "💔 <b>请先绑定账号喵！</b>", parse_mode='HTML')
            return

        vip_badge = " 👑" if u.is_vip else ""
        discount = "5折" if u.is_vip else "原价"

        # 在session关闭前保存需要的值
        user_account = u.emby_account
        points = u.points

    txt = (
        f"🛒 <b>【 魔 法 · 商 店 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>客人：</b> {user_account}{vip_badge}\n"
        f"💎 <b>钱包：</b> {points} MP\n"
        f"🏷️ <b>折扣：</b> {discount}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📜 <b>使用 /buy 商品名 购买商品</b>\n"
        f"💡 <b>或点击下方按钮购买</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )

    # 构建商品列表（含限购信息）
    shop_list = ""
    for item_id, item in SHOP_ITEMS.items():
        price = item["vip_price"] if u.is_vip else item["price"]
        line = f"{item['emoji']} <b>{item['name']}</b> — <b>{price} MP</b>"

        # 神秘宝箱显示限购信息
        if item_id == "box":
            bought_count, need_reset = get_box_limit_status(u)
            if need_reset:
                bought_count = 0
            limit = 5 if u.is_vip else 3
            remaining = max(0, limit - bought_count)
            if remaining > 0:
                line += f" <i>(今日可购 {remaining}/{limit})</i>"
            else:
                line += f" <i>(今日已达上限)</i>"

        shop_list += line + "\n"

    txt += f"\n📦 <b>今日商品：</b>\n{shop_list}"
    txt += "\n━━━━━━━━━━━━━━━━━━\n"
    txt += "<i>\"欢迎光临！这里有你需要的所有魔法道具喵~(｡•̀ᴗ-)✧\"</i>"

    buttons = []
    row = []
    for i, (item_id, item) in enumerate(SHOP_ITEMS.items()):
        price = item["vip_price"] if u.is_vip else item["price"]
        row.append(InlineKeyboardButton(f"{item['emoji']} {price}MP", callback_data=f"buy_{item_id}"))
        if len(row) == 2 or i == len(SHOP_ITEMS) - 1:
            buttons.append(row)
            row = []

    try:
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='HTML')
    except Exception:
        pass


def register(app):
    """注册商店处理器"""
    app.add_handler(CommandHandler("shop", shop_main))
    app.add_handler(CommandHandler("store", shop_main))
    app.add_handler(CommandHandler("buy", buy_item))
    app.add_handler(CallbackQueryHandler(shop_callback, pattern=r"^buy_"))
    app.add_handler(CallbackQueryHandler(shop_home_callback, pattern=r"^shop_home$"))
