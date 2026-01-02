#!/usr/bin/env python3
"""
RoyalBot 代码规范检查脚本

扫描常见错误模式，防止历史问题重演。

运行方式：
    python scripts/check_code.py
    或：python scripts/check_code.py --fix  (自动修复部分问题)
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# 颜色输出
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent
PLUGINS_DIR = ROOT_DIR / "plugins"
DATABASE_DIR = ROOT_DIR / "database"

# 检查规则
CHECKS = {
    "session_context": {
        "name": "数据库会话上下文管理",
        "severity": "error",
        "pattern": re.compile(
            r'session\s*=\s*get_session\(\)\s*$',  # 直接赋值，不用 with
            re.MULTILINE
        ),
        "exclude_in": ["# OK:", "# noqa:", "# fix:"],
        "message": "get_session() 返回上下文管理器，必须用 with 语句",
        "fix": "with get_session() as session:",
        "examples": [
            ("❌ 错误", "session = get_session()"),
            ("✅ 正确", "with get_session() as session:"),
        ]
    },

    "session_close": {
        "name": "数据库会话手动关闭",
        "severity": "warning",
        "pattern": re.compile(
            r'(?!Client)session\s*=\s*Session\(\)',  # 使用旧的 Session() 构造函数（排除 ClientSession）
            re.MULTILINE
        ),
        "exclude_in": ["# OK:", "# noqa:", "# fix:", "# context"],
        "message": "应使用 get_session() 上下文管理器代替手动管理",
        "fix": "with get_session() as session:",
        "examples": [
            ("❌ 错误", "session = Session()"),
            ("✅ 正确", "with get_session() as session:"),
        ]
    },

    "extbot_dynamic_attr": {
        "name": "ExtBot 动态属性",
        "severity": "error",
        "pattern": re.compile(
            r'(hasattr\(context\.bot,\s*[\'"]|context\.bot\.\w+\s*=)',  # 动态添加属性
            re.MULTILINE
        ),
        "exclude_in": ["# OK:", "# noqa:", "# fix:"],
        "message": "ExtBot 使用 __slots__，禁止动态添加属性",
        "fix": "使用模块级全局变量代替",
        "examples": [
            ("❌ 错误", "context.bot.active_pushes = {}"),
            ("✅ 正确", "ACTIVE_PUSHES = {}  # 模块级全局变量"),
        ]
    },

    "timezone_aware": {
        "name": "时区处理",
        "severity": "warning",
        "pattern": re.compile(
            r'datetime\.now\(\)\s*-\s*[a-zA-Z_]+\.[a-zA-Z_]+',  # 朴素 datetime 与可能有时区的对象属性相减
            re.MULTILINE
        ),
        "exclude_in": ["# OK:", "# noqa:", "# fix:", "tzinfo is not None", "timedelta"],
        "message": "datetime.now() 返回朴素时间，与可能有时区的对象运算会报错",
        "fix": "检查 tzinfo 或统一使用 datetime.now(timezone.utc)",
        "examples": [
            ("❌ 错误", "days = (datetime.now() - user.last_active).days"),
            ("✅ 正确", "now = datetime.now(timezone.utc) if obj.tzinfo else datetime.now()"),
        ]
    },

    "html_edit_method": {
        "name": "HTML 编辑方法",
        "severity": "error",
        "pattern": re.compile(
            r'\.edit_message_html\(',  # CallbackQuery 不支持这个方法
            re.MULTILINE
        ),
        "exclude_in": ["# OK:", "# noqa:", "# fix:"],
        "message": "CallbackQuery 不支持 edit_message_html()，需用 edit_message_text(parse_mode='HTML')",
        "fix": "edit_message_text(..., parse_mode='HTML')",
        "examples": [
            ("❌ 错误", "await query.edit_message_html('...')"),
            ("✅ 正确", "await query.edit_message_text('...', parse_mode='HTML')"),
        ]
    },

    "callback_conflict_pattern": {
        "name": "回调冲突风险",
        "severity": "info",
        "pattern": re.compile(
            r'CallbackQueryHandler\([^)]+pattern="[^"]*\^?\(',
            re.MULTILINE
        ),
        "exclude_in": ["# OK:", "# noqa:", "# fix:"],
        "message": "使用排除模式的回调可能导致与其他插件冲突，请确保排除列表完整",
        "fix": "检查排除模式是否包含所有相关回调前缀",
        "examples": [
            ("提示", "确保 start_menu.py 的排除模式包含所有插件回调前缀"),
        ]
    },

    "missing_timezone_import": {
        "name": "缺少时区导入",
        "severity": "info",
        "pattern": re.compile(
            r'datetime\.now\(timezone\.',
            re.MULTILINE
        ),
        "exclude_in": ["# OK:", "# noqa:", "# fix:", "from datetime import.*timezone"],
        "message": "使用 timezone 需要导入，检查是否已导入",
        "fix": "from datetime import datetime, timezone",
        "examples": [
            ("提示", "确保有 'from datetime import datetime, timezone'"),
        ]
    },
}


def check_file(filepath: Path) -> List[Tuple[str, int, int, str, str]]:
    """检查单个文件，返回问题列表"""
    issues = []

    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.splitlines()

        for check_name, check in CHECKS.items():
            for match in check["pattern"].finditer(content):
                # 计算匹配位置的行号
                line_num = content[:match.start()].count('\n') + 1
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""

                # 检查是否在排除列表中
                if any(excl in line_content for excl in check["exclude_in"]):
                    continue

                issues.append((
                    check["severity"],
                    line_num,
                    check["name"],
                    line_content.strip(),
                    check["message"]
                ))

    except Exception as e:
        print(f"{Colors.YELLOW}警告: 无法读取 {filepath}: {e}{Colors.END}")

    return issues


def scan_files() -> List[Tuple[Path, List]]:
    """扫描所有插件和数据库文件"""
    files_to_check = []

    # 扫描 plugins 目录
    if PLUGINS_DIR.exists():
        files_to_check.extend(PLUGINS_DIR.glob("*.py"))

    # 扫描 database 目录
    if DATABASE_DIR.exists():
        files_to_check.extend(DATABASE_DIR.glob("*.py"))

    results = []
    for filepath in files_to_check:
        issues = check_file(filepath)
        if issues:
            results.append((filepath, issues))

    return results


def print_results(results: List[Tuple[Path, List]]):
    """打印检查结果"""
    total_issues = sum(len(issues) for _, issues in results)

    if total_issues == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ 没有发现问题！{Colors.END}")
        return

    print(f"\n{Colors.BOLD}发现 {total_issues} 个问题：{Colors.END}\n")

    for filepath, issues in results:
        print(f"{Colors.BLUE}{filepath}{Colors.END}")
        print("-" * 60)

        # 按严重程度分组
        error_count = sum(1 for s, *_ in issues if s == "error")
        warning_count = sum(1 for s, *_ in issues if s == "warning")
        info_count = sum(1 for s, *_ in issues if s == "info")

        for severity, line_num, check_name, line_content, message in issues:
            if severity == "error":
                color = Colors.RED
                icon = "✗"
            elif severity == "warning":
                color = Colors.YELLOW
                icon = "⚠"
            else:
                color = Colors.BLUE
                icon = "ℹ"

            print(f"  {color}{icon} 第 {line_num} 行: {check_name}{Colors.END}")
            print(f"     {message}")
            if line_content:
                print(f"     {Colors.YELLOW}>{line_content}{Colors.END}")

            # 显示示例
            for check_name_key, check in CHECKS.items():
                if check["name"] == check_name:
                    for ex_type, ex_code in check.get("examples", []):
                        ex_color = Colors.GREEN if ex_type.startswith("✅") else Colors.RED
                        print(f"     {ex_color}{ex_type}: {ex_code}{Colors.END}")

        print()

    # 汇总统计
    print(f"{Colors.BOLD}统计：{Colors.END}")
    print(f"  文件数: {len(results)}")
    print(f"  {Colors.RED}错误: {error_count}{Colors.END}")
    print(f"  {Colors.YELLOW}警告: {warning_count}{Colors.END}")
    print(f"  {Colors.BLUE}提示: {info_count}{Colors.END}")


def print_examples():
    """打印常见错误示例"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}常见错误示例：{Colors.END}\n")

    examples = [
        {
            "title": "数据库会话管理",
            "error": "session = get_session()\nu = session.query(...)",
            "correct": "with get_session() as session:\n    u = session.query(...)"
        },
        {
            "title": "ExtBot 动态属性",
            "error": "context.bot.active_pushes = {}",
            "correct": "# 在模块顶部定义全局变量\nACTIVE_PUSHES = {}"
        },
        {
            "title": "HTML 编辑方法",
            "error": "await query.edit_message_html('...')",
            "correct": "await query.edit_message_text('...', parse_mode='HTML')"
        },
        {
            "title": "时区处理",
            "error": "days = (datetime.now() - user.last_active).days",
            "correct": "now = datetime.now(timezone.utc) if user.last_active.tzinfo else datetime.now()\ndays = (now - user.last_active).days"
        },
    ]

    for i, ex in enumerate(examples, 1):
        print(f"{Colors.BOLD}{i}. {ex['title']}{Colors.END}")
        print(f"{Colors.RED}❌ 错误:{Colors.END}")
        print(f"  {ex['error']}")
        print(f"{Colors.GREEN}✅ 正确:{Colors.END}")
        print(f"  {ex['correct']}\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="RoyalBot 代码规范检查")
    parser.add_argument("--examples", action="store_true", help="显示常见错误示例")
    parser.add_argument("--fix", action="store_true", help="尝试自动修复（未实现）")
    args = parser.parse_args()

    print(f"{Colors.BOLD}{Colors.BLUE}RoyalBot 代码规范检查{Colors.END}")
    print("=" * 60)

    if args.examples:
        print_examples()
        return

    results = scan_files()
    print_results(results)

    # 返回退出码
    total_errors = sum(1 for _, issues in results for s, *_ in issues if s == "error")
    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
