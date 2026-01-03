#!/usr/bin/env python3
"""
发送更新通知到群组
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from telegram import Bot
from config import Config

async def send_update():
    """发送更新通知"""
    bot = Bot(token=Config.BOT_TOKEN)

    message = """📢 【 Emby 影音挖矿系统上线 】
━━━━━━━━━━━━━━━━━━

🎬 边看片边赚MP，观影也能薅羊毛！

✨ 八大功能全面上线：

📊 观影状态
• 实时同步 Emby 观看时长
• 每5分钟 = 1 MP
• 每日最多36 MP
• VIP收益翻倍

🏆 观影排行榜
• 本周观影时长排名
• 榜一额外奖励

🏁 新片首播冲刺
• 新片上线48小时内
• 前10名看完得 100 MP

🎯 每周观影挑战
• 自设观影目标
• 完成挑战领奖励

🏆 观影成就系统
• 观影1小时、10小时等成就
• 解锁获得 MP 奖励

📈 观影统计报告
• 详细数据分析
• 观影历史记录

🎲 智能观影推荐
• 基于喜好推荐内容

📢 新片自动推送
• 新片上线自动通知群组

━━━━━━━━━━━━━━━━━━
入口：/menu → 影音挖矿中心
━━━━━━━━━━━━━━━━━━
"""

    if Config.GROUP_ID:
        await bot.send_message(chat_id=Config.GROUP_ID, text=message)
        print(f"✅ 更新通知已发送到群组 {Config.GROUP_ID}")
        print(f"📝 消息长度: {len(message)} 字符")
    else:
        print("⚠️ 未配置 GROUP_ID，跳过群组通知")

if __name__ == "__main__":
    import asyncio
    asyncio.run(send_update())
