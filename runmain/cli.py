"""自动化测试框架命令行入口。"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import Optional, Sequence

if not getattr(sys, "frozen", False):
    project_root = str(Path(__file__).resolve().parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from core.bootstrap import bootstrap_cli_runtime, resolve_testcase_paths

bootstrap_cli_runtime()

from core.comdata import CommonData
from core.generator import Generator
from core.loader import ActionLoader
from core.runner import AutoTestRunner
from core.utils.u_config import parse_bool
from core.utils.u_file import clear_directory, file_copy
from core.utils.u_ini import edit_ini_file


# CLI 运行命令允许选择的自动化类型。
AUTOMATION_TYPES = {"http", "web"}
# CLI 运行命令允许选择的报告类型。
REPORT_TYPES = {"allure", "html"}
# CLI 运行命令允许选择的日志级别。
LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}
# CLI 支持覆盖的项目运行配置项，新增配置时在这里统一维护。
RUN_CONFIG_OPTIONS = (
    "auto_type",
    "report_type",
    "test_url",
    "log_level",
    "is_email",
)


class RunTestCase(argparse.Action):
    """解析并执行 `-r/--run` 测试命令。"""

    def __init__(self, nargs="+", **kwargs):
        super().__init__(nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if len(values) > 2:
            parser.error("-r/--run 最多接收项目名称和用例路径两个参数")
        setattr(namespace, self.dest, values)

    @staticmethod
    def run_test_case(
        values: Sequence[str],
        run_config: Optional[dict[str, str]] = None,
    ) -> int:
        """按命令行参数执行测试。"""
        project_name = values[0]
        testcases = values[1] if len(values) > 1 else ""
        CommonData.select_project(project_name)
        CommonData.RUN_DATA["testcases"] = resolve_testcase_paths(testcases)

        config_overrides = run_config or {}
        if config_overrides:
            config_file = CommonData.get_config_path()
            for name, value in config_overrides.items():
                edit_ini_file(config_file, "项目运行设置", name, value)
        ActionLoader.load_actions()
        return AutoTestRunner().run()


class CreateProject(argparse.Action):
    """解析并执行 `-c/--create` 项目创建命令。"""

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)

    @staticmethod
    def create_project(project_name: str) -> Path:
        """复制内置模板并以指定名称创建测试项目。"""
        project_name = project_name.strip()
        if not project_name:
            raise ValueError("项目名不能为空")

        testsuit_root = Path(CommonData.TEST_SUIT_DIR).resolve()
        project_path = (testsuit_root / project_name).resolve()
        if project_path.parent != testsuit_root:
            raise ValueError(f"项目名不合法：{project_name}")
        if project_path.exists():
            raise FileExistsError(f"测试项目已存在：{project_path}")

        testsuit_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(CommonData.TEMPLATE_PROJECT, project_path)
        print(f"自动化测试项目创建成功：{project_path}")
        return project_path


class LoadActions(argparse.Action):
    """解析并执行 `-l/--load` 关键字加载命令。"""

    def __init__(self, nargs=0, **kwargs):
        super().__init__(nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, True)

    @staticmethod
    def load_actions() -> int:
        """重新扫描关键字类并生成 action YAML 模板。"""
        registry = ActionLoader.load_actions()
        clear_directory(CommonData.BASE_KEYWORD)
        Generator.generate_actions()
        file_copy(CommonData.CUSTOM_KEYWORD_TEMP, CommonData.BASE_KEYWORD)
        print(f"action 关键字加载成功，共加载 {len(registry)} 个关键字类")
        return len(registry)


def create_parser() -> argparse.ArgumentParser:
    """创建 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        description="自动化测试框架命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "使用示例：\n"
            "  # 按项目配置运行全部用例\n"
            "  python runmain/cli.py -r my_http_test\n\n"
            "  # 运行一个或多个指定目录/用例\n"
            "  python runmain/cli.py -r my_http_test \"01登录;02稿件管理\"\n\n"
            "  # 覆盖项目运行配置\n"
            "  python runmain/cli.py -r my_http_test --auto_type http "
            "--report_type html\n\n"
            "  # 覆盖全部项目运行设置\n"
            "  python runmain/cli.py -r my_web_test --auto_type web "
            "--report_type allure --test_url https://example.test "
            "--log_level DEBUG --is_email no\n\n"
            "  # 创建测试项目\n"
            "  python runmain/cli.py -c new_project\n\n"
            "  # 重新加载并生成基础关键字模板\n"
            "  python runmain/cli.py -l\n\n"
            "说明：未指定用例路径时运行项目全部用例；未指定的运行设置使用项目 INI 现有值。"
        ),
    )
    parser.add_argument(
        "-help",
        action="help",
        help="显示完整帮助信息并退出",
    )
    commands = parser.add_mutually_exclusive_group()
    commands.add_argument(
        "-r", "--run", action=RunTestCase,
        metavar=("测试项目", "测试用例集"), help="执行测试；省略用例集时运行全部用例，多个路径使用分号分隔"
    )
    commands.add_argument(
        "-c", "--create", action=CreateProject,
        metavar="项目名", help="根据内置模板创建自动化测试项目"
    )
    commands.add_argument(
        "-l", "--load", action=LoadActions,
        help="重新加载并生成 action 基础关键字"
    )
    run_options = parser.add_argument_group("项目运行设置覆盖参数")
    run_options.add_argument("--auto_type", type=str.lower, choices=sorted(AUTOMATION_TYPES), help="自动化测试类型")  # noqa
    run_options.add_argument("--report_type", type=str.lower, choices=sorted(REPORT_TYPES), help="测试报告类型")   # noqa
    run_options.add_argument("--test_url", help="项目测试地址")
    run_options.add_argument("--log_level", type=str.upper, choices=sorted(LOG_LEVELS), help="日志打印级别")   # noqa
    run_options.add_argument("--is_email", type=_parse_bool, metavar="布尔值", help="是否发送测试报告邮件")
    return parser


def _parse_bool(value: str) -> str:
    """解析 CLI 布尔参数并转换为统一配置文本。"""
    try:
        return "yes" if parse_bool(value) else "no"
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def main(argv: Optional[Sequence[str]] = None) -> int:
    """解析命令行参数并执行对应操作。"""
    parser = create_parser()
    try:
        args = parser.parse_args(argv)
        config_overrides = {
            name: getattr(args, name)
            for name in RUN_CONFIG_OPTIONS
            if getattr(args, name) is not None
        }
        if config_overrides and args.run is None:
            parser.error("项目运行设置参数只能与 -r/--run 一起使用")
        if args.run is not None:
            return RunTestCase.run_test_case(args.run, config_overrides)
        if args.create is not None:
            CreateProject.create_project(args.create)
            return 0
        if args.load:
            LoadActions.load_actions()
            return 0
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        parser.error(str(error))

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
