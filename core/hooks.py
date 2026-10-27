import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict

import pytest

from core import report as report_handler
from core.collector import YamlFileCollector
from core.comdata import CommonData
from core.logger import Log
from core.utils.u_file import clear_directory
from keywords.web.page import PageManager


# Pytest 收集时需要排除的前后置文件名。
FIXTURE_FILE_NAMES = {
    "测试集前置",
    "测试集后置",
    "测试用例前置",
    "测试用例后置",
}

_CASE_DURATIONS: Dict[str, float] = {}
_CASE_RESULTS: Dict[str, Dict[str, Any]] = {}


def pytest_sessionstart(session) -> None:
    """测试会话开始时清理当前自动化类型的失败产物。"""
    _CASE_DURATIONS.clear()
    _CASE_RESULTS.clear()
    if not CommonData.RUN_DATA.get("project_name"):
        return
    try:
        run_config = CommonData.get_config_data()["项目运行设置"]
        auto_type = run_config["auto_type"].lower()
        if auto_type == "web":
            artifact_options = PageManager.get_artifact_options()
            if artifact_options["video"]:
                clear_directory(CommonData.get_artifact_path("video"))
            if artifact_options["trace"]:
                clear_directory(CommonData.get_artifact_path("trace"))
    except Exception:
        Log().logger.exception("失败产物目录初始化失败")


def pytest_collect_file(parent: pytest.Collector, file_path: Path):
    """仅收集当前项目 testcase 目录中的用例 YAML。"""
    path = Path(str(file_path))
    if path.suffix.lower() != ".yaml" or path.stem in FIXTURE_FILE_NAMES:
        return None
    if not CommonData.RUN_DATA.get("project_name"):
        return None

    testcase_root = Path(CommonData.get_testcase_path()).resolve()
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(testcase_root):
        return None
    relative_parts = resolved_path.relative_to(testcase_root).parts
    if relative_parts and relative_parts[0] == "casedata":
        return None
    if resolved_path.parent == testcase_root:
        return None
    return YamlFileCollector.from_parent(parent=parent, path=file_path)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """补充测试描述，并为失败用例添加对应类型的失败产物。"""
    outcome = yield
    report = outcome.get_result()
    report.description = str(item.name)

    if report.failed:
        item._case_result = "failed"
        if call.excinfo is not None and not item._case_error:
            error = call.excinfo.value
            item._case_error = f"{type(error).__name__}: {error}"
    elif report.skipped and item._case_result != "failed":
        item._case_result = "skipped"

    if _is_failure_report(report):
        item._case_failed = True

    if getattr(item, "_case_failed", False):
        _attach_failure_artifacts(item, report)

    export_case_result(item, report)


def export_case_result(item, report) -> None:
    """将用例最终状态写入可由 Worker 回传的 pytest Report。"""
    if report.when != "teardown":
        return
    report.framework_case_result = item._case_result
    report.framework_case_error = item._case_error
    report.framework_case_path = os.path.relpath(
        item.case_path,
        CommonData.get_testcase_path(),
    ).replace(os.sep, "/")
    report.framework_case_name = item.case_name
    report.framework_suite_dir = os.path.dirname(
        report.framework_case_path
    ).replace(os.sep, "/")
    report.framework_data_row = item.data_row


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """汇总串行用例的最终执行结果。"""
    node_id = str(report.nodeid)
    _CASE_DURATIONS[node_id] = _CASE_DURATIONS.get(node_id, 0.0) + float(
        getattr(report, "duration", 0.0)
    )
    if report.when != "teardown":
        return
    status = getattr(report, "framework_case_result", None)
    case_path = getattr(report, "framework_case_path", None)
    if status is None or case_path is None:
        return
    _CASE_RESULTS[node_id] = {
        "case_path": case_path,
        "case_name": getattr(report, "framework_case_name", report.nodeid),
        "suite_dir": getattr(report, "framework_suite_dir", ""),
        "status": status,
        "duration_ms": round(_CASE_DURATIONS.get(node_id, 0.0) * 1000),
        "error_message": getattr(report, "framework_case_error", "") or None,
        "data_row": getattr(report, "framework_data_row", None),
    }


def _is_failure_report(report: Any) -> bool:
    """判断当前测试阶段是否属于需要保留产物的失败。"""
    if report.when not in {"setup", "call", "teardown"}:
        return False
    is_xfail = hasattr(report, "wasxfail")
    return (report.skipped and is_xfail) or (report.failed and not is_xfail)


def _attach_failure_artifacts(item: pytest.Item, report: Any) -> None:
    """将当前用例的失败截图、录像和 Trace 添加到报告。"""
    if getattr(item, "_artifacts_attached", False):
        return

    artifacts = getattr(item, "_artifact_paths", None) or {}
    video_paths = [
        path
        for path in artifacts.get("videos", [])
        if os.path.isfile(path)
    ]
    trace_path = artifacts.get("trace")
    if trace_path and not os.path.isfile(trace_path):
        trace_path = None
    screenshot_path = getattr(item, "_failure_screenshot_path", None)
    if screenshot_path and not os.path.isfile(screenshot_path):
        screenshot_path = None
    if not screenshot_path and not video_paths and not trace_path:
        return

    run_config = CommonData.get_config_data()["项目运行设置"]
    report_type = run_config["report_type"].lower()
    if report_type == "html":
        report_handler.attach_html_failure_artifacts(
            item,
            report,
            video_paths,
            trace_path,
            screenshot_path,
        )
    elif report_type == "allure":
        report_handler.attach_allure_failure_artifacts(
            video_paths,
            trace_path,
            screenshot_path,
        )
    else:
        return
    item._artifacts_attached = True


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: Any) -> None:
    """统计本次执行结果，写入运行数据并记录汇总日志。"""
    del exitstatus
    statistics = terminalreporter.stats
    result_reports = [
        report
        for result_name in ("passed", "failed", "error", "skipped")
        for report in statistics.get(result_name, ())
    ]
    executed_count = len(
        {
            report.nodeid
            for report in result_reports
            if getattr(report, "nodeid", None)
        }
    )
    collected_count = getattr(terminalreporter, "_numcollected", 0)
    summary = {
        "总数": collected_count or executed_count,
        "成功": len(statistics.get("passed", ())),
        "失败": len(statistics.get("failed", ())),
        "错误": len(statistics.get("error", ())),
        "跳过": len(statistics.get("skipped", ())),
    }
    total_count = summary["总数"]
    summary["成功率"] = (
        round(summary["成功"] / total_count * 100, 2) if total_count else 0.0
    )

    run_data = getattr(CommonData, "RUN_DATA", None)
    if run_data is not None:
        run_data["result"] = summary

    _write_case_results()

    Log().logger.info(_format_execution_summary(summary))


def _write_case_results() -> None:
    """Write a stable machine-readable result file for remote Agents."""
    report_root = Path(CommonData.get_project_path()) / "report"
    report_root.mkdir(parents=True, exist_ok=True)
    result_path = report_root / "case_results.json"
    temp_path = result_path.with_suffix(".json.tmp")
    results = sorted(
        _CASE_RESULTS.values(),
        key=lambda item: (item["case_path"], item["case_name"]),
    )
    try:
        temp_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        temp_path.replace(result_path)
    except OSError:
        Log().logger.exception("用例结果文件写入失败：%s", result_path)


def _format_execution_summary(summary: Dict[str, Any]) -> str:
    """将执行统计格式化为日志文本。"""
    return (
        "\n本次执行情况如下：\n"
        f"总用例数为：{summary['总数']}\n"
        f"通过用例数：{summary['成功']}\n"
        f"失败用例数：{summary['失败']}\n"
        f"错误用例数：{summary['错误']}\n"
        f"跳过用例数：{summary['跳过']}\n"
        f"通过率为：{summary['成功率']}"
    )


def pytest_html_report_title(report) -> None:
    """在首次生成报告前加载主题，兼容逐用例生成报告。"""
    report_handler.HtmlReportBeautifier.add_summary(report.additional_summary["prefix"])


def pytest_html_results_summary(prefix, summary, postfix, session) -> None:
    """在 HTML 报告中加载展示模板；已加载时保持幂等。"""
    del summary, postfix
    report_handler.add_html_results_summary(prefix, session)


def pytest_html_results_table_header(cells) -> None:
    """在 HTML 报告结果表中添加 Description 列。"""
    report_handler.add_html_results_table_header(cells)


def pytest_html_results_table_row(report, cells) -> None:
    """向 HTML 报告结果行写入测试项描述。"""
    report_handler.add_html_results_table_row(report, cells)
