"""INI 配置文件读写工具。"""

from configparser import ConfigParser, RawConfigParser
from pathlib import Path


def load_ini(file_path: str) -> dict[str, dict[str, str]]:
    """读取 INI 文件并返回按节分组的字典。"""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"INI 文件不存在: {path}")

    parser = RawConfigParser()
    parser.read(path, encoding="utf-8")
    return {
        section: dict(parser.items(section))
        for section in parser.sections()
    }


def edit_ini_file(file_path: str, section: str, key: str, value: str) -> None:
    """更新 INI 文件中指定节和键的值。"""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"INI 文件不存在: {path}")

    parser = ConfigParser(comment_prefixes=("/",), allow_no_value=True)
    parser.read(path, encoding="utf-8")
    parser.set(section, key, value)
    with path.open("w", encoding="utf-8") as ini_file:
        parser.write(ini_file)
