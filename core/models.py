from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
)

from core.logger import Log


YamlData = Dict[str, Any]
ModelType = TypeVar("ModelType", bound=BaseModel)
# 测试用例配置允许使用的执行策略。
SUPPORTED_POLICIES = {"skip", "parametrize"}


class StrictYamlModel(BaseModel):
    """禁止 YAML 结构中出现未声明的字段。"""

    model_config = ConfigDict(
        extra="forbid",
        coerce_numbers_to_str=True,
    )


class ActionStepModel(StrictYamlModel):
    """基础关键字步骤。"""

    action: str
    method: str
    desc: str
    params: YamlData = Field(default_factory=dict)

    @field_validator("action", "method", "desc")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("字段不能为空")
        return value


class FunctionStepModel(StrictYamlModel):
    """自定义 Python 函数步骤。"""

    function: str
    desc: str
    params: YamlData = Field(default_factory=dict)

    @field_validator("function")
    @classmethod
    def validate_function_type(cls, value: str) -> str:
        if value != "python":
            raise ValueError("function目前只支持python")
        return value

    @field_validator("params")
    @classmethod
    def validate_function_params(cls, params: YamlData) -> YamlData:
        for field_name in ("py_name", "func_name"):
            if not params.get(field_name):
                raise ValueError(f'缺少必填字段："{field_name}"')
        kwargs = params.get("kwargs")
        if kwargs is not None and not isinstance(kwargs, dict):
            raise ValueError("function.params.kwargs必须为字典")
        result_name = params.get("result")
        if result_name is not None and not isinstance(result_name, str):
            raise ValueError("function.params.result必须为字符串或空值")
        return params


class BusinessStepModel(StrictYamlModel):
    """业务关键字步骤。"""

    business: str
    desc: str
    params: YamlData = Field(default_factory=dict)

    @field_validator("business", "desc")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("字段不能为空")
        return value

    @field_validator("params")
    @classmethod
    def validate_business_params(cls, params: YamlData) -> YamlData:
        for param_name, param_data in params.items():
            if not isinstance(param_data, dict):
                raise ValueError(f"业务参数{param_name}必须为字典")
            if not param_data.get("path"):
                raise ValueError(
                    f'缺少必填字段："params.{param_name}.path"'
                )
            if "value" not in param_data:
                raise ValueError(
                    f'缺少必填字段："params.{param_name}.value"'
                )
        return params


YamlStepModel = Union[ActionStepModel, FunctionStepModel, BusinessStepModel]


class TestCaseInfoModel(StrictYamlModel):
    """测试用例的描述和标识信息。"""

    desc: str
    params: Dict[str, Optional[str]] = Field(default_factory=dict)


class TestCasePolicyModel(StrictYamlModel):
    """测试用例的跳过、参数化等运行策略。"""

    policy: str
    flag: bool = False
    desc: str
    params: YamlData = Field(default_factory=dict)

    @field_validator("policy")
    @classmethod
    def validate_policy_name(cls, value: str) -> str:
        if value not in SUPPORTED_POLICIES:
            raise ValueError(f"不支持的用例策略：{value}")
        return value

    @field_validator("params")
    @classmethod
    def validate_policy_params(
        cls,
        params: YamlData,
        info: ValidationInfo,
    ) -> YamlData:
        policy = info.data.get("policy")
        flag = params.get("flag", False)
        if not isinstance(flag, bool):
            raise ValueError(f"{policy}.params.flag必须为布尔值")
        if not flag:
            return params
        if policy == "skip" and not params.get("reason"):
            raise ValueError('缺少必填字段："skip.params.reason"')
        if policy == "parametrize":
            for field_name in ("filename", "sheetname"):
                if not params.get(field_name):
                    raise ValueError(
                        f'缺少必填字段："parametrize.params.{field_name}"'
                    )
        return params


class TestCaseModel(StrictYamlModel):
    """完整的 YAML 测试用例结构。"""

    info: List[TestCaseInfoModel]
    config: List[TestCasePolicyModel]
    step: List[YamlStepModel]

    @field_validator("info")
    @classmethod
    def validate_info_not_empty(
        cls, info: List[TestCaseInfoModel]
    ) -> List[TestCaseInfoModel]:
        if not info:
            raise ValueError("info不能为空")
        return info

    @field_validator("config")
    @classmethod
    def validate_policy_duplicates(
        cls, policies: List[TestCasePolicyModel]
    ) -> List[TestCasePolicyModel]:
        policy_names = [policy.policy for policy in policies]
        if len(policy_names) != len(set(policy_names)):
            raise ValueError("config中存在重复的policy")
        return policies

    @field_validator("step")
    @classmethod
    def validate_request_action_params(
        cls, steps: List[YamlStepModel]
    ) -> List[YamlStepModel]:
        """校验通用 HTTP 请求步骤所需的 method 和 url 参数。"""
        for step in steps:
            if not isinstance(step, ActionStepModel):
                continue
            if step.method not in {
                "request",
                "request_get",
                "request_post",
                "request_file",
            }:
                continue
            for field_name in ("method", "url"):
                if not step.params.get(field_name):
                    raise ValueError(f'缺少必填字段："{field_name}"')
        return steps


class FixtureModel(StrictYamlModel):
    """测试集或测试用例的前后置文件结构。"""

    step: List[YamlStepModel]


class BusinessInfoModel(StrictYamlModel):
    """业务关键字自身的描述和参数模板。"""

    business: Optional[str] = None
    desc: str
    params: YamlData = Field(default_factory=dict)


class BusinessModel(StrictYamlModel):
    """业务关键字 YAML 结构。"""

    business: List[BusinessInfoModel]
    step: List[YamlStepModel]

    @field_validator("business")
    @classmethod
    def validate_business_info(
        cls, business: List[BusinessInfoModel]
    ) -> List[BusinessInfoModel]:
        if not business:
            raise ValueError("business不能为空")
        return business

    @field_validator("step")
    @classmethod
    def reject_nested_business(
        cls, steps: List[YamlStepModel]
    ) -> List[YamlStepModel]:
        if any(isinstance(step, BusinessStepModel) for step in steps):
            raise ValueError("业务关键字暂不支持嵌套business步骤")
        return steps


def _validate_action_references(steps: List[YamlData], file_path: str) -> None:
    """在注册表可用时校验 Action 类和关键字方法。"""
    from core.loader import ActionLoader

    registry = ActionLoader.get_registry()
    if not registry:
        return
    for step_index, step in enumerate(steps):
        action_name = step.get("action")
        if not action_name:
            continue
        action_data = registry.get(action_name)
        if action_data is None:
            raise ValueError(
                f"{file_path} 第{step_index + 1}步Action未注册：{action_name}"
            )
        method_name = step["method"]
        if method_name not in action_data["funcs"]:
            raise ValueError(
                f"{file_path} 第{step_index + 1}步关键字未注册："
                f"{action_name}.{method_name}"
            )


def _validate_yaml_data(
    yaml_data: Any,
    file_path: str,
    model_class: Type[ModelType],
    data_description: str,
) -> YamlData:
    """使用指定模型校验 YAML 数据，并统一记录格式错误。"""
    if not isinstance(yaml_data, dict):
        raise TypeError(f"{data_description}数据格式必须为字典！")

    try:
        validated_data = model_class.model_validate(yaml_data).model_dump()
        _validate_action_references(validated_data.get("step", []), file_path)
        return validated_data
    except (ValidationError, TypeError, ValueError) as error:
        detail = error.json() if isinstance(error, ValidationError) else str(error)
        Log().logger.error(
            "文件%s\n数据格式验证失败：%s", file_path, detail
        )
        raise


def validate_fixture_yaml(fixture_data: Any, file_path: str) -> YamlData:
    """校验测试集或测试用例的前后置 YAML 数据。"""
    return _validate_yaml_data(fixture_data, file_path, FixtureModel, "前后置文件")


def validate_business_yaml(business_data: Any, file_path: str) -> YamlData:
    """校验业务关键字 YAML 数据。"""
    return _validate_yaml_data(business_data, file_path, BusinessModel, "业务关键字")


def validate_test_case_yaml(case_data: Any, file_path: str) -> YamlData:
    """校验测试用例 YAML 数据。"""
    return _validate_yaml_data(case_data, file_path, TestCaseModel, "测试用例文件")
