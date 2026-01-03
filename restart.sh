#!/bin/bash
# RoyalBot 重启脚本
# 使用 docker-compose 管理

cd /root/royalbot

echo "🔄 RoyalBot 重启中..."

# 使用 docker compose v2
docker compose down 2>/dev/null

# 重新构建和启动
docker compose up -d --build

# 等待数据库启动
echo "⏳ 等待数据库启动..."
sleep 5

# 等待数据库健康检查
echo "⏳ 等待数据库健康检查..."
for i in {1..30}; do
    if docker exec royalbot-db pg_isready -U royalbot -d royalbot &>/dev/null; then
        echo "✅ 数据库已就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ 数据库启动超时"
        docker logs royalbot-db --tail 20
        exit 1
    fi
    sleep 1
done

# 等待 bot 启动
echo "⏳ 等待 RoyalBot 启动..."
sleep 3

# 验证启动状态
if docker ps | grep -q royalbot; then
    echo "✅ RoyalBot 容器启动成功"
    docker logs royalbot --tail 10
else
    echo "❌ 启动失败，请检查日志:"
    docker logs royalbot
    exit 1
fi

echo ""
echo "📊 数据库状态:"
docker exec royalbot-db psql -U royalbot -d royalbot -c "SELECT version();" 2>/dev/null | head -3
