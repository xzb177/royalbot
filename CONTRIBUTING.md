# 贡献指南

感谢你对 RoyalBot 的关注！本文档说明如何参与贡献。

## 🚀 快速开始

### 1. Fork 仓库
点击右上角的 Fork 按钮

### 2. 克隆你的 Fork
```bash
git clone https://github.com/YOUR_USERNAME/royalbot.git
cd royalbot
```

### 3. 创建功能分支
```bash
git checkout -b feature/your-feature-name
```

### 4. 安装依赖
```bash
pip install -r requirements.txt
```

## 📝 开发规范

### 代码风格

#### 数据库会话管理
```python
# ✅ 正确 - 使用上下文管理器
from database import get_session, UserBinding

with get_session() as session:
    user = session.query(UserBinding).filter_by(tg_id=user_id).first()
    user.points += 100
    session.commit()

# ❌ 错误 - 手动管理会话
from database import Session

session = Session()
user = session.query(UserBinding).filter_by(tg_id=user_id).first()
session.commit()
session.close()
```

#### 消息编辑
```python
# ✅ 正确
await query.edit_message_text(text, parse_mode='HTML')

# ❌ 错误 - CallbackQuery 不支持此方法
await query.edit_message_html(text)
```

#### 回调处理器
新增插件回调时，更新 `start_menu.py` 的排除模式：

```python
# 在排除模式中添加新的回调前缀
pattern="^(?!admin_|vip_|duel_accept|duel_reject|forge_|me_|buy_|shop_|wheel_|airdrop_|mission_|presence_|emby_|your_plugin_).*$"
```

### 提交信息规范

使用语义化提交信息：

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加每日签到功能` |
| `fix` | Bug 修复 | `fix: 修复数据库会话泄漏` |
| `refactor` | 重构 | `refactor: 优化数据库查询` |
| `docs` | 文档 | `docs: 更新 README` |
| `test` | 测试 | `test: 添加会话管理测试` |
| `style` | 代码格式 | `style: 统一代码风格` |

### 测试要求

提交前确保测试通过：

```bash
# 运行所有测试
python3 -m pytest tests/ -v

# 运行代码检查
python3 scripts/check_code.py
```

## 📋 提交流程

### 1. 推送到你的 Fork
```bash
git push origin feature/your-feature-name
```

### 2. 创建 Pull Request
1. 访问原仓库的 GitHub 页面
2. 点击 "New Pull Request"
3. 选择你的功能分支
4. 填写 PR 模板
5. 等待 CI 检查通过

### 3. 响应审查
- 根据反馈修改代码
- 更新 PR
- 等待最终批准

## 🧪 添加新功能

### 创建新插件

1. 在 `plugins/` 目录创建文件 `your_plugin.py`
2. 实现插件逻辑
3. 在 `plugins/your_plugin.py` 中导出 `register(app)` 函数
4. 在 `main.py` 中导入并注册

### 示例模板

```python
"""
插件名称
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database import get_session, UserBinding
from utils import reply_with_auto_delete

async def your_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """命令处理函数"""
    user_id = update.effective_user.id

    with get_session() as session:
        user = session.query(UserBinding).filter_by(tg_id=user_id).first()
        # 处理逻辑

    await reply_with_auto_delete(update.message, "响应内容")

def register(app):
    """注册处理器"""
    app.add_handler(CommandHandler("your_command", your_command))
```

## 🔍 调试技巧

### 查看日志
```bash
tail -f /tmp/royalbot.log
```

### 重启机器人
```bash
/root/royalbot/restart.sh
```

### 运行特定测试
```bash
pytest tests/test_database.py::TestUserRepository::test_create_user -v
```

## 📖 相关文档

- [代码质量保障](docs/CODE_QUALITY.md)
- [开发备忘录](ai.md)
- [更新日志](CHANGELOG.md)

## ❓ 获取帮助

- 提 Issue 描述问题
- 加入讨论组交流
- 查看 Wiki 文档

## 📜 许可证

本项目采用 MIT 许可证。
