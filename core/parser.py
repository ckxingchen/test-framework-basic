import os
import re
import sys
from typing import Any, Dict, List, Mapping
import allure
from core.comdata import CommonData
from core.container import LocalManager
from core.keyword import RESULT_PARAM_DEFAULT, RESULT_PARAM_NAME
from core.loader import ActionLoader
from core.logger import Log
from core.models import validate_business_yaml
from core.utils.u_json import update_jsonpath_value
from core.utils.u_obj import load_function
from core.utils.u_yaml import read_yaml_file


# 匹配 YAML 中的 `${变量名}` 局部变量语法。
LOCAL_VARIABLE_PATTERN = re.compile(r"\${(.*?)}")
# 匹配 YAML 中的 `DataDriver.字段名` 数据驱动语法。
DATA_DRIVER_PATTERN = re.compile(r"DataDriver\.(\w+)")


class YamlStepExecutor:
    """解析并执行 YAML 中的基础关键字、自定义函数和业务关键字步骤。"""

    @classmethod
    def execute(cls, steps: List[Dict[str, Any]]) -> None:
        """按照 YAML 中的定义顺序执行全部步骤。"""
        for step in steps or []:
            if "action" in step:
                cls._execute_action_step(step)
            elif "function" in step:
                cls._execute_python_step(step)
            elif "business" in step:
                cls._execute_business_step(step)

    @classmethod
    def _execute_action_step(cls, step: Dict[str, Any]) -> None:
        """解析参数并执行一个已注册的基础关键字步骤。"""
        action_name = step["action"]
        method_name = step["method"]
        action_registry = ActionLoader.get_registry()
        action_data = action_registry.get(action_name)

        if action_data is None:
            message = f"基础关键字类{action_name}未找到或未实现！"
            Log().logger.error(message)
            raise AssertionError(message)

        keyword_info = action_data["funcs"].get(method_name)
        if keyword_info is None:
            message = f"基础关键字未找到或未实现：{method_name}"
            Log().logger.error(message)
            raise AssertionError(message)

        with allure.step(f"action步骤:{step['desc']}"):
            Log().logger.info(f"基础关键字[{step['desc']}],开始执行:")
            resolved_params = cls.resolve_variables(
                step.get("params") or {}, LocalManager.local_dict
            )
            call_params = dict(resolved_params)
            result_name = None
            if keyword_info["has_result"]:
                result_name = call_params.pop(
                    RESULT_PARAM_NAME,
                    RESULT_PARAM_DEFAULT,
            )

            try:
                action_class = keyword_info.get(
                    "owner_cls",
                    action_data["cls_obj"],
                )
                action_instance = action_class()
                action_instance._set_keyword_context(
                    action_name,
                    method_name,
                    result_name,
                )
                result_value = getattr(action_instance, method_name)(**call_params)
                if keyword_info["has_result"] and result_name:
                    LocalManager.set_value(result_name, result_value)
            except Exception:
                if keyword_info["has_result"] and result_name:
                    LocalManager.set_value(result_name, None)
                raise

            if not action_instance._has_logged_detail():
                action_instance.log.info(step["desc"])
            Log().logger.debug(
                "执行action步骤解析==>函数%s执行成功,参数：%s",
                method_name,
                resolved_params,
            )

    @classmethod
    def _execute_python_step(cls, step: Dict[str, Any]) -> None:
        """加载并执行项目 casedata/lib 目录中的自定义 Python 函数。"""
        function_type = step["function"]
        if function_type != "python":
            message = f"方法未找到或未实现：{function_type}"
            Log().logger.error(message)
            raise AssertionError(message)

        with allure.step(f"function步骤:{step['desc']}"):
            if CommonData.DRIVER_DIR not in sys.path:
                sys.path.append(CommonData.DRIVER_DIR)

            function_params = step["params"]
            library_path = os.path.join(
                CommonData.get_testcase_path(), "casedata", "lib"
            )
            function_name = function_params["func_name"]
            function = load_function(
                library_path, function_params["py_name"], function_name
            )
            if function is None:
                message = f"自定义关键字未找到或未实现：{function_name}"
                Log().logger.error(message)
                raise AssertionError(message)

            Log().logger.info(f"自定义关键字[{step['desc']}],开始执行:")
            resolved_params = cls.resolve_variables(
                function_params.get("kwargs") or {}, LocalManager.local_dict
            )
            result = function(**resolved_params)
            result_name = function_params.get("result")
            if result_name:
                LocalManager.set_value(result_name, result)
            Log().logger.debug(
                "自定义函数%s执行成功,参数：%s", function_name, resolved_params
            )

    @classmethod
    def _execute_business_step(cls, step: Dict[str, Any]) -> None:
        """加载业务关键字文件，注入调用参数并执行其中的子步骤。"""
        business_name = step["business"]
        business_path = os.path.join(CommonData.get_business_path(), business_name)
        if not os.path.exists(business_path):
            message = f"业务关键字{business_name}不存在!"
            Log().logger.error(message)
            raise AssertionError(message)

        business_data = validate_business_yaml(
            read_yaml_file(business_path),
            business_path,
        )
        for extracted_param in (step.get("params") or {}).values():
            update_jsonpath_value(
                business_data["step"],
                extracted_param["path"],
                extracted_param["value"],
            )

        cls.execute(business_data["step"])

    @classmethod
    def resolve_variables(
        cls, yaml_data: Any, variables: Mapping[str, Any]
    ) -> Any:
        """递归解析 YAML 数据中的数据驱动变量和局部变量。

        返回新的字典或列表，避免数据驱动多次执行时修改原始 YAML 步骤。
        """
        if isinstance(yaml_data, str):
            driven_value = cls._resolve_data_driver_variables(yaml_data, variables)
            return cls._resolve_local_variables(driven_value, variables)
        if isinstance(yaml_data, dict):
            return {
                key: cls.resolve_variables(value, variables)
                for key, value in yaml_data.items()
            }
        if isinstance(yaml_data, list):
            return [cls.resolve_variables(value, variables) for value in yaml_data]
        return yaml_data

    @staticmethod
    def _resolve_local_variables(data: Any, variables: Mapping[str, Any]) -> Any:
        """替换字符串中的 ``${变量名}`` 局部变量。"""
        if not isinstance(data, str):
            return data

        variable_names = LOCAL_VARIABLE_PATTERN.findall(data)
        for variable_name in variable_names:
            if variable_name not in variables:
                raise ValueError(f"局部变量不存在：{variable_name}")

            variable_value = variables[variable_name]
            placeholder = f"${{{variable_name}}}"
            if data == placeholder:
                data = variable_value
            else:
                data = data.replace(placeholder, str(variable_value))

            if variable_name not in {"result_text", "result_content"}:
                Log().logger.info(f"动态变量{variable_name}替换成功")
                Log().logger.debug(
                    "动态变量%s替换成功,替换后的值==>%s",
                    variable_name,
                    variable_value,
                )
        return data

    @staticmethod
    def _resolve_data_driver_variables(
        data: str, variables: Mapping[str, Any]
    ) -> Any:
        """替换字符串中的 ``DataDriver.字段名`` 数据驱动变量。"""
        field_names = DATA_DRIVER_PATTERN.findall(data)
        if not field_names:
            return data

        if "DataDriver" not in variables:
            raise ValueError("数据驱动变量不存在：DataDriver")
        driver_data = variables["DataDriver"]
        for field_name in field_names:
            if field_name not in driver_data:
                raise ValueError(f"数据驱动字段不存在：{field_name}")
            field_value = driver_data[field_name]
            placeholder = f"DataDriver.{field_name}"
            if data == placeholder:
                data = field_value
            else:
                data = data.replace(placeholder, str(field_value))
            Log().logger.info(
                "数据驱动变量[%s]替换成功,替换后的值==>%s",
                placeholder,
                field_value,
            )
        return data
