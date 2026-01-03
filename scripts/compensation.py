#!/usr/bin/env python3
"""
全服补偿脚本
给所有用户发放统一补偿
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from telegram import Bot
from database import get_session, UserBinding
from config import Config


async def send_compensation():
    """发送全服补偿"""
    bot = Bot(token=Config.BOT_TOKEN)

    # 补偿配置
    COMPENSATION_MP = 500  # 每人补偿500 MP
    COMPENSATION_GACHA = 3  # 每人补偿3张盲盒券

    with get_session() as session:
        # 获取所有绑定用户
        users = session.query(UserBinding).filter(
            UserBinding.emby_account.isnot(None)
        ).all()

        total_users = len(users)
        compensated = 0

        for user in users:
            try:
                # 发放补偿
                user.points = (user.points or 0) + COMPENSATION_MP
                user.extra_gacha = (user.extra_gacha or 0) + COMPENSATION_GACHA
                compensated += 1
            except Exception as e:
                print(f"补偿用户 {user.tg_id} 失败: {e}")

        session.commit()

    # 发送群组通知
    message = f"""
🎁 【 全 服 补 偿 公 告 】
━━━━━━━━━━━━━━━━━━

抱歉，由于近期更新导致部分数据回档，
特此发放全服补偿，感谢大家理解与支持！

✨ <b>补偿内容：</b>
💰 <b>{COMPENSATION_MP} MP</b>
🎰 <b>{COMPENSATION_GACHA} 张</b> 盲盒券

📊 <b>已发放：</b>{compensated}/{total_users} 人

<i>\"感谢大家一直以来的支持喵~(｡•̀ᴗ-)✧\"</i>
━━━━━━━━━━━━━━━━━━
"""

    if Config.GROUP_ID:
        await bot.send_message(chat_id=Config.GROUP_ID, text=message, parse_mode='HTML')
        print(f"✅ 补偿已发放: {compensated} 人")
    else:
        print("⚠️ 未配置 GROUP_ID")


if __name__ == "__main__":
    import asyncio
    asyncio.run(send_compensation())
