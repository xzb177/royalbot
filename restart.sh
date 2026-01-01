#!/bin/bash
# RoyalBot 安全重启脚本

# 查找并杀死所有 main.py 进程
pkill -9 -f "main.py" 2>/dev/null

# 等待进程完全退出
sleep 2

# 确认没有残留进程
if pgrep -f "main.py" > /dev/null; then
    echo "警告：仍有残留进程，强制清理..."
    killall -9 python3 2>/dev/null
    sleep 1
fi

# 清空日志
> /tmp/royalbot.log

# 启动新进程
cd /root/royalbot
nohup python3 main.py > /tmp/royalbot.log 2>&1 &

# 等待启动
sleep 3

# 验证启动状态
if pgrep -f "main.py" > /dev/null; then
    echo "✅ RoyalBot 启动成功 (PID: $(pgrep -f 'main.py' | head -1))"
else
    echo "❌ 启动失败，请检查日志: /tmp/royalbot.log"
    exit 1
fi
