from typing import Any, Dict, Iterable, List, Mapping, Tuple


def exclude_keys(data: Mapping[Any, Any], excluded_keys: Iterable[Any]) -> Dict[Any, Any]:
    """返回排除指定键后的新字典。"""
    excluded = tuple(excluded_keys)
    return {key: value for key, value in data.items() if key not in excluded}


def partition_by_keys(
    data: Mapping[Any, Any], selected_keys: Iterable[Any]
) -> Tuple[Dict[Any, Any], Dict[Any, Any]]:
    """将字典拆分为未选中部分和选中部分。"""
    selected = tuple(selected_keys)
    remaining = {key: value for key, value in data.items() if key not in selected}
    matched = {key: value for key, value in data.items() if key in selected}
    return remaining, matched


def get_dict_keys(data: Mapping[Any, Any]) -> List[Any]:
    """按原顺序返回映射中的全部键。"""
    if not isinstance(data, Mapping):
        raise TypeError("data必须为字典类型！")
    return list(data.keys())


def get_dict_value(data: Mapping[Any, Any]) -> List[Any]:
    """按原顺序返回映射中的全部值。"""
    if not isinstance(data, Mapping):
        raise TypeError("data必须为字典类型！")
    return list(data.values())
