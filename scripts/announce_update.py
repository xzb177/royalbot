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

    message = """
📢 【 系 统 更 新 通 知 】
━━━━━━━━━━━━━━━━━━

✨ RoyalBot v3.0 影音挖矿系统

🎬 本次新增功能：

1️⃣ 影音挖矿系统（边看片边赚MP）
   • 📊 观影状态 - 实时同步观看时长
   • 🏆 观影排行榜 - 本周观影排名
   • 🏁 新片首播冲刺 - 前10名看完得100MP
   • 🎯 每周观影挑战 - 完成目标领奖励
   • 🏆 观影成就系统 - 解锁成就得MP
   • 📈 观影统计报告 - 详细数据分析
   • 🎲 智能观影推荐 - 发现好内容
   • 👑 VIP观影特权 - 加成奖励翻倍

2️⃣ 新片自动推送
   • 新片上线自动推送到群组
   • 配置 EMBY_NOTIFY_CHATS 启用
   • 每30分钟检查一次更新

🔧 经济平衡优化：

• 锻造成本：200MP → 150MP
• 新手礼包：100MP → 150MP
• 观影收益：10分钟/MP → 5分钟/MP
• 新片窗口：24小时 → 48小时
• 每周挑战目标：60分钟 → 30分钟

🐛 修复优化：

• 修复 Emby 系统文案乱码
• 优化影音挖矿菜单布局
• 移除每日任务中的高消费任务
• 增强 Job Queue 定时任务支持

📊 代码检查：通过 ✅

"边看片边赚MP，观影也能薅羊毛喵~(｡•̀ᴗ-)✧"
━━━━━━━━━━━━━━━━━━
"""

    if Config.GROUP_ID:
        await bot.send_message(chat_id=Config.GROUP_ID, text=message)
        print("✅ 更新通知已发送到群组")
    else:
        print("⚠️ 未配置 GROUP_ID，跳过群组通知")

if __name__ == "__main__":
    import asyncio
    asyncio.run(send_update())
