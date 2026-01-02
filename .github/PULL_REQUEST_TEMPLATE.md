## 📋 变更说明

<!-- 简要描述这次 PR 的内容 -->

### 变更类型
- [ ] 🐛 Bug 修复
- [ ] ✨ 新功能
- [ ] 🎨 代码重构
- [ ] 📝 文档更新
- [ ] 🧪 测试相关
- [ ] 🔧 配置更改

---

## 📝 变更详情

<!-- 描述具体的变更内容 -->

**修改的文件：**
-

**新增的文件：**
-

---

## ✅ 检查清单

在提交 PR 前，请确保：

- [ ] 代码已通过本地测试 (`pytest tests/`)
- [ ] 代码检查通过 (`python3 scripts/check_code.py`)
- [ ] 已添加或更新相关测试
- [ ] 已更新 `ai.md` 记录变更
- [ ] 遵循项目代码规范：
  - 数据库操作使用 `with get_session() as session:`
  - 不使用 `session = Session()`
  - 不使用 `edit_message_html()`
  - 新增回调时更新 `start_menu.py` 排除模式

---

## 🔗 相关 Issue

<!-- 关联的 Issue 编号，如 Closes #123 -->

Closes #
