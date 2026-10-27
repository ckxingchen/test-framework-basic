import os
import subprocess
from typing import Dict, List

import pytest

from core.comdata import CommonData
from core.logger import Log
from core.send_email import ReportEmailSender
from core.utils.u_config import parse_bool
from core.utils.u_file import clear_directory


# 框架当前支持的测试报告类型。
SUPPORTED_REPORT_TYPES = {"allure", "html"}
# 自动发送报告邮件时使用的默认正文。
EMAIL_CONTENT = "本邮件由系统自动发出，无需回复！\n各位同事，大家好，以下为本次测试报告!"


class AutoTestRunner:
    """根据项目配置执行 YAML 测试，并生成及发送测试报告。"""

    def __init__(self) -> None:
        self._run_config: Dict[str, str] = CommonData.get_config_data()["项目运行设置"]

    def run(self, run_all: bool = False) -> int:
        """执行测试流程并返回 pytest 退出码。"""
        logger = Log().logger
        logger.info(f"{'- ' * 20}【自动化测试开始】{'- ' * 20}")
        try:
            self._log_run_config()
            report_type = self._run_config["report_type"].lower()
            self._validate_report_type(report_type)

            if report_type == "allure":
                clear_directory(CommonData.get_allure_result_path())

            pytest_exit_code = pytest.main(
                self._build_pytest_args(report_type, run_all)
            )

            if report_type == "allure":
                self._generate_allure_report()

            if self._should_send_email():
                ReportEmailSender().send_report(
                    content=EMAIL_CONTENT,
                    report_type=report_type,
                )
                print(f"邮件发送成功：{report_type}")

            return int(pytest_exit_code)
        finally:
            logger.info(f"{'* ' * 20}【自动化测试结束】{'* ' * 20}")

    def _log_run_config(self) -> None:
        """记录当前项目的核心运行配置。"""
        Log().logger.info(
            "加载运行设置 ==> 自动化测试类型：%s，测试报告类型：%s，"
            "项目测试地址：%s，是否发送邮件：%s",
            self._run_config["auto_type"],
            self._run_config["report_type"],
            self._run_config["test_url"],
            self._run_config["is_email"],
        )

    @staticmethod
    def _validate_report_type(report_type: str) -> None:
        """确保配置中的报告类型受框架支持。"""
        if report_type not in SUPPORTED_REPORT_TYPES:
            message = f"暂不支持此报告类型:{report_type}"
            Log().logger.error(message)
            raise ValueError(message)

    def _build_pytest_args(self, report_type: str, run_all: bool) -> List[str]:
        """构建指定报告类型对应的 pytest 参数。"""
        if report_type == "allure":
            report_args = [f"--alluredir={CommonData.get_allure_result_path()}"]  # noqa
        else:
            report_args = [
                f"--html={os.path.join(CommonData.get_html_path(), 'auto_reports.html')}",
                "--self-contained-html",
            ]
        run_args = ["-sv"]
        return [
            "-c",
            CommonData.get_pytest_ini_path(),
            *run_args,
            *report_args,
            *CommonData.get_testcases(run_all),
        ]

    @staticmethod
    def _generate_allure_report() -> None:
        """同步调用 Allure CLI，确保后续邮件读取到完整报告。"""
        result_path = CommonData.get_allure_result_path()
        report_path = CommonData.get_allure_report_path()
        command = f'allure generate "{result_path}" -o "{report_path}" --clean'
        run_options = {"shell": True, "check": True}
        if os.name == "nt":
            run_options["creationflags"] = subprocess.CREATE_NO_WINDOW   # noqa
        subprocess.run(command, **run_options)

    def _should_send_email(self) -> bool:
        """判断当前配置是否启用邮件发送。"""
        return parse_bool(
            self._run_config["is_email"],
            name="is_email",
        )
