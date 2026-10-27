"""配置值解析工具。"""

from typing import Any, Optional


# 配置文件中允许表示“真”的文本值。
_TRUE_VALUES = {"1", "true", "yes", "on"}
# 配置文件中允许表示“假”的文本值。
_FALSE_VALUES = {"0", "false", "no", "off"}


def parse_bool(
    value: Any,
    *,
    default: Optional[bool] = None,
    name: str = "配置项",
) -> bool:
    """将常见布尔配置值转换为 bool，未配置时可返回指定默认值。"""
    if value in (None, ""):
        if default is not None:
            return default
        raise ValueError(f"{name}不能为空")

    if isinstance(value, bool):
        return value

    normalized_value = str(value).strip().lower()
    if normalized_value in _TRUE_VALUES:
        return True
    if normalized_value in _FALSE_VALUES:
        return False
    raise ValueError(f"{name}必须为布尔值：{value}")
