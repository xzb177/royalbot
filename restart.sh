#!/bin/bash
# RoyalBot Docker 重启脚本
# ⚠️ 必须通过 Docker 容器运行，禁止直接运行

cd /root/royalbot

echo "🔄 RoyalBot Docker 重启中..."

# 停止并删除旧容器
docker stop royalbot 2>/dev/null
docker rm royalbot 2>/dev/null

# 重新构建镜像（可选，加快速度可注释掉）
# docker build -t royalbot-royalbot:latest . > /dev/null 2>&1

# 启动新容器
docker run -d \
  --name royalbot \
  --restart unless-stopped \
  --network host \
  -e TZ=Asia/Shanghai \
  -e PYTHONUNBUFFERED=1 \
  -v /root/royalbot/bot.log:/app/bot.log \
  royalbot-royalbot:latest

# 等待启动
sleep 3

# 验证启动状态
if docker ps | grep -q royalbot; then
    echo "✅ RoyalBot 容器启动成功"
    docker logs royalbot --tail 5
else
    echo "❌ 启动失败，请检查日志:"
    docker logs royalbot
    exit 1
fi
