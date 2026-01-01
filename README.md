# 🪄 RoyalBot - 云海看板娘

一款基于 Telegram 的多功能娱乐机器人，集成 Emby 契约绑定、积分经济系统、VIP 管理、魔法决斗等丰富功能。

## ✨ 功能特性

### 🎮 核心功能
- **🔗 契约绑定** - 绑定 Emby 账号，享受专属服务
- **💰 积分经济** - 钱包/金库双账户系统，支持存取款
- **👑 VIP 系统** - 贵族特权，手续费减免
- **🍬 每日签到** - 每日领取补给奖励

### ⚔️ 娱乐功能
- **🔮 塔罗占卜** - 每日命运预测
- **⚔️ 魔法决斗** - 与好友一决高下
- **🎰 命运盲盒** - 试手气赢大奖
- **⚒️ 灵装炼金** - 强化装备提升战力
- **🎁 魔力转赠** - 好友间积分赠送

### 🛡️ 管理功能
- **🛡️ 控制台** - 可视化管理面板
- **👥 用户管理** - 查询/积分操作/VIP设置
- **📋 VIP 审批** - 在线审核贵族申请
- **🗣️ 全员广播** - 一键通知所有用户

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Telegram Bot Token

### 安装部署

```bash
# 克隆仓库
git clone https://github.com/xzb177/royalbot.git
cd royalbot

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 BOT_TOKEN 等配置

# 启动机器人
python main.py
```

### Docker 部署

```bash
docker build -t royalbot .
docker run -d --env-file .env royalbot
```

## 📝 配置说明

在 `.env` 文件中配置以下变量：

| 变量 | 说明 | 必填 |
|------|------|------|
| `BOT_TOKEN` | Telegram Bot Token | ✅ |
| `OWNER_ID` | 管理员 Telegram ID | ✅ |
| `GROUP_ID` | 群组 ID | - |
| `MESSAGE_DELETE_DELAY` | 消息自毁延迟(秒) | - |
| `EMBY_URL` | Emby 服务器地址 | - |
| `EMBY_API_KEY` | Emby API 密钥 | - |

## 📋 命令列表

| 命令 | 说明 |
|------|------|
| `/start` | 唤醒看板娘 |
| `/menu` | 展开魔法阵（主菜单）|
| `/me` | 冒险者档案 |
| `/bind` | 缔结契约（绑定Emby）|
| `/daily` | 每日补给 |
| `/bank` | 皇家银行 |
| `/vip` | 贵族中心 |
| `/duel` | 魔法决斗 |
| `/tarot` | 塔罗占卜 |
| `/forge` | 灵装炼金 |

## 🛡️ 管理员命令

| 命令 | 说明 |
|------|------|
| `/admin` | 管理控制台 |
| `/query <用户ID>` | 查询用户信息 |
| `/addpoints <用户ID> <数量>` | 添加积分 |
| `/setvip <用户ID>` | 设置VIP |

## 📦 插件架构

项目采用插件化设计，每个功能模块独立开发：

```
plugins/
├── start_menu.py    # 主菜单系统
├── bank.py          # 银行系统
├── checkin_bind.py  # 签到与绑定
├── vip_apply.py     # VIP申请
├── fun_games.py     # 娱乐游戏
└── system_cmds.py   # 管理命令
```

## 📄 开源协议

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**Made with ❤️ by xzb177**
