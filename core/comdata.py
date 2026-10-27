import os
import sys
from pathlib import Path
from core.utils.u_excel import ExcelReader
from core.utils.u_ini import load_ini


def _get_frozen_project_root() -> str:
    """根据 PyInstaller 可执行文件位置获取外部项目根目录。

    打包程序约定放在 ``<项目根>/driver`` 内部。以可执行文件路径中最近
    的 ``driver`` 目录为锚点，取其父目录作为项目根，避免 CLI、GUI 的
    onedir/app bundle 层级差异影响外部工作目录。
    """
    executable_path = Path(sys.executable).resolve()

    for candidate in executable_path.parents:
        if candidate.name.casefold() == 'driver':
            return str(candidate.parent)
    raise RuntimeError(
        "打包程序必须位于<项目根>/driver目录内："
        f"{executable_path}"
    )


if getattr(sys, 'frozen', False):
    _project_root = _get_frozen_project_root()
    _resource_root = os.path.abspath(
        getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    )
else:
    _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
    _resource_root = _project_root


class CommonData(object):
    """公共路径类"""

    # 运行时可变状态，名称保持兼容现有调用方。
    RUN_DATA = {
        "project_name": "",
        "testcases": [],
    }

    # 项目数据根目录。
    PROJECT_ROOT: str = _project_root
    # PyInstaller 内置资源根目录。
    RESOURCE_ROOT: str = _resource_root
    # 驱动和构建产物目录。
    DRIVER_DIR: str = os.path.join(PROJECT_ROOT, "driver")
    # 内置关键字源码目录。
    KEYWORDS_DIR: str = os.path.join(PROJECT_ROOT, "keywords")
    # 测试项目根目录。
    TEST_SUIT_DIR: str = os.path.join(PROJECT_ROOT, "testsuits")
    # 项目根目录下的 Pytest 配置文件。
    PYTEST_INI: str = os.path.join(PROJECT_ROOT, "pytest.ini")
    # 内置静态资源目录。
    STATIC_DIR: str = os.path.join(RESOURCE_ROOT, "static")
    # 关键字 YAML 模板输出目录。
    BASE_KEYWORD: str = os.path.join(PROJECT_ROOT, "action")
    # 项目和 YAML 模板目录。
    TEMPLATE_DIR: str = os.path.join(STATIC_DIR, "template")
    # 自定义关键字 YAML 模板。
    CUSTOM_KEYWORD_TEMP: str = os.path.join(
        TEMPLATE_DIR,
        "自定义关键字.yaml",
    )
    # 自定义关键字 Python 模板。
    KEYWORDS_TEMP: str = os.path.join(TEMPLATE_DIR, "keyword.py")
    # 测试项目目录模板。
    TEMPLATE_PROJECT: str = os.path.join(TEMPLATE_DIR, "project")
    # 测试用例模板。
    TEMPLATE_CASE: str = os.path.join(TEMPLATE_DIR, "case.yaml")
    # 前后置步骤模板。
    TEMPLATE_FIXTURE: str = os.path.join(TEMPLATE_DIR, "fixture.yml")
    # 业务关键字模板。
    TEMPLATE_BUSINESS: str = os.path.join(TEMPLATE_DIR, "business.yaml")

    @classmethod
    def select_project(cls, project_name: str) -> None:
        """设置当前工程，并清空上一个工程的用例选择。"""
        if not isinstance(project_name, str) or not project_name:
            raise ValueError("工程名称不能为空")
        cls.RUN_DATA["project_name"] = project_name
        cls.RUN_DATA["testcases"] = []

    @classmethod
    def get_project_name(cls):
        """获取项目名称"""
        project_name = cls.RUN_DATA['project_name']
        if not project_name:
            raise KeyError('未指定项目，请指定要运行的项目名称！')
        return project_name

    @classmethod
    def get_testcases(cls, all_flag=False):
        """获取运行用例数据"""
        if (not cls.RUN_DATA['testcases']) and all_flag:
            return [cls.get_project_path()]
        else:
            return cls.RUN_DATA['testcases']

    @classmethod
    def get_pytest_ini_path(cls):
        """获取与外部工作目录同级的 Pytest 配置文件。"""
        if not os.path.isfile(cls.PYTEST_INI):
            raise FileNotFoundError(f'Pytest配置文件不存在：{cls.PYTEST_INI}')
        return cls.PYTEST_INI

    @classmethod
    def get_project_path(cls):
        """获取项目路径"""
        project_path = os.path.join(cls.TEST_SUIT_DIR, cls.get_project_name())
        if not os.path.exists(project_path):
            raise KeyError('项目{}目录不存在！'.format(project_path))
        return project_path

    @classmethod
    def get_business_path(cls):
        """获取项目路径"""
        business_path = os.path.join(cls.get_project_path(), 'business')
        if not os.path.exists(business_path):
            raise KeyError('业务关键字{}目录不存在！'.format(business_path))
        return business_path

    @classmethod
    def get_testcase_path(cls):
        """获取项目路径"""
        testcase_path = os.path.join(cls.get_project_path(), 'testcase')
        if not os.path.exists(testcase_path):
            raise KeyError('测试用例{}目录不存在！'.format(testcase_path))
        return testcase_path

    @classmethod
    def get_log_path(cls):
        """获取日志目录，不存在时自动创建。"""
        log_path = os.path.join(cls.get_project_path(), 'log')
        os.makedirs(log_path, exist_ok=True)
        return log_path

    @classmethod
    def get_allure_report_path(cls):
        """获取 Allure 报告目录，不存在时自动创建。"""
        allure_report_path = os.path.join(cls.get_project_path(), 'report', 'allure', 'report')
        os.makedirs(allure_report_path, exist_ok=True)
        return allure_report_path

    @classmethod
    def get_allure_result_path(cls):
        """获取 Allure 结果目录，不存在时自动创建。"""
        allure_result_path = os.path.join(cls.get_project_path(), 'report', 'allure', 'result')
        os.makedirs(allure_result_path, exist_ok=True)
        return allure_result_path

    @classmethod
    def get_html_path(cls):
        """获取 HTML 报告目录，不存在时自动创建。"""
        html_path = os.path.join(cls.get_project_path(), 'report', 'html')
        os.makedirs(html_path, exist_ok=True)
        return html_path

    @classmethod
    def get_pytest_temp_path(cls):
        """获取当前项目专用的 pytest 临时目录。"""
        report_path = os.path.join(cls.get_project_path(), 'report')
        os.makedirs(report_path, exist_ok=True)
        return os.path.join(report_path, '.pytest_tmp')

    @classmethod
    def get_artifacts_path(cls):
        """根据报告类型获取 artifacts 目录，不存在时自动创建。"""
        report_type = cls.get_config_data()["项目运行设置"][
            "report_type"
        ].lower()
        report_root = os.path.join(cls.get_project_path(), 'report')
        report_dirs = {
            'html': os.path.join(report_root, 'html'),
            'allure': os.path.join(report_root, 'allure'),
        }
        try:
            report_path = report_dirs[report_type]
        except KeyError as error:
            raise ValueError(f'暂不支持此报告类型:{report_type}') from error
        artifacts_path = os.path.join(report_path, 'artifacts')
        os.makedirs(artifacts_path, exist_ok=True)
        return artifacts_path

    @classmethod
    def get_artifact_path(cls, artifact_type: str):
        """获取指定类型的失败产物目录，不存在时自动创建。"""
        artifact_path = os.path.join(
            cls.get_artifacts_path(), artifact_type
        )
        os.makedirs(artifact_path, exist_ok=True)
        return artifact_path

    @classmethod
    def get_config_path(cls):
        """获取项目配置文件路径"""
        config_path = os.path.join(cls.get_project_path(), 'config', '配置文件.ini')
        if not os.path.exists(config_path):
            raise KeyError('配置{}文件不存在！'.format(config_path))
        return config_path

    @classmethod
    def get_config_data(cls):
        """获取配置文件信息"""
        return load_ini(cls.get_config_path())

    @classmethod
    def get_config_item(cls, item):
        item_config = cls.get_config_data().get(item)
        if not item_config:
            raise KeyError('配置项[{}]不存在！'.format(item))
        return item_config

    @classmethod
    def get_data_driver(cls, file_name, sheet_name):
        """获取数据驱动"""
        testcase_path = cls.get_testcase_path()
        file_path = os.path.join(testcase_path, 'casedata', 'datadriver', file_name)  # noqa
        if not os.path.exists(file_path):
            raise FileNotFoundError("文件路径不存在，请检查路径是否正确：%s" % file_path)
        excel_reader = ExcelReader(file_path, sheet_name)
        return excel_reader.read_records()


if __name__ == '__main__':
    p = CommonData
    res = p.get_config_item("项目运行设置")
    print(res)
