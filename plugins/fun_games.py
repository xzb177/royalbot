"""
娱乐功能模块 - 魔法少女版
- 命运塔罗牌 (每日运势)
- 魔法盲盒 (魔力回收器)
- 魔法少女决斗 (PVP互动)
"""
import random
import uuid
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from database import Session, UserBinding
from utils import reply_with_auto_delete


# 导入活动追踪函数
async def track_activity_wrapper(user_id: int, activity_type: str):
    """包装函数，延迟导入避免循环依赖"""
    from plugins.mission import track_activity
    await track_activity(user_id, activity_type)


async def check_duel_bounty_progress(update: Update, context: ContextTypes.DEFAULT_TYPE, winner_id: int):
    """检查决斗悬赏任务进度"""
    from plugins.mission import check_bounty_progress
    await check_bounty_progress(update, context, "duel")

# ==========================================
# 🔮 玩法一：命运塔罗牌 (每日运势)
# ==========================================
TAROT_CARDS = [
    ("The Fool 愚者", "新的开始，自由，天真", "🌱", "★★★★★"),
    ("The Magician 魔术师", "创造力，行动，力量", "🪄", "★★★★★"),
    ("The High Priestess 女祭司", "直觉，神秘，潜意识", "🌙", "★★★★★"),
    ("The Empress 皇后", "丰饶，母性，自然", "👑", "★★★★★"),
    ("The Emperor 皇帝", "权威，结构，父性", "🛡️", "★★★★★"),
    ("The Lovers 恋人", "爱，和谐，选择", "💕", "★★★★☆"),
    ("The Chariot 战车", "意志力，胜利，决心", "⚔️", "★★★★☆"),
    ("Strength 力量", "勇气，耐心，控制", "🦁", "★★★★☆"),
    ("The Hermit 隐士", "内省，孤独，引导", "🕯️", "★★★☆☆"),
    ("Wheel of Fortune 命运之轮", "改变，周期，运气", "🎡", "★★★★★"),
    ("Justice 正义", "公平，真理，法律", "⚖️", "★★★☆☆"),
    ("The Sun 太阳", "快乐，成功，活力", "☀️", "★★★★★"),
    ("The Moon 月亮", "幻觉，恐惧，潜意识", "🌔", "★★☆☆☆"),
    ("The Star 星星", "希望，灵感，宁静", "🌟", "★★★★☆"),
    ("The World 世界", "完成，整合，成就", "🌍", "★★★★★")
]

async def tarot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """每日塔罗牌占卜 - 每天限抽一次"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    session = Session()
    user = session.query(UserBinding).filter_by(tg_id=user_id).first()

    # 检查是否已绑定
    if not user or not user.emby_account:
        session.close()
        await reply_with_auto_delete(msg, "💔 <b>请先绑定账号喵！</b>\n使用 <code>/bind 账号</code> 绑定后再来占卜~")
        return

    # 检查今日是否已抽取
    now = datetime.now()
    if user.last_tarot:
        last_tarot_date = user.last_tarot.date()
        today_date = now.date()
        if last_tarot_date >= today_date:
            # 计算剩余时间 - 修复：先归零再+1天
            next_available = user.last_tarot.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            remaining = next_available - now
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)

            session.close()
            await reply_with_auto_delete(
                msg,
                f"⏰ <b>今日已占卜喵~</b>\n\n"
                f"今天已经抽过塔罗牌了喵！\n"
                f"命运之轮需要时间转动... 距离下次占卜还有：<b>{hours}小时{minutes}分钟</b>\n\n"
                f"<i>\"明天再来吧，命运不会逃走的喵~(｡•̀ᴗ-)✧\"</i>"
            )
            return

    # 抽取塔罗牌
    card = random.choice(TAROT_CARDS)
    user.last_tarot = now
    # 追踪活动用于悬赏任务
    await track_activity_wrapper(user_id, "tarot")
    session.commit()
    session.close()

    txt = (
        f"🔮 <b>【 命 运 · 塔 罗 占 卜 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>看板娘闭上眼睛，为您从虚空中抽了一张牌...</i>\n\n"
        f"{card[2]} <b>{card[0]}</b>\n"
        f"✨ <b>星级：</b> {card[3]}\n"
        f"📝 <b>启示：</b> {card[1]}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"这就是星辰给您的指引哦，Master...(｡•̀ᴗ-)✧\"</i>"
    )
    await reply_with_auto_delete(msg, txt)


# ==========================================
# 🎰 玩法二：魔法盲盒 (魔力回收器)
# ==========================================
GACHA_ITEMS = {
    "UR": {  # Ultra Rare - 5% 概率
        "rate": 5,
        "emoji": "🌈",
        "name": "UR (Ultra Rare)",
        "items": [
            "[绝版] 魔法少女签名照",
            "[传说] 星灵契约书",
            "[限定] 看板娘亲手做的小饼干"
        ],
        "bonus": 500  # 返利
    },
    "SSR": {  # Super Super Rare - 10% 概率
        "rate": 10,
        "emoji": "🟡",
        "name": "SSR (Super Super Rare)",
        "items": [
            "4K 原盘海报 (典藏版)",
            "魔法少女剧场版合集",
            "声优签名卡"
        ],
        "bonus": 100
    },
    "SR": {  # Super Rare - 20% 概率
        "rate": 20,
        "emoji": "🟣",
        "name": "SR (Super Rare)",
        "items": [
            "蓝光 1080P 封面",
            "魔法少女原声带选辑",
            "角色设定集"
        ],
        "bonus": 0
    },
    "R": {  # Rare - 35% 概率
        "rate": 35,
        "emoji": "🔵",
        "name": "R (Rare)",
        "items": [
            "720P 高清海报",
            "主题曲 MV",
            "角色立绘"
        ],
        "bonus": 0
    },
    "N": {  # Normal - 30% 概率
        "rate": 30,
        "emoji": "⚪",
        "name": "N (Normal)",
        "items": [
            "480P 标清海报",
            "剧照截图",
            "宣传名片"
        ],
        "bonus": 0
    }
}

async def gacha_poster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """魔法盲盒 - 花费魔力抽取稀有物品"""
    msg = update.effective_message
    if not msg:
        return

    user_id = update.effective_user.id
    session = Session()
    try:
        u = session.query(UserBinding).filter_by(tg_id=user_id).first()

        # 检查是否已绑定
        if not u or not u.emby_account:
            await reply_with_auto_delete(msg, "💔 <b>请先绑定账号喵！</b>\n使用 <code>/bind 账号</code> 绑定后再来抽盲盒~")
            return

        # 设定价格 (VIP 5折优惠)
        price = 50 if u.is_vip else 100

        if u.points < price:
            await reply_with_auto_delete(
                msg,
                f"💸 <b>魔力不足喵！</b>\n\n"
                f"抽取盲盒需要 <b>{price} MP</b>\n"
                f"您当前余额：<b>{u.points} MP</b>\n\n"
                f"<i>\"快去签到攒钱吧喵！(ง •_•)ง\"</i>"
            )
            return

        # 扣费
        u.points -= price

        # 抽奖逻辑
        roll = random.randint(1, 100)
        cumulative = 0
        selected_rank = "N"

        for rank, data in GACHA_ITEMS.items():
            cumulative += data["rate"]
            if roll <= cumulative:
                selected_rank = rank
                break

        rank_data = GACHA_ITEMS[selected_rank]
        item = random.choice(rank_data["items"])

        # 高稀有度返利
        bonus = rank_data["bonus"]
        if bonus > 0:
            u.points += bonus

        # === 将物品存入背包 ===
        current_items = u.items if u.items else ""
        if current_items:
            u.items = current_items + "," + item
        else:
            u.items = item

        # 追踪活动用于悬赏任务
        await track_activity_wrapper(user_id, "box")
        session.commit()

        if selected_rank == "UR":
            desc = f"天哪！！是传说中的UR！欧皇附体喵！\n(系统自动返利 {bonus} MP)"
        elif selected_rank == "SSR":
            desc = "哇！金色的光芒！运气超棒喵~"
        elif selected_rank == "SR":
            desc = "不错的收获哦~"
        elif selected_rank == "R":
            desc = "普普通通...再试一次？"
        else:
            desc = "emmm...下次会更好的喵！"

        txt = (
            f"🎰 <b>【 命 运 · 盲 盒 机 】</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 消耗: {price} MP\n"
            f"💼 剩余: {u.points} MP\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💫 <i>魔法阵转动中... 砰！</i>\n\n"
            f"🏆 品级：{rank_data['emoji']} <b>{rank_data['name']}</b>\n"
            f"🎁 获得：<b>{item}</b>\n"
            f"📦 <i>物品已存入背包！使用 /bag 查看</i>\n"
            f"💬 看板娘：<i>\"{desc}\"</i>"
        )
        await reply_with_auto_delete(msg, txt)
    except Exception as e:
        session.rollback()
        await reply_with_auto_delete(msg, f"⚠️ <b>抽卡失败</b>\n\n<i>\"魔法阵出错了...请稍后再试喵！\"</i>")
    finally:
        session.close()


# ==========================================
# ⚔️ 玩法三：魔法少女决斗 (PVP 互动)
# ==========================================
# 决斗数据存储结构: context.bot_data["duels"] = { duel_id: { ... } }

async def duel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发起魔法少女决斗"""
    msg = update.effective_message
    if not msg:
        return

    challenger = update.effective_user

    # 必须回复一条消息才能发起
    target_msg = msg.reply_to_message
    if not target_msg:
        await reply_with_auto_delete(
            msg,
            "⚔️ <b>发起失败喵！</b>\n\n"
            f"请回复您要挑战的小伙伴消息，并发送：\n"
            f"<code>/duel 赌注金额</code>\n"
            f"例如：<code>/duel 100</code>\n\n"
            f"<i>\"起步价 10 MP 喵！\"</i>"
        )
        return

    opponent = target_msg.from_user

    # 检查是否在挑战自己
    if opponent.id == challenger.id:
        await reply_with_auto_delete(msg, "🤔 <b>不能和自己打架哦喵！</b>\n\n<i>\"再怎么想赢也不能这样啦！\"</i>")
        return

    # 检查是否在挑战机器人
    if opponent.is_bot:
        await reply_with_auto_delete(msg, "🤖 <b>看板娘是裁判，不能下场比赛的喵！</b>\n\n<i>\"找真人决斗吧！\"</i>")
        return

    # 解析金额
    try:
        bet = int(context.args[0]) if context.args else 50
        if bet < 10:
            await reply_with_auto_delete(msg, "⚠️ <b>赌注太小啦喵！</b>\n\n起步价 <b>10 MP</b>。")
            return
        if bet > 10000:
            await reply_with_auto_delete(msg, "⚠️ <b>赌注太大啦喵！</b>\n\n单次决斗上限 <b>10000 MP</b>。")
            return
    except (IndexError, ValueError):
        await reply_with_auto_delete(
            msg,
            "⚠️ <b>格式错误</b>\n\n"
            f"请使用：<code>/duel 金额</code>\n"
            f"例如：<code>/duel 100</code>"
        )
        return

    session = Session()

    # 检查发起者是否绑定
    u_challenger = session.query(UserBinding).filter_by(tg_id=challenger.id).first()
    if not u_challenger or not u_challenger.emby_account:
        session.close()
        await reply_with_auto_delete(msg, "💔 <b>您还未绑定账号喵！</b>\n\n使用 <code>/bind 账号</code> 绑定后再来决斗。")
        return

    # 检查发起者余额
    if u_challenger.points < bet:
        session.close()
        await reply_with_auto_delete(
            msg,
            f"💸 <b>魔力不足喵！</b>\n\n"
            f"只有 {u_challenger.points} MP，无法发起 {bet} MP 的决斗！"
        )
        return

    # 检查应战者是否绑定
    u_opponent = session.query(UserBinding).filter_by(tg_id=opponent.id).first()
    if not u_opponent or not u_opponent.emby_account:
        session.close()
        await reply_with_auto_delete(msg, "💔 <b>对方还未绑定账号喵！</b>\n\n<i>\"不能欺负没绑定的路人哦！\"</i>")
        return

    # 获取双方战力用于显示
    cha_atk = u_challenger.attack if u_challenger.attack is not None else 10
    opp_atk = u_opponent.attack if u_opponent.attack is not None else 10
    cha_wep = u_challenger.weapon or "赤手空拳"
    opp_wep = u_opponent.weapon or "赤手空拳"

    session.close()

    # 生成唯一决斗ID
    duel_id = str(uuid.uuid4())[:8]

    # 存储决斗数据
    duel_data = {
        "challenger_id": challenger.id,
        "challenger_name": challenger.first_name or "挑战者",
        "opponent_id": opponent.id,
        "opponent_name": opponent.first_name or "应战者",
        "bet": bet,
        "chat_id": update.effective_chat.id,
        "message_id": None,  # 稍后填充
        "created_at": datetime.now()
    }

    # 初始化 bot_data 存储结构
    if not hasattr(context, 'bot_data') or context.bot_data is None:
        context.bot_data = {}
    if "duels" not in context.bot_data:
        context.bot_data["duels"] = {}

    context.bot_data["duels"][duel_id] = duel_data

    # 构造按钮 (使用唯一ID)
    keyboard = [
        [
            InlineKeyboardButton("🔥 接受挑战", callback_data=f"duel_accept_{duel_id}"),
            InlineKeyboardButton("🏳️ 认怂", callback_data=f"duel_reject_{duel_id}")
        ]
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

    sent_msg = await msg.reply_html(
        f"⚔️ <b>【 魔 法 少 女 · 决 斗 展 开 】</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔴 <b>挑战者：</b> {challenger.first_name or '神秘人'}\n"
        f"    ⚡ 战力: <code>{cha_atk}</code> | 🗡️ {cha_wep}\n"
        f"\n"
        f"🔵 <b>应战者：</b> {opponent.first_name or '神秘人'}\n"
        f"    ⚡ 战力: <code>{opp_atk}</code> | 🗡️ {opp_wep}\n"
        f"\n"
        f"💰 <b>赌注金额：</b> <code>{bet}</code> MP\n"
        f"{adv_emoji} <i>{adv_text}</i>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>\"气氛焦灼起来了！应战者请在 60秒 内做出选择喵！\"</i>",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # 保存消息ID用于后续更新
    context.bot_data["duels"][duel_id]["message_id"] = sent_msg.message_id


async def duel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理决斗按钮回调"""
    query = update.callback_query
    await query.answer()

    # 解析: duel_accept_xxxxx 或 duel_reject_xxxxx
    parts = query.data.split('_')
    # parts[0]="duel", parts[1]="accept/reject", parts[2]=duel_id
    if len(parts) < 3:
        await query.edit_message_text("⚠️ <b>决斗数据错误喵！</b>")
        return

    action = parts[1]  # "accept" 或 "reject"
    duel_id = parts[2]  # 决斗ID

    if not context.bot_data or "duels" not in context.bot_data or duel_id not in context.bot_data["duels"]:
        await query.edit_message_text("⏰ <b>这场决斗已经过期啦喵！</b>\n\n<i>\"可能被取消了，或者服务器重启了喵~\"</i>")
        return

    duel_data = context.bot_data["duels"][duel_id]
    user = query.from_user

    # 检查决斗是否过期 (60秒，从30秒延长)
    if (datetime.now() - duel_data["created_at"]).total_seconds() > 60:
        await query.edit_message_text("⏰ <b>决斗已超时喵！</b>\n\n<i>\"犹豫就会败北...\"</i>")
        del context.bot_data["duels"][duel_id]
        return

    # 只有应战者能操作
    if user.id != duel_data["opponent_id"]:
        await query.answer("这不是你的决斗喵！吃瓜群众请后退！", show_alert=True)
        return

    if action == "reject":
        # 认怂，挑战者获得少量安慰奖
        session = Session()
        try:
            u_cha = session.query(UserBinding).filter_by(tg_id=duel_data["challenger_id"]).first()
            if u_cha:
                consolation = max(5, duel_data["bet"] // 10)  # 10% 安慰奖
                u_cha.points += consolation
                session.commit()
                await query.edit_message_html(
                    f"🏳️ <b>决斗取消</b>\n\n"
                    f"{user.first_name or '应战者'} 选择了认怂...\n"
                    f"💰 <b>{duel_data['challenger_name']}</b> 获得 <code>{consolation}</code> MP 安慰奖\n"
                    f"<i>\"没有人受伤，就是有点没面子喵...\"</i>"
                )
            else:
                await query.edit_message_html(
                    f"🏳️ <b>决斗取消</b>\n\n"
                    f"{user.first_name or '应战者'} 选择了认怂...\n"
                    f"<i>\"没有人受伤，就是有点没面子喵...\"</i>"
                )
        except:
            await query.edit_message_html(
                f"🏳️ <b>决斗取消</b>\n\n"
                f"{user.first_name or '应战者'} 选择了认怂...\n"
                f"<i>\"没有人受伤，就是有点没面子喵...\"</i>"
            )
        finally:
            session.close()
            if duel_id in context.bot_data.get("duels", {}):
                del context.bot_data["duels"][duel_id]
        return

    if action == "accept":
        session = Session()
        try:
            # 重新查询双方数据
            u_opp = session.query(UserBinding).filter_by(tg_id=user.id).first()
            u_cha = session.query(UserBinding).filter_by(tg_id=duel_data["challenger_id"]).first()

            bet = duel_data["bet"]

            # 再次检查余额
            if not u_opp or u_opp.points < bet:
                await query.edit_message_html(
                    f"💸 <b>决斗取消</b>\n\n"
                    f"{user.first_name or '应战者'} 的钱不够付赌注喵！\n"
                    f"<i>\"好尴尬啊...\"</i>"
                )
                del context.bot_data["duels"][duel_id]
                session.close()
                return

            if not u_cha or u_cha.points < bet:
                await query.edit_message_html(
                    f"💸 <b>决斗取消</b>\n\n"
                    f"{duel_data['challenger_name']} 的钱已经花光了喵！\n"
                    f"<i>\"发起者破产了，决斗无效！\"</i>"
                )
                del context.bot_data["duels"][duel_id]
                session.close()
                return

            # ===== 增强决斗系统：基于战力的战斗计算 =====
            cha_attack = u_cha.attack if u_cha.attack is not None else 10
            opp_attack = u_opp.attack if u_opp.attack is not None else 10

            # 计算基础胜率（基于战力差距，使用sigmoid函数平滑）
            attack_diff = cha_attack - opp_attack
            # 每100点战力差距约影响5%胜率，上限+/-30%
            attack_bonus = max(-0.3, min(0.3, attack_diff / 2000))

            # VIP 加成
            vip_bonus = 0.0
            if u_cha.is_vip:
                vip_bonus += 0.08  # 挑战者VIP +8%
            if u_opp.is_vip:
                vip_bonus -= 0.05  # 应战者VIP -5%（防守优势）

            # 武器加成（稀有度额外加成）
            cha_weapon_bonus = get_weapon_rarity_bonus(u_cha.weapon)
            opp_weapon_bonus = get_weapon_rarity_bonus(u_opp.weapon)

            # 最终胜率计算
            win_chance = 0.5 + attack_bonus + vip_bonus + (cha_weapon_bonus - opp_weapon_bonus) / 100
            win_chance = max(0.15, min(0.85, win_chance))  # 限制在15%-85%之间

            winner_is_challenger = random.random() < win_chance

            # 生成战斗过程文本
            battle_text = generate_battle_text(
                duel_data["challenger_name"], cha_attack, u_cha.weapon,
                duel_data["opponent_name"], opp_attack, u_opp.weapon,
                winner_is_challenger, win_chance
            )

            if winner_is_challenger:
                winner, loser = u_cha, u_opp
                win_name = duel_data["challenger_name"]
                lose_name = duel_data["opponent_name"]
            else:
                winner, loser = u_opp, u_cha
                win_name = duel_data["opponent_name"]
                lose_name = duel_data["challenger_name"]

            # 资金转移
            winner.points += bet
            winner.win += 1
            loser.points -= bet
            loser.lost += 1

            # 胜者可能获得战力提升（小概率）
            power_up = 0
            if random.random() < 0.15:  # 15%概率
                power_up = random.randint(1, 3)
                winner.attack = (winner.attack or 0) + power_up

            session.commit()

            # 检查悬赏任务进度（决斗类型）
            await check_duel_bounty_progress(update, context, winner.tg_id)

            power_up_text = f"\n⬆️ <b>{win_name}</b> 战力 +{power_up}！战斗经验提升了喵！" if power_up else ""

            await query.edit_message_html(
                f"⚔️ <b>【 决 斗 结 束 】</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{battle_text}\n"
                f"👑 <b>胜者：</b> {win_name}\n"
                f"💰 <b>收益：</b> +{bet} MP{power_up_text}\n\n"
                f"💀 <b>败者：</b> {lose_name} 失去 {bet} MP\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>\"多么精彩的战斗！看板娘看得热血沸腾喵！\"</i>"
            )
            del context.bot_data["duels"][duel_id]
        except Exception as e:
            session.rollback()
            await query.edit_message_html(
                f"⚠️ <b>决斗出错</b>\n\n<i>\"魔法阵不稳定...决斗已取消，请稍后再试喵！\"</i>"
            )
            if duel_id in context.bot_data.get("duels", {}):
                del context.bot_data["duels"][duel_id]
        finally:
            session.close()


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
    app.add_handler(CommandHandler("tarot", tarot))
    app.add_handler(CommandHandler("poster", gacha_poster))
    app.add_handler(CommandHandler("duel", duel_start))
    app.add_handler(CallbackQueryHandler(duel_callback, pattern=r"^duel_(accept|reject)_[a-f0-9]+$"))
