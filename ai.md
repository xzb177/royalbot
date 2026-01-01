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

## 2026-01-01 修复 VIP 申请批准后群组通报功能

### 1. 搞定了啥
- **修复群组通报 Bug**：VIP 批准后群组推送无反应的问题

### 2. 关键信息
**修改的文件：**
- `plugins/vip_apply.py:312` - 条件判断修复

**Bug 原因：**
```python
# 修复前（错误）
if Config.GROUP_ID > 0:  # Telegram 群组 ID 是负数(-100...)，条件永远为 False

# 修复后（正确）
if Config.GROUP_ID:  # 使用真值判断，负数也能通过
```

### 3. 接下来该干嘛
- 重启机器人生效
- 测试 VIP 批准后群组通报是否正常推送

---

## 2026-01-01 VIP 群组通报消息自毁功能

### 1. 搞定了啥
- **新增 `send_with_auto_delete()` 函数**：`utils.py` 添加直接发送消息并自毁的通用函数
- **VIP 群组通报自毁**：批准 VIP 后的群组推送消息现在会自动删除（默认30秒）
- **保持私聊通知不变**：用户私聊收到的通知消息不删除

### 2. 关键信息
**修改的文件：**
- `utils.py` - 新增函数：
  ```python
  async def send_with_auto_delete(bot, chat_id, text, delay=None, **kwargs)
  # 发送消息并在延迟后自动删除（仅群组有效）
  ```

- `plugins/vip_apply.py:11,334-339` - 群组通报改用 `send_with_auto_delete()`
  ```python
  await send_with_auto_delete(
      context.bot,
      Config.GROUP_ID,
      announcement,
      parse_mode='HTML'
  )
  ```

### 3. 接下来该干嘛
- 重启机器人生效

---

## 2026-01-01 修复 /menu 命令升级 VIP 按钮问题

### 1. 搞定了啥
- **修复 VIP 按钮回调处理**：改用 `edit_message_text` 而不是发送新消息
- **添加返回菜单按钮**：所有子页面都可以返回主菜单
- **VIP 申请流程优化**：引导用户前往私聊申请，避免群组消息自毁问题
- **决斗场页面优化**：添加返回按钮，使用编辑消息

### 2. 关键信息
**修改的文件：**
- `plugins/start_menu.py` - 重构按钮回调处理

**问题原因：**
- 群组菜单中的 VIP 按钮点击后，使用 `reply_with_auto_delete` 发送新消息
- 新消息在群组中会被自动删除，导致用户点击按钮时消息已不存在
- 产生 `Unknown slash command: menu /menu` 错误

**修复方案：**
1. **`vip` 按钮** - 直接内嵌处理逻辑，使用 `edit_message_text`
2. **`upgrade_vip` 按钮** - 改用 `edit_message_text` + 返回按钮
3. **`apply_vip` 按钮** - 引导用户私聊申请，提供跳转链接
4. **`back_menu` 回调** - 重新显示完整菜单
5. **`duel_info` 按钮** - 添加返回按钮

**新增回调数据：**
- `back_menu` - 返回主菜单

### 3. 接下来该干嘛
- 重启机器人生效
- 测试群组菜单 VIP 按钮流程

---

## 2026-01-01 菜单按钮优化：删除重复 VIP 按钮，添加荣耀殿堂

### 1. 搞定了啥
- **删除重复 VIP 按钮**：移除第四个位置的 "💎升级 VIP" 按钮
- **添加荣耀殿堂按钮**：新增 "🏆 荣耀殿堂" 按钮，链接到战力排行榜
- **保留第一个 VIP 按钮**：普通用户显示 "💎 成为 VIP"，VIP 显示 "📜 个人档案"

### 2. 关键信息
**修改的文件：**
- `plugins/start_menu.py`

**菜单按钮布局（更新后）：**
```
┌─────────────────┬─────────────────┐
│ 📜 个人档案     │ 🍬 每日签到     │  (第一行)
│ 或 💎 成为 VIP  │                 │
├─────────────────┼─────────────────┤
│ 🏦 皇家银行     │ 🎒 次源背包     │  (第二行)
├─────────────────┼─────────────────┤
│ 🔮 命运占卜     │ 🎰 盲盒抽取     │  (第三行)
├─────────────────┼─────────────────┤
│ 🏆 荣耀殿堂     │ ⚔️ 决斗场       │  (第四行，已修改)
├─────────────────┴─────────────────┤
│ 📖 魔法指南                    │  (第五行)
└───────────────────────────────────┘
```

**新增回调：**
- `hall` - 调用 `hall_leaderboard()` 显示战力排行榜

### 3. 接下来该干嘛
- 重启机器人生效

---

## 2026-01-01 修复菜单「魔法指南」按钮指向

### 1. 搞定了啥
- **修复按钮错误**：「📖 魔法指南」按钮从 URL 链接改为回调处理
- **新增返回按钮**：魔法指南页面可以返回主菜单
- **内嵌显示内容**：使用 `edit_message_text` 编辑当前消息，不发送新消息

### 2. 关键信息
**修改的文件：**
- `plugins/start_menu.py`

**修改内容：**
- 第47行：`url="https://t.me/YourChannel"` → `callback_data="help_manual"`
- 第305行（back_menu）：同步更新
- 新增 `help_manual` 回调处理（第336-361行）

**修改前：**
```python
[InlineKeyboardButton("📖 魔法指南", url="https://t.me/YourChannel")]
```

**修改后：**
```python
[InlineKeyboardButton("📖 魔法指南", callback_data="help_manual")]
```

### 3. 接下来该干嘛
- 重启机器人生效

---

## 2026-01-01 全局魔法少女/二次元/皇家风格文案改版

### 1. 搞定了啥
- **全局文案风格改造**：将所有插件改为魔法少女/二次元/皇家风格
- **统一语言风格**：使用「喵~」等二次元口癖，颜文字 (｡•̀ᴗ-)✧ (≧◡≦) 等
- **VIP/普通双体系**：VIP用户使用皇家尊贵称呼，普通用户使用见习魔法少女/学院风格

### 2. 关键信息
**修改的文件（全部12个插件）：**

| 文件 | 主要改动 |
|------|----------|
| `start_menu.py` | 「星辰殿堂」/「魔法学院」双菜单，魔法少女主题 |
| `checkin_bind.py` | 缔结魔法契约，领取魔力，见习魔法少女称呼 |
| `bank.py` | 皇家魔法少女金库 / 魔法学院储蓄柜台 |
| `bag.py` | 魔法少女的背包 |
| `forge.py` | 魔法武器炼金，可爱/做蛋糕元素 |
| `fun_games.py` | 塔罗占卜，魔法盲盒，魔法少女决斗 |
| `me.py` | 星灵终极契约书 / 魔法少女档案 |
| `vip_shop.py` | 觉醒之门，皇家魔法少女特权 |
| `gift.py` | 魔力转赠，见习魔法少女手续费 |
| `hall.py` | 皇家荣耀殿堂 / 魔法学院荣耀榜单 |
| `vip_apply.py` | 觉醒仪式流程，新晋VIP群组通报 |

**风格关键词：**
- 魔法少女 / 魔法学院 / 皇家 / 星辰 / 觉醒
- 称呼：Master / 酱 / 喵~
- 颜文字：(｡•̀ᴗ-)✧ (≧◡≦) (｡･ω･｡)ﾉ♡ (*/ω＼*)

### 3. 接下来该干嘛
- **重启机器人**使所有文案更改生效
- 体验全新的魔法少女风格看板娘喵~

---

## 2026-01-01 修复菜单「魔法指南」按钮指向

### 1. 搞定了啥
- **数据库扩展**：添加 8 个新字段支持活动追踪
- **重写 mission.py**：从单一数学题扩展为 7 种悬赏类型
- **聊天挖矿增强**：连击系统、时段加成、关键词彩蛋、稀有掉落
- **多插件集成**：forge、tarot、box、gift 活动自动追踪

---

## 2026-01-01 修复决斗Bug + 全面增强决斗系统

### 1. 搞定了啥
- **修复决斗回调解析Bug**：别人邀请后点击"接受"显示"决斗已过期"的问题
- **全面增强决斗玩法**：
  - 新增战力系统影响（战力差距影响胜率）
  - 新增武器稀有度加成（SSR+15%, SR+10%, R+5%, 咸鱼-5%）
  - 新增战斗过程描述文本
  - 新增胜者15%概率战力提升（1-3点）
  - 认怂安慰奖（挑战者获得10%赌注补偿）
  - 超时从30秒延长到60秒
  - 胜率限制在15%-85%之间，避免过于极端
  - VIP加成调整：挑战者+8%，应战者-5%（防守优势）

### 2. 关键信息
**修改的文件：**
- `plugins/fun_games.py`

**Bug原因：**
```python
# 修复前（错误）
parts = query.data.split('_')
# duel_accept_abc12345 -> ["duel", "accept", "abc12345"]
action = f"{parts[1]}_{parts[2]}"  # 变成 "accept_abc12345" ❌
duel_id = parts[3]  # 索引越界，变成 None ❌

# 修复后（正确）
parts = query.data.split('_')
action = parts[1]  # "accept" ✅
duel_id = parts[2]  # "abc12345" ✅
```

**新增函数：**
- `get_weapon_rarity_bonus(weapon)` - 武器稀有度战力加成
- `generate_battle_text()` - 生成战斗过程描述

**决斗邀请界面新功能：**
- 显示双方战力
- 显示双方装备武器
- 战力对比指示器（压倒性优势/略占上风/势均力敌）

**胜率计算公式：**
```python
win_chance = 0.5 + attack_bonus + vip_bonus + weapon_bonus
# attack_bonus: 战力差距，每2000点差±30%
# vip_bonus: 挑战者VIP+8%，应战者VIP-5%
# weapon_bonus: (cha_weapon - opp_weapon) / 100
# 最终限制在 0.15 - 0.85 之间
```

### 3. 接下来该干嘛
- 重启机器人生效
- 测试决斗功能
- 可考虑添加连胜奖励、败者安慰等奖励机制

---

## 2026-01-01 VIP专属权益文案优化

### 1. 搞定了啥
- **VIP权益文案全面升级**：从4项扩展到9项完整权益展示
- **统一权益列表格式**：使用 `图标 + 名称 ─ 说明` 的简洁格式
- **多位置同步更新**：VIP中心、菜单按钮、申请批准通知全部更新

### 2. 关键信息
**修改的文件：**
- `plugins/vip_shop.py` - VIP中心主页
- `plugins/start_menu.py` - 菜单VIP按钮回调
- `plugins/vip_apply.py` - VIP批准通知（群组+私聊）

**完整VIP权益列表（9项）：**
| 图标 | 权益名称 | 说明 |
|------|----------|------|
| 🚀 | 4K 极速通道 | 画质飞跃/已开启 |
| 🏰 | 皇家金库 | 存取/转账 0 手续费 |
| 💰 | 双倍魔力 | 每日签到 2x 收益 |
| ⚒️ | 炼金工坊 | 武器锻造 5 折 |
| 🔮 | 命运眷顾 | 塔罗占卜 5 折 |
| 🎁 | 魔力转赠 | 免手续费（普通5%） |
| 📜 | 悬赏加成 | 任务奖励暴击提升 |
| ⚔️ | 决斗祝福 | 挑战时 +8% 胜率 |
| 🏆 | 星辰称号 | 三段式尊贵头衔 |

**文案格式对比：**
```python
# 修改前（简单列举）
"✨ 4K 极速通道\n"
"🏰 皇家金库（免手续费）\n"
"💕 双倍魔力加成\n"
"🎀 专属称号与称号\n"

# 修改后（详细格式）
"🚀 <b>4K 极速通道</b>\n"
"   └─ 流畅观影，画质飞升~\n\n"
"🏰 <b>皇家金库特权</b>\n"
"   └─ 存取/转账 0 手续费\n\n"
```

### 3. 接下来该干嘛
- 重启机器人生效
- 测试VIP相关文案显示效果

---

## 2026-01-01 修复决斗按钮回调无响应问题

### 1. 搞定了啥
- **修复决斗按钮回调无响应**：点击"接受挑战"和"认怂"按钮没有反应的问题
- **修复回调处理器优先级冲突**：将 `start_menu.py` 的通配符回调移到 group=1

### 2. 关键信息
**问题原因：**
- `start_menu.py` 和 `fun_games.py` 的回调处理器都在 group=0（默认优先级）
- 插件加载顺序导致 `start_menu.py` 的通配符回调优先处理，阻止了决斗回调执行

**修改的文件：**
- `plugins/start_menu.py:389` - 回调处理器注册添加 `group=1`：
```python
# 修改前
app.add_handler(CallbackQueryHandler(button_callback, pattern="^(?!admin_|vip_|duel_|forge_|me_).*$"))

# 修改后
app.add_handler(CallbackQueryHandler(button_callback, pattern="^(?!admin_|vip_|duel_|forge_|me_).*$"), group=1)
```

**Telegram 回调处理器优先级：**
- group 值越小，优先级越高
- 默认 group=0，具体回调应该使用 group=0
- 通配符/兜底回调应该使用更高的 group 值（如 group=1）

### 3. 接下来该干嘛
- 测试决斗功能是否正常工作
- 如有类似回调问题，其他模块也可参考此解决方案

---

## 2026-01-01 修复塔罗占卜命令无响应问题

### 1. 搞定了啥
- **修复 `/tarot` 命令无响应**：在某些情况下 `update.message` 为 `None` 导致命令失败
- **全面修复 fun_games.py**：所有命令处理函数改用 `update.effective_message`
- **增强代码健壮性**：添加空值检查，防止 AttributeError

### 2. 关键信息
**问题原因：**
```python
# 修复前（错误）
async def tarot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_with_auto_delete(update.message, txt)  # update.message 可能为 None

# 修复后（正确）
async def tarot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message  # 安全的消息获取
    if not msg:
        return
    await reply_with_auto_delete(msg, txt)
```

**修改的文件：**
- `plugins/fun_games.py` - 修复了三个函数：
  - `tarot()` - 塔罗占卜（第49-105行）
  - `gacha_poster()` - 盲盒抽取（第169-249行）
  - `duel_start()` - 决斗发起（第259-409行）

**`update.effective_message` vs `update.message`：**
- `update.message` - 仅在消息更新时存在
- `update.effective_message` - Telegram 提供的安全封装，自动处理各种更新类型

### 3. 接下来该干嘛
- **重启机器人**使修改生效
- 测试 `/tarot`、`/poster`、`/duel` 命令

---

## 2026-01-01 修复 fun_games.py 导入路径错误

### 1. 搞定了啥
- **修复模块导入错误**：`from mission import ...` 改为 `from plugins.mission import ...`
- **创建安全重启脚本**：`restart.sh` 确保只有一个进程运行

### 2. 关键信息
**问题原因：**
```
ModuleNotFoundError: No module named 'mission'
```
fun_games.py 中使用了错误的导入路径：
```python
# 修复前（错误）
from mission import track_activity

# 修复后（正确）
from plugins.mission import track_activity
```

**修改的文件：**
- `plugins/fun_games.py:19,25` - 导入路径修复

**新增文件：**
- `/root/royalbot/restart.sh` - 安全重启脚本
  ```bash
  # 使用方法
  /root/royalbot/restart.sh
  ```

### 3. 接下来该干嘛
- 测试 `/tarot`、`/poster`、`/duel` 命令确认修复成功

---

## 2026-01-01 修复个人档案「圣物锻造」按钮

### 1. 搞定了啥
- **修复「圣物锻造」按钮无响应**：添加缺失的 `forge_go_callback` 回调处理器
- **复用现有逻辑**：调用 forge.py 的 `forge_callback` 实现锻造功能

### 2. 关键信息
**问题原因：**
- `me.py` 中定义了 `callback_data="forge_go"` 按钮
- 但没有注册对应的回调处理器

**修改的文件：**
- `plugins/me.py:200-204` - 添加 `forge_go_callback` 函数
- `plugins/me.py:243` - 注册回调处理器

```python
# 新增函数
async def forge_go_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理「立即锻造」按钮回调 - 调用 forge.py 的锻造逻辑"""
    from plugins.forge import forge_callback
    await forge_callback(update, context)

# 新增注册
app.add_handler(CallbackQueryHandler(forge_go_callback, pattern="^forge_go$"))
```

### 3. 接下来该干嘛
- 测试个人档案中的「圣物锻造」按钮

---

## 2026-01-01 代码推送到 GitHub 仓库

### 1. 搞定了啥
- **提交并推送所有更改**到 `git@github.com:xzb177/royalbot.git`
- **提交 ID**: `32ae3b1`
- **17 个文件变更**: 1701 行新增，354 行删除

### 2. 关键信息
**提交的文件（16个修改 + 1个新增）：**
- `ai.md` - 更新备忘录
- `database.py` - 数据库字段扩展
- `utils.py` - 消息自毁工具
- `plugins/*.py` - 全部12个插件
- `restart.sh` - 新增安全重启脚本

**提交信息：**
```
feat: 完善魔法少女风格系统与多项功能增强

主要更新:
- 全局文案魔法少女/二次元风格改造
- 决斗系统增强: 战力影响、武器加成、战斗描述
- 塔罗占卜/盲盒/决斗命令修复
- VIP权益扩展至9项完整展示
- 个人档案动态称号体系
- 消息自毁功能全插件集成
- 新增魔力转赠、荣耀殿堂功能
- 修复多项回调处理Bug
```

**仓库地址：**
```
git@github.com:xzb177/royalbot.git
```

### 3. 接下来该干嘛
- 等待用户指示下一项任务

---

## 2026-01-01 背包系统完全重构

### 1. 搞定了啥
- **数据库扩展**：添加 `items` 字段存储用户背包物品（逗号分隔格式）
- **盲盒系统打通**：抽卡后自动将物品存入背包
- **完全重写 bag.py**：实现真正的背包系统，支持物品统计、稀有度排序
- **快捷按钮集成**：一键跳转盲盒/占卜/个人档案

### 2. 关键信息
**修改的文件：**
- `database.py:31` - 添加字段：
  ```python
  items = Column(Text, default="")  # 道具背包 (逗号分隔存储)
  ```

- `plugins/fun_games.py:220-225` - 盲盒物品存入背包：
  ```python
  current_items = u.items if u.items else ""
  if current_items:
      u.items = current_items + "," + item
  else:
      u.items = item
  ```

- `plugins/fun_games.py:251` - 抽卡提示增加背包说明

- `plugins/bag.py` - 完全重写：
  - 使用 `Counter` 统计物品数量
  - 按稀有度分组（UR/SSR/SR/R/N）显示
  - 显示用户魔力、战力、VIP状态、藏品总数
  - 快捷按钮：抽盲盒、占卜、个人档案
  - 空背包友好提示

**稀有度配置：**
| 图标 | 稀有度 | 关键词 |
|------|--------|--------|
| 🌈 | UR | 签名照、契约书、小饼干、传说、限定 |
| 🟡 | SSR | 4K、原盘、典藏、剧场版、签名卡 |
| 🟣 | SR | 蓝光、1080P、原声带、设定集 |
| 🔵 | R | 720P、高清、主题曲、立绘 |
| ⚪ | N | 480P、标清、剧照、名片、宣传 |

### 3. 接下来该干嘛
- 重启机器人使 `items` 字段生效（SQLAlchemy 会自动添加列）
- 测试 `/poster` 抽卡后物品是否正确存入背包
- 测试 `/bag` 命令查看背包显示效果

---

## 2026-01-01 全局 UI 风格统一

### 1. 搞定了啥
- **统一分隔线风格**：所有插件使用 `━━━━━━━━━━━━━━━━━━` 分隔线
- **统一标题格式**：`【 标 题 】` 格式，VIP 和普通用户双界面
- **统一报错提示**：使用相同的标题和分隔线风格
- **修复导入路径**：`forge.py` 和 `gift.py` 修复循环依赖导入问题

### 2. 关键信息
**修改的文件（6个）：**
- `plugins/bank.py` - 皇家金库 / 学院储蓄柜台
- `plugins/checkin_bind.py` - 每日补给 / 魔法契约缔结
- `plugins/forge.py` - 炼金工坊，修复 `from plugins.mission import`
- `plugins/hall.py` - 荣耀殿堂排行榜
- `plugins/gift.py` - 魔力转赠，修复 `from plugins.mission import`
- `plugins/bag.py` - 背包系统（已完成）

**UI 统一标准：**
```
🎯 <b>【 标 题 】</b>
━━━━━━━━━━━━━━━━━━
内容区域
━━━━━━━━━━━━━━━━━━
<i>"看板娘台词喵~(｡•̀ᴗ-)✧"</i>
```

**VIP/普通双界面：**
- VIP 用户：使用「皇家 · XXX」标题，尊贵称呼 "Master"
- 普通用户：使用「魔法学院 · XXX」标题，亲切称呼 "小魔法少女"

### 3. 接下来该干嘛
- 已重启机器人，UI 风格全部统一生效
- 可考虑优化 `vip_shop.py` 和 `me.py` 的 UI 风格
- 可考虑优化 `fun_games.py` 的塔罗/盲盒/决斗 UI 风格

---

## 2026-01-01 魔法商店系统

### 1. 搞定了啥
- **新增 `plugins/shop.py`**：完整的魔法商店系统
- **数据库字段扩展**：添加 6 个道具效果字段
- **VIP 折扣系统**：VIP 用户享受所有商品 5 折优惠

### 2. 关键信息
**新增的文件：**
- `plugins/shop.py` - 魔法商店
  - 命令：`/shop`、`/store` 打开商店，`/buy 商品名` 直接购买
  - 支持按钮购买和命令购买两种方式
  - 购买后可返回商店继续购物

**数据库字段（已在 database.py 添加）：**
```python
lucky_boost = Column(Boolean, default=False)      # 幸运草：下次签到暴击率UP
shield_active = Column(Boolean, default=False)    # 防御卷轴：下次决斗失败不掉钱
extra_tarot = Column(Integer, default=0)          # 额外塔罗次数
extra_gacha = Column(Integer, default=0)          # 额外盲盒次数
free_forges = Column(Integer, default=0)          # 免费锻造券
free_forges_big = Column(Integer, default=0)      # 高级锻造券（稀有度UP）
```

**商店商品列表：**
| 商品 | 普通价 | VIP价 | 效果 |
|------|--------|-------|------|
| 🔮 塔罗占卜券 | 50 | 25 | 额外一次塔罗占卜 |
| 🎰 盲盒券 | 100 | 50 | 额外一次盲盒抽取 |
| ⚒️ 锻造锤(小) | 50 | 25 | 免费锻造一次 |
| ⚒️ 锻造锤(大) | 500 | 250 | 免费锻造+稀有度UP |
| 🍀 幸运草 | 30 | 15 | 下次签到暴击率+50% |
| ⚡ 能量药水 | 150 | 75 | 获得200MP |
| 🛡️ 防御卷轴 | 80 | 40 | 下次决斗失败不掉钱 |
| 🎁 神秘宝箱 | 100 | 50 | 随机开出50-500MP |

### 3. 接下来该干嘛
- 商店功能已生效（PID: 1690633）
- 需要打通商店道具效果到其他系统：
  - `lucky_boost` → 签到系统
  - `shield_active` → 决斗系统
  - `extra_tarot` → 塔罗系统
  - `extra_gacha` → 盲盒系统
  - `free_forges` / `free_forges_big` → 锻造系统

---

## 2026-01-01 商店道具效果全打通

### 1. 搞定了啥
- **修复商店无响应问题**：添加缺失的数据库字段（lucky_boost, shield_active, extra_tarot, extra_gacha, free_forges, free_forges_big）
- **打通幸运草→签到**：签到时检查 lucky_boost，50%概率暴击获得额外魔力
- **打通防御卷轴→决斗**：决斗失败时消耗 shield_active，不扣除败者魔力
- **打通塔罗券→塔罗**：额外塔罗券可绕过每日限制，消费后扣减
- **打通盲盒券→盲盒**：额外盲盒券可免费抽取，消费后扣减
- **打通锻造券→锻造**：
  - 小锻造锤：免费锻造一次
  - 大锻造锤：免费锻造 + 稀有度UP（15%神器，25%传说，20%史诗）
- **优化 _generate_weapon 函数**：新增 boost_rarity 参数支持高稀有度模式

### 2. 关键信息
**修改的文件（5个）：**
- `plugins/checkin_bind.py` - 签到系统支持幸运草暴击
- `plugins/fun_games.py` - 塔罗/盲盒支持额外券，决斗支持防御卷轴
- `plugins/forge.py` - 锻造支持小/大锻造券，高稀有度模式
- `plugins/shop.py` - 商店系统（无修改）

**数据库迁移：**
```sql
ALTER TABLE bindings ADD COLUMN lucky_boost BOOLEAN DEFAULT 0;
ALTER TABLE bindings ADD COLUMN shield_active BOOLEAN DEFAULT 0;
ALTER TABLE bindings ADD COLUMN extra_tarot INTEGER DEFAULT 0;
ALTER TABLE bindings ADD COLUMN extra_gacha INTEGER DEFAULT 0;
ALTER TABLE bindings ADD COLUMN free_forges INTEGER DEFAULT 0;
ALTER TABLE bindings ADD COLUMN free_forges_big INTEGER DEFAULT 0;
```

**道具效果说明：**
| 道具 | 效果 |
|------|------|
| 🍀 幸运草 | 下次签到50%暴击，额外获得基础值MP |
| 🛡️ 防御卷轴 | 下次决斗失败不损失MP |
| 🔮 塔罗券 | 可额外抽塔罗一次（无视每日限制） |
| 🎰 盲盒券 | 免费抽盲盒一次 |
| ⚒️ 小锻造锤 | 免费锻造一次 |
| ⚒️ 大锻造锤 | 免费锻造+高稀有度概率 |

### 3. 接下来该干嘛
- 机器人已重启（PID: 1703173）
- 测试 `/shop` 命令和所有道具效果

---
