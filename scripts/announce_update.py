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

✨ RoyalBot v2.1 平衡性调整

🔧 本次更新：

1️⃣ 平衡性调整
   • 降低 UR/SSR 高品质物品获取概率
   • 优化锻造武器稀有度分布
   • 调整游戏经济平衡

2️⃣ 功能优化
   • 修复多处回调处理问题
   • 优化消息推送格式
   • 代码风格统一

3️⃣ 基础设施
   • 新增 Docker 部署配置
   • 更新依赖包

📊 代码检查：通过 ✅

"欧皇非天命，细水长流才是真~(｡•̀ᴗ-)✧"
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
