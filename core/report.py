import base64
import mimetypes
import os
from html import escape
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

import allure
from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.comdata import CommonData
from core.logger import Log


# pytest-html 结果表中描述列的插入位置。
DESCRIPTION_COLUMN_INDEX = 1


class HtmlReportBeautifier:
    """通过 pytest-html 公共钩子加载主题，并内嵌失败产物。

    保留 pytest-html 的结果数据、日志、筛选、排序和折叠行为；模板中的
    CSS/JavaScript 仅负责展示。资源从 CommonData 的内置模板目录读取，
    兼容源码运行和 PyInstaller 的静态资源目录。
    """

    @staticmethod
    def _render(template_name: str, **context: Any) -> str:
        template_dir = Path(CommonData.TEMPLATE_DIR) / "html_report"
        environment = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(("html",)),
            keep_trailing_newline=True,
        )
        return environment.get_template(template_name).render(**context)

    @classmethod
    def add_summary(cls, prefix: Any, session: Any = None) -> None:
        """把主题、展示脚本和页面装饰内联到 pytest-html 汇总钩子。"""
        if not any('id="kw-report-style"' in str(fragment) for fragment in prefix):
            prefix.append(cls._render("report.html"))
        if session is not None and not any('id="kw-report-count"' in str(fragment) for fragment in prefix):
            # 阶段错误可能为一个用例产生多条结果，不能用结果行数作为用例总数。
            total = int(session.testscollected)
            prefix.append(f'<span id="kw-report-count" data-total="{total}" hidden></span>')

    @staticmethod
    def add_table_header(cells: list) -> None:
        """保留原生可排序列，增加既有的描述列并移除 Links 列。"""
        cells.insert(
            DESCRIPTION_COLUMN_INDEX,
            '<th class="col-description">描述 / Description</th>',
        )
        if cells:
            cells.pop()

    @staticmethod
    def add_table_row(report: Any, cells: list) -> None:
        description = escape(str(getattr(report, "description", "")))
        cells.insert(
            DESCRIPTION_COLUMN_INDEX,
            f'<td class="col-description">{description}</td>',
        )
        if cells:
            cells.pop()

    @staticmethod
    def _artifact(file_path: Optional[str], config: Any) -> Optional[dict]:
        if not file_path:
            return None
        path = Path(file_path)
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        try:
            if config.getoption("self_contained_html", default=False):
                content = base64.b64encode(path.read_bytes()).decode("ascii")
                url = f"data:{mime_type};base64,{content}"
            else:
                report_path = config.getoption("htmlpath", default=None)
                report_dir = (
                    Path(os.path.expandvars(report_path)).expanduser().absolute().parent
                    if report_path else Path(CommonData.get_html_path())
                )
                url = quote(
                    Path(os.path.relpath(path, report_dir)).as_posix(), safe="/._-"
                )
        except OSError:
            Log().logger.exception("HTML 报告失败产物读取失败：%s", file_path)
            return None
        return {"url": url, "name": path.name, "mime_type": mime_type}

    @classmethod
    def attach_failure_artifacts(
        cls,
        item: Any,
        report: Any,
        video_paths: list[str],
        trace_path: Optional[str],
        screenshot_path: Optional[str],
    ) -> None:
        pytest_html = item.config.pluginmanager.getplugin("html")
        if pytest_html is None:
            Log().logger.warning("未加载 pytest-html，无法添加失败产物")
            return
        screenshot = cls._artifact(screenshot_path, item.config)
        videos = [
            artifact for path in video_paths
            if (artifact := cls._artifact(path, item.config)) is not None
        ]
        trace = cls._artifact(trace_path, item.config)
        if not screenshot and not videos and not trace:
            return
        extras = list(getattr(report, "extras", []))
        extras.append(pytest_html.extras.html(cls._render(
            "artifacts.html", screenshot=screenshot, videos=videos, trace=trace,
        )))
        report.extras = extras


def attach_html_failure_artifacts(
    item: Any,
    report: Any,
    video_paths: list[str],
    trace_path: Optional[str],
    screenshot_path: Optional[str],
) -> None:
    """向 HTML 报告的失败详情添加截图、录像和 Trace。"""
    HtmlReportBeautifier.attach_failure_artifacts(
        item, report, video_paths, trace_path, screenshot_path,
    )


def attach_allure_failure_artifacts(
    video_paths: list[str],
    trace_path: Optional[str],
    screenshot_path: Optional[str],
) -> None:
    """向 Allure 报告添加失败截图、录像和 Trace。"""
    if screenshot_path:
        allure.attach.file(
            screenshot_path,
            name="失败截图",
            attachment_type=allure.attachment_type.PNG,
        )
    for index, video_path in enumerate(video_paths, start=1):
        allure.attach.file(
            video_path,
            name=f"失败录像 {index}",
            attachment_type="video/webm",
            extension="webm",
        )
    if trace_path:
        allure.attach.file(
            trace_path,
            name="Playwright Trace",
            attachment_type="application/zip",
            extension="zip",
        )


def _build_html_artifact_url(file_path: str) -> str:
    """生成相对于 HTML 报告目录的 URL 安全路径。"""
    relative_path = os.path.relpath(file_path, CommonData.get_html_path())
    return quote(Path(relative_path).as_posix(), safe="/._-")


def add_html_results_summary(prefix: Any, session: Any = None) -> None:
    """在 HTML 报告中内联 V3 主题和展示模板。"""
    HtmlReportBeautifier.add_summary(prefix, session)


def add_html_results_table_header(cells: list) -> None:
    """在 HTML 报告结果表中添加 Description 列。"""
    HtmlReportBeautifier.add_table_header(cells)


def add_html_results_table_row(report: Any, cells: list) -> None:
    """向 HTML 报告结果行写入测试项描述。"""
    HtmlReportBeautifier.add_table_row(report, cells)
