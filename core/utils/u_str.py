import uuid
from typing import List


def split_semicolon_list(value: str) -> List[str]:
    """移除换行后，按分号将字符串拆分为列表。"""
    if not isinstance(value, str):
        raise TypeError("参数必须为使用分号连接的字符串！")
    return value.replace("\n", "").split(";")


def generate_uuid() -> str:
    """生成随机 UUID 字符串。"""
    return str(uuid.uuid4())
