# RoyalBot 开发备忘录

> 本文件记录项目开发进度，内容持续追加，不删除历史记录

---

## 2026-01-01 初始化备忘录

### 1. 搞定了啥
- 创建 `ai.md` 备忘录文件，用于记录项目开发进度
- 确立文档维护规范：追加内容，不删除历史

### 2. 关键信息
- 文件路径：`/root/royalbot/ai.md`
- 记录格式：
  - 搞定了啥（结果）
  - 关键信息（文件、命令、变量）
  - 接下来该干嘛（下一步）

### 3. 接下来该干嘛
- 等待用户指示下一项任务

---

## 2026-01-01 集成灵装炼金与悬赏系统

### 1. 搞定了啥
- **数据库扩展**：给 `UserBinding` 模型添加了 `weapon` 和 `attack` 字段
- **新增插件 `forge.py`**：灵装炼金系统，玩家可消耗 MP 锻造随机武器
- **新增插件 `mission.py`**：悬赏公会系统，群内数学题抢答获得 MP 奖励
- **代码优化**：修复了原脚本的多个问题（缺少回调处理器、依赖 chat_data 等）

### 2. 关键信息
**修改的文件：**
- `database.py` - 添加字段：
  ```python
  weapon = Column(String, default=None)     # 装备武器
  attack = Column(Integer, default=0)       # 战力数值
  ```

**新增的文件：**
- `plugins/forge.py` - 炼金系统
  - 命令：`/forge`、`/weapon` 锻造武器，`/myweapon` 查看装备
  - VIP 锻造享受 5 折优惠
  - 支持"再来一次"按钮回调
  - 武器稀有度：普通(R)、史诗(SR)、神器(SSR)、咸鱼(特殊)

- `plugins/mission.py` - 悬赏系统
  - 命令：`/mission`、`/task` 发布题目
  - 题型：加减乘混合运算
  - 赏金：30-80 MP 随机
  - VIP 用户额外获得 20% 加成

### 3. 接下来该干嘛
- **重要**：需要重启机器人使新字段生效
- SQLite 数据库可能需要手动迁移（或删除重建）：
  ```bash
  rm data/magic.db  # 删除旧数据库（会清空所有数据！）
  # 或使用 ALTER TABLE 手动添加字段
  ```

---

## 2026-01-01 添加消息自毁功能（万人群优化）

### 1. 搞定了啥
- **新增 `utils.py` 工具模块**：提供消息自毁功能
- **配置系统扩展**：`config.py` 添加 `MESSAGE_DELETE_DELAY` 配置项（默认 30 秒）
- **插件集成**：`forge.py` 和 `mission.py` 已集成消息自毁
- **智能逻辑**：私聊不删除，群组才删除；配置为 0 则不删除

### 2. 关键信息
**新增文件：**
- `utils.py` - 工具函数模块
  ```python
  reply_with_auto_delete(message, text, delay=None, **kwargs)
  # 发送回复并自动删除（群组消息）
  ```

**修改的文件：**
- `config.py` - 新增配置：
  ```python
  MESSAGE_DELETE_DELAY = int(os.getenv("MESSAGE_DELETE_DELAY", 30))  # 默认30秒
  ```

- `plugins/forge.py` - 所有回复使用 `reply_with_auto_delete()`

- `plugins/mission.py` - 答对后额外删除原题目消息

**环境变量（可选）：**
```bash
# .env 文件添加（不添加则使用默认值30秒）
MESSAGE_DELETE_DELAY=30  # 设为0则不删除消息
```

### 3. 接下来该干嘛
- 其他插件（如 `checkin_bind.py`、`bank.py` 等）可以逐步迁移到 `reply_with_auto_delete()`
- 重启机器人生效

---

## 2026-01-01 全插件消息自毁集成完成

### 1. 搞定了啥
- **全部 9 个旧插件已完成消息自毁集成**
- **万人群刷屏问题解决**：群组消息默认 30 秒后自动删除
- **保留私聊体验**：私聊消息不删除，保持用户体验
- **语法验证通过**：所有插件编译无错误

### 2. 关键信息
**已集成的插件（使用 `reply_with_auto_delete()`）：**
- ✅ `plugins/forge.py` - 炼金系统
- ✅ `plugins/mission.py` - 悬赏系统
- ✅ `plugins/bag.py` - 背包系统
- ✅ `plugins/bank.py` - 银行系统
- ✅ `plugins/checkin_bind.py` - 签到绑定
- ✅ `plugins/fun_games.py` - 娱乐游戏（塔罗/盲盒/决斗）
- ✅ `plugins/me.py` - 个人档案
- ✅ `plugins/vip_shop.py` - VIP 商店
- ✅ `plugins/system_cmds.py` - 系统命令

**保持原样的插件（私聊场景，不需要自毁）：**
- ⚪ `plugins/start_menu.py` - 起始菜单（私聊为主）
- ⚪ `plugins/vip_apply.py` - VIP 申请（私聊+管理员通知）

**配置方式：**
```bash
# .env 文件
MESSAGE_DELETE_DELAY=30  # 默认值，可省略
# MESSAGE_DELETE_DELAY=0  # 设为0禁用自毁
```

### 3. 接下来该干嘛
- **重启机器人**使所有更改生效
- 在万人群测试消息自毁功能
- 如需调整自毁时间，修改 `.env` 中的 `MESSAGE_DELETE_DELAY`

---

## 2026-01-01 添加新功能命令到菜单

### 1. 搞定了啥
- **命令菜单扩展**：将新功能的命令添加到 Telegram 左侧命令菜单
- **新增命令**：`/bag`、`/forge`、`/myweapon`、`/mission`

### 2. 关键信息
**修改的文件：**
- `plugins/system_cmds.py` - `PUBLIC_COMMANDS` 列表新增：
  ```python
  ("bag", "🎒 次源背包")
  ("forge", "⚒️ 灵装炼金")
  ("myweapon", "⚔️ 我的装备")
  ("mission", "📜 公会悬赏")
  ```

**如何刷新菜单：**
- 方法1：重启机器人
- 方法2：管理员发送 `/sync` 命令

### 3. 接下来该干嘛
- 重启机器人或发送 `/sync` 刷新命令菜单
- 用户可在输入框左边看到新命令按钮

---

## 2026-01-01 完善 BotFather 命令菜单配置

### 1. 搞定了啥
- **更新 PUBLIC_COMMANDS 完整列表**：添加所有可用命令到 BotFather 菜单
- **命令数量**：从 11 个扩展到 19 个

### 2. 关键信息
**修改的文件：**
- `plugins/system_cmds.py` - 更新后的完整命令列表：
  ```python
  PUBLIC_COMMANDS = [
      ("start", "✨ 唤醒看板娘"),
      ("menu", "💠 展开魔法阵"),
      ("me", "📜 冒险者档案"),
      ("daily", "🍬 每日补给"),
      ("bind", "🔗 缔结契约"),
      ("vip", "👑 贵族中心"),
      ("bank", "🏦 皇家银行"),
      ("bag", "🎒 次源背包"),
      ("forge", "⚒️ 灵装炼金"),
      ("myweapon", "⚔️ 我的装备"),
      ("mission", "📜 悬赏公会"),
      ("duel", "⚔️ 魔法决斗"),
      ("poster", "🎰 命运盲盒"),
      ("tarot", "🔮 塔罗占卜"),
      ("shop", "🎁 魔法商店"),
      ("gift", "💝 魔力转赠"),
      ("hall", "🏆 荣耀殿堂"),
      ("libs", "🎬 视界观测"),
      ("help", "📖 魔法指南")
  ]
  ```

**现有插件对应关系：**
| 命令 | 插件 |
|------|------|
| start, menu, help | start_menu.py |
| daily, bind | checkin_bind.py |
| me | me.py |
| bank | bank.py |
| bag | bag.py |
| forge, myweapon | forge.py |
| mission | mission.py |
| tarot, poster, duel | fun_games.py |
| vip, shop | vip_shop.py |

**缺失待实现：**
| 命令 | 描述 |
|------|------|
| gift | 魔力转赠（用户间 MP 转账） |
| hall | 荣耀殿堂（全服战力排行榜） |
| libs | 视界观测（媒体库清单） |

### 3. 接下来该干嘛
- 实现 `/gift` 命令（魔力转赠功能）
- 实现 `/hall` 命令（战力排行榜）
- 实现 `/libs` 命令（媒体库）
- 管理员发送 `/sync` 刷新命令菜单

---

## 2026-01-01 新增魔力转赠与战力排行榜功能

### 1. 搞定了啥
- **新增 `plugins/gift.py`**：魔力转赠系统，用户间可互相转赠 MP
- **新增 `plugins/hall.py`**：荣耀殿堂排行榜，按战力展示 TOP 10
- **语法验证通过**：两个新插件编译无错误

### 2. 关键信息
**新增的文件：**
- `plugins/gift.py` - 魔力转赠
  - 命令：`/gift`
  - 用法1：回复某人 `/gift 数量`
  - 用法2：`/gift @username 数量`
  - 手续费：普通用户 5%，VIP 免费
  - 转账后双方都会收到通知
  - 不能转给自己

- `plugins/hall.py` - 战力排行榜
  - 命令：`/hall`
  - 展示 TOP 10 魔导士排名
  - 显示用户战力、称号
  - 称号系统：
    - 👑 星辰主宰 (10000+)
    - 🌟 传奇大魔导 (5000+)
    - 💫 星之大魔导师 (2000+)
    - ⭐ 大魔导师 (1000+)
    - 🔥 魔导师 (500+)
    - ⚔️ 高级魔法师 (200+)
    - 🛡️ 见习魔法师 (100+)
    - 🌱 初级魔法师 (50+)
    - 👶 冒险者学徒 (<50)
  - 当前用户排名高亮显示
  - VIP 和普通用户不同界面风格

**配置项（gift.py）：**
```python
GIFT_FEE_RATE = 0.05  # 5% 手续费
```

**配置项（hall.py）：**
```python
PAGE_SIZE = 10  # 每页显示数量
```

### 3. 接下来该干嘛
- 实现 `/libs` 命令（媒体库）- 仍缺失
- **已同步命令菜单到 BotFather**

---

## 2026-01-01 同步命令菜单到 BotFather

### 1. 搞定了啥
- **命令菜单已同步**：通过 API 直接调用 `set_my_commands` 同步到 BotFather
- **无需管理员操作**：自动完成，无需手动发送 `/sync`

### 2. 关键信息
**执行的命令：**
```python
await bot.set_my_commands(commands=[BotCommand(c, d) for c, d in PUBLIC_COMMANDS])
```

**已设置的命令（19 个）：**
| 命令 | 描述 | 插件 |
|------|------|------|
| start | ✨ 唤醒看板娘 | start_menu.py |
| menu | 💠 展开魔法阵 | start_menu.py |
| me | 📜 冒险者档案 | me.py |
| daily | 🍬 每日补给 | checkin_bind.py |
| bind | 🔗 缔结契约 | checkin_bind.py |
| vip | 👑 贵族中心 | vip_shop.py |
| bank | 🏦 皇家银行 | bank.py |
| bag | 🎒 次源背包 | bag.py |
| forge | ⚒️ 灵装炼金 | forge.py |
| myweapon | ⚔️ 我的装备 | forge.py |
| mission | 📜 悬赏公会 | mission.py |
| duel | ⚔️ 魔法决斗 | fun_games.py |
| poster | 🎰 命运盲盒 | fun_games.py |
| tarot | 🔮 塔罗占卜 | fun_games.py |
| shop | 🎁 魔法商店 | vip_shop.py |
| gift | 💝 魔力转赠 | gift.py ✨ |
| hall | 🏆 荣耀殿堂 | hall.py ✨ |
| libs | 🎬 视界观测 | ❌ 未实现 |
| help | 📖 魔法指南 | start_menu.py |

### 3. 接下来该干嘛
- 实现 `/libs` 命令（媒体库）- 最后一个缺失功能

---

## 2026-01-01 更新个人档案面板

### 1. 搞定了啥
- **数据库扩展**：添加 `intimacy` 字段（好感度系统）
- **重构 `me.py`**：个人档案面板新增武器、战力、好感度显示
- **VIP/普通双界面**：不同风格展示，带互动按钮

### 2. 关键信息
**修改的文件：**
- `database.py` - 添加字段：
  ```python
  intimacy = Column(Integer, default=0)  # 好感度
  ```

- `plugins/me.py` - 完全重写：
  - 显示：武器、战力、钱包/银行、好感度
  - VIP 版本：星灵风格，带"锻造武器"和"宠幸她"按钮
  - 普通版本：冒险者风格，带"铁匠铺"和"互动一下"按钮
  - 移除了 `reply_with_auto_delete()`（用户选择保留显示）

**预留 Callback 接口：**
- `forge` - 跳转锻造系统（待实现）
- `love_back` - 好感度互动系统（待实现）

### 3. 接下来该干嘛
- 实现 `forge` 和 `love_back` 按钮的回调处理器

---

## 2026-01-01 完善个人档案面板（动态称号系统）

### 1. 搞定了啥
- **新增动态称号系统**：称号根据战力自动计算，不再是固定值
- **修复战力判断 Bug**：使用 `is not None` 代替 `else`，避免 0 值被误判
- **整合 hall.py 称号逻辑**：称号与排行榜系统保持一致

### 2. 关键信息
**修改的文件：**
- `plugins/me.py` - 新增 `get_rank_title()` 函数：
  ```python
  def get_rank_title(attack):
      if attack >= 10000: return "👑 星辰主宰"
      elif attack >= 5000: return "🌟 传奇大魔导"
      elif attack >= 2000: return "💫 星之大魔导师"
      elif attack >= 1000: return "⭐ 大魔导师"
      elif attack >= 500: return "🔥 魔导师"
      elif attack >= 200: return "⚔️ 高级魔法师"
      elif attack >= 100: return "🛡️ 见习魔法师"
      elif attack >= 50: return "🌱 初级魔法师"
      else: return "👶 冒险者学徒"
  ```

**修复的 Bug：**
```python
# 修复前（战力为0时会被误判）
atk = user.attack if user.attack else 10

# 修复后（正确处理0值）
atk = user.attack if user.attack is not None else 10
```

**VIP 称号显示：**
- VIP 用户：`👑 星辰主宰 (VIP)`
- 普通用户：`👑 星辰主宰`

### 3. 接下来该干嘛
- 重启机器人测试动态称号显示

---

## 2026-01-01 VIP 专属尊贵称号体系

### 1. 搞定了啥
- **VIP 专属称号**：完全独立的称号体系，不再只是加后缀
- **三段式结构**：尊称 · 职位 · 加护（如「朕 · 星河主宰 · 绝对神格」）
- **贵族等级感**：朕 → 陛下 → 殿下 → 阁下 → 勋爵 → 准男爵 → 骑士 → 侍从 → 眷属

### 2. 关键信息
**修改的文件：**
- `plugins/me.py` - `get_rank_title(attack, is_vip)` 新增 VIP 判定

**称号对比：**
| 战力 | 普通用户 | VIP 用户 |
|------|----------|----------|
| 10000+ | 👑 星辰主宰 | 🏆 朕 · 星河主宰 · 绝对神格 |
| 5000+ | 🌟 传奇大魔导 | 👑 陛下 · 传奇至尊 · 星之眷属 |
| 2000+ | 💫 星之大魔导师 | 🌟 殿下 · 圣域贤者 · 虚空行者 |
| 1000+ | ⭐ 大魔导师 | 💫 阁下 · 皇家大魔导师 · 荣耀之翼 |
| 500+ | 🔥 魔导师 | ⚜️ 勋爵 · 殿堂魔导师 · 月光加护 |

### 3. 接下来该干嘛
- 可考虑同步更新 `hall.py` 排行榜也使用 VIP 专属称号

---
