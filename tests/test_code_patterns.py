"""
代码模式测试 - 防止历史问题重演

这个测试扫描所有插件文件，确保没有使用错误的数据库会话管理模式。
如果检测到问题模式，测试会失败，防止错误代码进入仓库。
"""
import os
import re
from pathlib import Path
import pytest


# 获取项目根目录
ROOT_DIR = Path(__file__).parent.parent
PLUGINS_DIR = ROOT_DIR / "plugins"
DATABASE_DIR = ROOT_DIR / "database"


class TestCodePatterns:
    """代码模式测试 - 防止常见的错误模式"""

    def test_no_raw_session_in_plugins(self):
        """插件中不应直接使用 Session() 构造函数"""
        errors = []

        for py_file in PLUGINS_DIR.glob("*.py"):
            content = py_file.read_text(encoding='utf-8')
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                # 检查 session = Session() 模式（排除 ClientSession）
                if re.search(r'^(?!.*Client)session\s*=\s*Session\(\)', line):
                    # 排除注释行
                    if not line.strip().startswith('#'):
                        errors.append(f"{py_file.name}:{i} - 发现 'session = Session()'")

        if errors:
            error_msg = "\n".join(errors)
            pytest.fail(
                f"发现 {len(errors)} 处直接使用 Session() 的代码！\n"
                f"请使用 'with get_session() as session:' 代替\n\n"
                f"错误位置:\n{error_msg}"
            )

    def test_no_get_session_direct_assignment(self):
        """不应直接赋值 get_session() 的返回值"""
        errors = []

        for py_file in PLUGINS_DIR.glob("*.py"):
            content = py_file.read_text(encoding='utf-8')
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                # 检查 session = get_session() 模式（后面没有 with）
                if re.search(r'session\s*=\s*get_session\(\)\s*$', line):
                    # 排除注释行和 OK 标记
                    if not line.strip().startswith('#') and '# OK:' not in line:
                        errors.append(f"{py_file.name}:{i} - 发现 'session = get_session()'")

        if errors:
            error_msg = "\n".join(errors)
            pytest.fail(
                f"发现 {len(errors)} 处错误使用 get_session() 的代码！\n"
                f"get_session() 返回上下文管理器，必须用 with 语句：\n"
                f"'with get_session() as session:'\n\n"
                f"错误位置:\n{error_msg}"
            )

    def test_no_edit_message_html(self):
        """不应使用 edit_message_html()（CallbackQuery 不支持）"""
        errors = []

        for py_file in PLUGINS_DIR.glob("*.py"):
            content = py_file.read_text(encoding='utf-8')
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                if 'edit_message_html(' in line:
                    # 排除注释行
                    if not line.strip().startswith('#'):
                        errors.append(f"{py_file.name}:{i} - 发现 'edit_message_html()'")

        if errors:
            error_msg = "\n".join(errors)
            pytest.fail(
                f"发现 {len(errors)} 处使用 edit_message_html() 的代码！\n"
                f"CallbackQuery 不支持此方法，请使用：\n"
                f"'edit_message_text(..., parse_mode=\"HTML\")'\n\n"
                f"错误位置:\n{error_msg}"
            )

    def test_import_from_database_not_session(self):
        """插件应从 database 导入 get_session 而不是 Session"""
        errors = []

        for py_file in PLUGINS_DIR.glob("*.py"):
            content = py_file.read_text(encoding='utf-8')
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                # 检查是否导入 Session（但允许从 models 导入）
                if re.search(r'from database import.*\bSession\b', line):
                    # 排除 database 包内部的文件
                    if 'SessionError' not in line and ' declarative' not in line:
                        errors.append(f"{py_file.name}:{i} - 从 database 导入 Session")

        if errors:
            error_msg = "\n".join(errors)
            pytest.fail(
                f"发现 {len(errors)} 处导入 Session 的代码！\n"
                f"插件应使用 'from database import get_session' 代替\n\n"
                f"错误位置:\n{error_msg}"
            )

    def test_session_closed_in_with_block(self):
        """使用 with 语句时不应该手动 close()"""
        errors = []

        for py_file in PLUGINS_DIR.glob("*.py"):
            content = py_file.read_text(encoding='utf-8')
            lines = content.splitlines()

            # 找到 with get_session() 块
            in_with_block = False
            with_indent = 0

            for i, line in enumerate(lines, 1):
                stripped = line.lstrip()
                indent = len(line) - len(stripped)

                # 检测进入 with 块
                if re.search(r'with\s+get_session\(\)\s+as\s+session:', line):
                    in_with_block = True
                    with_indent = indent
                    continue

                # 检测退出 with 块
                if in_with_block and indent <= with_indent and stripped:
                    in_with_block = False

                # 在 with 块内检查 session.close()
                if in_with_block and 'session.close()' in line:
                    # 排除注释
                    if not stripped.startswith('#'):
                        errors.append(f"{py_file.name}:{i} - with 块内调用 session.close()")

        if errors:
            error_msg = "\n".join(errors)
            pytest.fail(
                f"发现 {len(errors)} 处在 with 块内手动 close() 的代码！\n"
                f"with 语句会自动关闭，不需要手动调用 close()\n\n"
                f"错误位置:\n{error_msg}"
            )


class TestSessionManagementSafety:
    """会话管理安全性测试"""

    def test_database_uses_context_manager(self):
        """database 包本身应正确实现上下文管理器"""
        from database.repository import get_session

        # 验证 get_session 返回的是上下文管理器
        import inspect
        result = get_session()
        assert hasattr(result, '__enter__'), "get_session() 必须返回上下文管理器"
        assert hasattr(result, '__exit__'), "get_session() 必须返回上下文管理器"

    def test_get_session_creates_new_session_each_time(self):
        """每次调用 get_session 应创建新的会话"""
        from database.repository import get_session

        ctx1 = get_session()
        ctx2 = get_session()

        # 应该是不同的上下文管理器实例
        assert ctx1 is not ctx2, "get_session() 每次应返回新的上下文管理器"


class TestImportConsistency:
    """导入一致性测试"""

    def test_repository_exports_get_session(self):
        """repository 应导出 get_session"""
        from database import repository
        assert hasattr(repository, 'get_session'), "repository 应导出 get_session"

    def test_database_package_exports_get_session(self):
        """database 包应导出 get_session"""
        from database import get_session
        assert callable(get_session), "database.get_session 应该是可调用的"
