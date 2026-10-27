"""CLI 源码与冻结程序的早期运行环境引导。"""

from pathlib import Path


def bootstrap_cli_runtime() -> None:
    """统一初始化源码 CLI 和冻结 CLI 的早期运行环境。"""

    from core.utils.u_playwright import configure_playwright_runtime

    configure_playwright_runtime()


def resolve_testcase_paths(testcases: str) -> list[str]:
    """将 CLI 用例参数解析为当前项目内的绝对路径。"""
    from core.comdata import CommonData
    from core.utils.u_str import split_semicolon_list

    testcase_root = Path(CommonData.get_testcase_path()).resolve()
    raw_paths = [
        value.strip()
        for value in split_semicolon_list(testcases)
        if value.strip()
    ]
    if not raw_paths:
        return [str(testcase_root)]

    resolved_paths = []
    for raw_path in raw_paths:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            project_relative = testcase_root / candidate
            candidate = (
                project_relative
                if project_relative.exists()
                else Path.cwd() / candidate
            )
        candidate = candidate.resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"测试用例路径不存在：{candidate}")
        if not candidate.is_relative_to(testcase_root):
            raise ValueError(f"测试用例路径不在当前项目中：{candidate}")
        relative_parts = candidate.relative_to(testcase_root).parts
        if relative_parts and relative_parts[0] == "casedata":
            raise ValueError(f"casedata目录不能作为测试用例运行：{candidate}")
        if candidate.is_file() and candidate.parent == testcase_root:
            raise ValueError(f"testcase根目录中的YAML不作为测试用例：{candidate}")
        if candidate.is_file() and candidate.suffix.lower() != ".yaml":
            raise ValueError(f"测试用例文件必须使用.yaml扩展名：{candidate}")
        candidate_text = str(candidate)
        if candidate_text not in resolved_paths:
            resolved_paths.append(candidate_text)
    return resolved_paths


__all__ = ["bootstrap_cli_runtime", "resolve_testcase_paths"]
