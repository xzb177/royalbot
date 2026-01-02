# RoyalBot 代码质量保障体系

本文档说明 RoyalBot 的代码质量保障措施。

## 📋 检查清单

在提交代码前，请确保：

### 1. 本地测试
```bash
# 运行所有测试
python3 -m pytest tests/ -v

# 运行代码检查
python3 scripts/check_code.py
```

### 2. 代码规范

#### 数据库操作
```python
# ✅ 正确
from database import get_session

with get_session() as session:
    user = session.query(UserBinding).filter_by(tg_id=123).first()
    session.commit()

# ❌ 错误
from database import Session

session = Session()
user = session.query(UserBinding).filter_by(tg_id=123).first()
session.commit()
session.close()
```

#### HTML 消息编辑
```python
# ✅ 正确
await query.edit_message_text(text, parse_mode='HTML')

# ❌ 错误
await query.edit_message_html(text)  # 此方法不存在
```

#### 新增回调
如果新增插件 CallbackQuery，在 `start_menu.py` 的排除模式中添加前缀：
```python
# 新回调前缀
pattern="^(?!admin_|vip_|duel_accept|duel_reject|forge_|me_|buy_|shop_|wheel_|airdrop_|mission_|presence_|emby_|your_new_prefix_).*$"
```

### 3. 提交前检查
```bash
# Git 提交会自动运行 pre-commit hook
git commit -m "message"

# 如果需要跳过（不推荐）
git commit --no-verify -m "message"
```

## 🔄 CI/CD 流程

### GitHub Actions 自动运行

触发条件：
- Push 到 `main` 或 `dev` 分支
- 创建/更新 Pull Request

检查项目：
1. **代码模式测试** - 检测错误的数据库会话管理
2. **单元测试** - 28 个测试用例
3. **代码覆盖率** - 统计测试覆盖范围
4. **Flake8 语法检查** - Python 代码质量
5. **代码检查脚本** - 7 种错误模式检测

### PR 合并要求

**建议在 GitHub 仓库设置中配置：**

1. 进入 `Settings` → `Branches`
2. 添加分支保护规则 `main`
3. 启用以下选项：
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - 选择必需的检查：`Tests`
   - ✅ Require pull request reviews before merging
   - ✅ Dismiss stale reviews when new commits are pushed

## 📁 测试文件结构

```
tests/
├── conftest.py              # 测试配置和 fixtures
├── test_achievement.py      # 成就系统测试
├── test_code_patterns.py    # 代码模式测试（防止历史问题）
└── test_database.py         # 数据库层测试
```

## 🛠️ 开发工作流

1. **拉取最新代码**
   ```bash
   git checkout main
   git pull
   git checkout -b feature/your-feature
   ```

2. **开发和测试**
   ```bash
   # 编写代码
   # 运行测试
   python3 -m pytest tests/ -v
   ```

3. **提交变更**
   ```bash
   git add .
   git commit -m "feat: 描述"
   git push origin feature/your-feature
   ```

4. **创建 PR**
   - 在 GitHub 上创建 Pull Request
   - 填写 PR 模板
   - 等待 CI 检查通过
   - 请求审查

5. **合并**
   - CI 检查通过
   - 审查通过
   - 合并到 main

## 📊 测试覆盖率目标

| 模块 | 当前目标 | 优先级 |
|------|---------|--------|
| database/ | >80% | 高 |
| plugins/ | >60% | 中 |
| tests/ | 100% | 高 |

## 🚨 常见问题

### Q: 测试失败怎么办？
A: 检查错误日志，修复后重新提交。本地先用 `pytest tests/` 验证。

### Q: 如何跳过 pre-commit hook？
A: `git commit --no-verify`（不推荐，应在 CI 中修复）

### Q: CI 和本地测试结果不一致？
A: 检查 Python 版本和依赖版本是否一致。
