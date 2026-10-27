import os.path
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest
from core.comdata import CommonData
from core.container import LocalManager
from core.logger import Log
from core.models import validate_fixture_yaml, validate_test_case_yaml
from core.parser import YamlStepExecutor
from core.utils.u_yaml import collect_yaml_files, read_yaml_file
from keywords.http.session import SessionManager
from keywords.web.page import PageManager


def _get_session_collection_order(node: pytest.Collector) -> Dict[str, List[str]]:
    """获取当前 pytest 会话的 YAML 用例收集顺序。

    收集顺序保存在 Session 对象中，避免同一进程多次调用
    ``pytest.main`` 时复用上一次运行遗留的模块级状态。
    """
    collection_order = getattr(node.session, "_yaml_case_collection_order", None)
    if collection_order is None:
        collection_order = {}
        setattr(node.session, "_yaml_case_collection_order", collection_order)
    return collection_order


def _execute_fixture(fixture_dir: str, fixture_name: str) -> None:
    """读取、校验并执行指定目录下的前置或后置 YAML 步骤。"""
    fixture_path = os.path.join(fixture_dir, f"{fixture_name}.yml")
    if not os.path.exists(fixture_path):
        return

    Log().logger.info(f"{'- ' * 20}【{fixture_name}开始】{'- ' * 20}")
    fixture_content = read_yaml_file(fixture_path)
    validated_content = validate_fixture_yaml(fixture_content, fixture_path)
    YamlStepExecutor.execute(validated_content["step"])


def _cleanup_suite_fixture_runtime() -> None:
    """释放测试集前后置可能创建的自动化资源和局部变量。"""
    try:
        automation_type = CommonData.get_config_data()["项目运行设置"][
            "auto_type"
        ].lower()
        if automation_type == "web":
            PageManager.close_page(keep_artifacts=False)
        elif automation_type == "http":
            SessionManager.close_session()
    finally:
        LocalManager.clear()


def _get_enabled_policy_params(
    case_config: List[Dict[str, Any]],
    policy_name: str,
) -> Optional[Dict[str, Any]]:
    """返回指定且已启用的用例策略参数。"""
    for policy_config in case_config:
        if policy_config.get("policy") != policy_name:
            continue
        policy_params = policy_config.get("params", {})
        if bool(policy_params.get("flag")):
            return policy_params
    return None


class YamlFileCollector(pytest.File):
    """将一个 YAML 文件转换为 pytest 测试集收集节点。"""

    def collect(self):
        """收集当前 YAML 文件，并创建对应的测试集节点。"""
        suite_node_id = self.parent.nodeid
        self._record_case_collection_order(suite_node_id)

        for suite_data in collect_yaml_files(str(self.path)):
            # testcase 根目录下的 YAML 不作为测试集执行，保持原有过滤规则。
            if suite_data.get("testcase"):
                continue

            suite_name = next(iter(suite_data))
            suite_parent = self.parent.parent
            yield YamlSuiteCollector.from_parent(
                parent=suite_parent,
                name=suite_name,
                suite_data=suite_data,
                suite_node_id=suite_node_id,
            )

    def _record_case_collection_order(self, suite_node_id: str) -> None:
        """记录同一测试集内 YAML 文件的收集顺序。"""
        collection_order = _get_session_collection_order(self)
        collection_order.setdefault(suite_node_id, []).append(Path(self.name).stem)


class YamlSuiteCollector(pytest.Class):
    """表示一个 YAML 测试集，并负责测试集级前后置处理。"""

    def __init__(
        self,
        name: str,
        parent: pytest.Collector,
        suite_data: Dict[str, List[str]],
        suite_node_id: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, parent=parent, **kwargs)
        self.suite_data = suite_data
        self.case_paths = next(iter(suite_data.values()))
        self.suite_node_id = suite_node_id

    @classmethod
    def from_parent(
        cls,
        parent: pytest.Collector,
        *,
        name: str,
        suite_data: Dict[str, List[str]],
        suite_node_id: str,
    ):
        """通过 pytest 推荐入口创建测试集节点。"""
        return super().from_parent(
            parent=parent,
            name=name,
            suite_data=suite_data,
            suite_node_id=suite_node_id,
        )

    def setup(self) -> None:
        """在测试集第一个 YAML 用例执行前运行测试集前置。"""
        if self._is_collection_boundary(0):
            try:
                self._run_suite_fixture("测试集前置")
            except BaseException:
                _cleanup_suite_fixture_runtime()
                raise

    def teardown(self) -> None:
        """在测试集最后一个 YAML 用例执行后运行测试集后置。"""
        if self._is_collection_boundary(-1):
            try:
                self._run_suite_fixture("测试集后置")
            finally:
                _cleanup_suite_fixture_runtime()

    def collect(self):
        """读取测试集中的 YAML 文件并创建 pytest 测试项。"""
        for case_path in self.case_paths:
            case_content = validate_test_case_yaml(
                read_yaml_file(case_path),
                case_path,
            )
            case_name = Path(case_path).stem
            parameterization = _get_enabled_policy_params(
                case_content["config"],
                "parametrize",
            )
            if not parameterization:
                yield self._create_case_item(
                    case_name,
                    case_path,
                    case_content,
                )
                continue

            data_rows = CommonData.get_data_driver(
                parameterization["filename"],
                parameterization["sheetname"],
            )
            if not data_rows:
                raise ValueError(f"数据驱动文件没有数据行：{case_path}")
            for data_index, data_row in enumerate(data_rows, start=1):
                yield self._create_case_item(
                    f"{case_name}[{data_index}]",
                    case_path,
                    case_content,
                    data_row=data_row,
                )

    def _create_case_item(
        self,
        name: str,
        case_path: str,
        case_content: Dict[str, Any],
        data_row: Optional[Dict[str, Any]] = None,
    ):
        return YamlTestCaseItem.from_parent(
            parent=self,
            name=name,
            case_path=case_path,
            case_content=case_content,
            data_row=data_row,
        )

    def _is_collection_boundary(self, position: int) -> bool:
        """判断当前节点是否位于测试集收集顺序的首位或末位。"""
        collection_order = _get_session_collection_order(self)
        case_names = collection_order.get(self.suite_node_id, [])
        if not case_names or not self.case_paths:
            return False
        return case_names[position] == Path(self.case_paths[0]).stem

    def _run_suite_fixture(self, fixture_name: str) -> None:
        """执行当前测试集目录下的测试集级前置或后置步骤。"""
        suite_dir = os.path.dirname(self.case_paths[0])
        _execute_fixture(suite_dir, fixture_name)


class YamlTestCaseItem(pytest.Item):
    """表示一个 YAML 测试用例及其完整执行生命周期。"""

    def __init__(
        self,
        name: str,
        parent: pytest.Collector,
        case_path: str,
        case_content: Dict[str, Any],
        data_row: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, parent=parent, **kwargs)
        self.case_name = Path(case_path).stem
        self.case_path = case_path
        self.case_content = case_content
        self.data_row = data_row
        self._case_failed = False
        self._case_result = "passed"
        self._case_error = ""
        self._artifact_paths = {"videos": [], "trace": None}
        self._artifacts_attached = False

    @classmethod
    def from_parent(
        cls,
        parent: pytest.Collector,
        *,
        name: str,
        case_path: str,
        case_content: Dict[str, Any],
        data_row: Optional[Dict[str, Any]] = None,
    ):
        """通过 pytest 推荐入口创建 YAML 测试项。"""
        return super().from_parent(
            parent=parent,
            name=name,
            case_path=case_path,
            case_content=case_content,
            data_row=data_row,
        )

    def setup(self) -> None:
        """初始化自动化资源，然后执行测试用例前置步骤。"""
        try:
            if self.data_row is not None:
                LocalManager.set_value("DataDriver", self.data_row)
            self._initialize_runtime_resource()
            self._run_case_fixture("测试用例前置")
        except BaseException:
            self._case_failed = True
            self._cleanup_case_runtime()
            raise

    def teardown(self) -> None:
        """执行测试用例后置，并确保自动化资源和局部变量被释放。"""
        try:
            self._run_case_fixture("测试用例后置")
        except BaseException:
            self._case_failed = True
            raise
        finally:
            self._cleanup_case_runtime()

    def runtest(self) -> None:
        """按照用例策略执行当前普通用例或数据驱动行。"""
        Log().logger.info(f"{'- ' * 20}【测试用例{self.case_name}开始】{'- ' * 20}")
        case_config = self.case_content["config"]
        case_steps = self.case_content["step"]
        skip_params = _get_enabled_policy_params(case_config, "skip")

        if skip_params:
            self._skip_test_case(skip_params)

        if self.data_row is not None:
            Log().logger.info(
                "【%s】参数化测试数据：%s",
                self.case_name,
                self.data_row,
            )

        YamlStepExecutor.execute(case_steps)

    def repr_failure(self, excinfo):
        """使用精简格式展示 YAML 测试用例的执行异常。"""
        return f"{self.name}: {excinfo.value}"

    def _run_case_fixture(self, fixture_name: str) -> None:
        """执行当前用例目录下的用例级前置或后置步骤。"""
        _execute_fixture(os.path.dirname(self.case_path), fixture_name)

    @staticmethod
    def _skip_test_case(skip_params: Dict[str, Any]) -> None:
        """根据策略配置跳过当前测试用例。"""
        pytest.skip(skip_params["reason"])

    @staticmethod
    def _get_automation_type() -> str:
        """读取当前项目配置的自动化类型。"""
        return CommonData.get_config_data()["项目运行设置"]["auto_type"]

    def _initialize_runtime_resource(self) -> None:
        """按自动化类型初始化浏览器页面或 HTTP Session。"""
        automation_type = self._get_automation_type()
        if automation_type == "web":
            PageManager.prepare_case_artifacts(self.nodeid)
            PageManager.get_page()
        elif automation_type == "http":
            SessionManager.get_session()

    def _release_runtime_resource(self):
        """按自动化类型释放浏览器页面或 HTTP Session。"""
        automation_type = self._get_automation_type()
        if automation_type == "web":
            return PageManager.close_page(
                keep_artifacts=self._case_failed
            )
        elif automation_type == "http":
            SessionManager.close_session()
        return {"videos": [], "trace": None}

    def _cleanup_case_runtime(self) -> None:
        """释放自动化资源，并保证当前用例的局部变量一定被清空。"""
        try:
            self._artifact_paths = self._release_runtime_resource()
        finally:
            LocalManager.clear()
