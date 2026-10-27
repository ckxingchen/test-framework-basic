"""JSON 数据读写工具。"""

import json
from pathlib import Path
from typing import Any

from jsonpath_ng import parse


def load_json(file_path: str) -> Any:
    """读取 JSON 文件并返回反序列化后的数据。"""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"JSON 文件不存在: {path}")
    with path.open("r", encoding="utf-8") as json_file:
        return json.load(json_file)


def update_jsonpath_value(json_data: Any, json_path: str, value: Any) -> Any:
    """通过 JSONPath 更新数据并返回原数据对象。"""
    expression = parse(json_path)
    if not expression.find(json_data):
        raise ValueError(f"JSONPath未匹配到业务步骤参数：{json_path}")
    expression.update(json_data, value)
    return json_data
