"""YAML 文件读写与收集工具。"""

import os
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


def read_yaml_file(file_path: str) -> Any:
    """安全读取 YAML 文件并返回解析后的数据。"""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"YAML 文件不存在: {path}")
    with path.open("r", encoding="utf-8") as yaml_file:
        return YAML(typ="safe").load(yaml_file)


def write_yaml_file(file_path: str, data: Any) -> None:
    """以支持 Unicode 的格式写入 YAML 文件。"""
    path = Path(file_path)
    writer = YAML()
    writer.allow_unicode = True
    writer.default_flow_style = False
    writer.indent(mapping=2, sequence=2, offset=0)
    with path.open("w", encoding="utf-8") as yaml_file:
        writer.dump(data, yaml_file)


def collect_yaml_files(path: str) -> list[dict[str, list[str]]]:
    """按直接父目录分组收集 YAML 用例文件。"""
    target = Path(path)
    if target.is_file():
        return [{target.parent.name: [path]}]

    grouped_files = []
    for root, dirs, files in os.walk(path):
        dirs.sort()
        yaml_files = sorted(
            file_name for file_name in files if file_name.endswith(".yaml")
        )
        if yaml_files:
            grouped_files.append(
                {
                    os.path.basename(root): [
                        os.path.join(root, file_name).replace("\\", "/")
                        for file_name in yaml_files
                    ]
                }
            )
    return grouped_files
