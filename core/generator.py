import inspect
import json
import re
import shutil
from inspect import Parameter
from typing import Dict, List, Any, Optional, Type
from pathlib import Path
from core.comdata import CommonData
from core.keyword import RESULT_PARAM_DEFAULT, RESULT_PARAM_NAME
from core.loader import ActionLoader
from core.utils.u_yaml import write_yaml_file


# HTTP 关键字模板中响应结果参数的默认变量名。
HTTP_RESULT_DEFAULTS = {
    "result_code": None,
    "result_content": None,
    "result_text": "result_text",
    "result_json": "result_json",
}
# 跨平台文件名不允许出现的字符。
INVALID_FILE_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# Windows 不允许直接作为文件名使用的保留名称。
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
# 自动生成的关键字模板文件名最大长度。
MAX_TEMPLATE_NAME_LENGTH = 100


class Generator:

    @classmethod
    def generate_actions(cls, action_names=None, clean=False) -> None:
        """按关键字类名称生成action模板。"""
        action_map = ActionLoader.get_registry()
        action_dir = Path(CommonData.BASE_KEYWORD)
        selected_names = set(action_names or action_map)
        used_action_paths = {}
        for cls_name, cls_data in action_map.items():
            if cls_name not in selected_names:
                continue
            if cls_name not in ["HttpAction", "WebAction", "CheckAction"]:
                action_path = action_dir / '处理器'
            else:
                action_path = action_dir
            class_dir_name = cls._get_action_dir_name(cls_data["cls_obj"])
            class_dir = action_path / class_dir_name
            normalized_path = str(class_dir).casefold()
            if normalized_path in used_action_paths:
                previous_action = used_action_paths[normalized_path]
                raise ValueError(
                    f"Action模板目录重复：{previous_action}和{cls_name}"
                    f" -> {class_dir_name}"
                )
            used_action_paths[normalized_path] = cls_name
            if clean and class_dir.is_dir():
                shutil.rmtree(class_dir)
            action_path.mkdir(parents=True, exist_ok=True)
            cls._process_action_class(cls_data, action_path, class_dir_name)
        cls._write_gui_catalog(action_map, action_dir)

    @staticmethod
    def _write_gui_catalog(action_map: Dict, action_dir: Path) -> None:
        """输出 GUI 可独立读取的关键字参数说明。"""
        catalog = {
            action_name: {
                method_name: {
                    str(param_name): str(description)
                    for param_name, description in (
                        method_data.get("param_desc") or {}
                    ).items()
                }
                for method_name, method_data in action_data["funcs"].items()
            }
            for action_name, action_data in action_map.items()
        }
        action_dir.mkdir(parents=True, exist_ok=True)
        catalog_path = action_dir / ".gui_catalog.json"
        temporary_path = action_dir / ".gui_catalog.json.tmp"
        with temporary_path.open("w", encoding="utf-8") as catalog_file:
            json.dump(catalog, catalog_file, ensure_ascii=False, indent=2)
        temporary_path.replace(catalog_path)

    @classmethod
    def _process_action_class(
        cls,
        cls_data: Dict,
        output_dir: Path,
        class_dir_name: str,
    ) -> None:
        """处理单个Action类，生成对应的YAML文件"""
        cls_obj = cls_data['cls_obj']
        action_path = output_dir / class_dir_name
        action_path.mkdir(parents=True, exist_ok=True)
        used_file_names = {}
        for func_name, func_data in cls_data['funcs'].items():
            action_data = cls._create_action_template(cls_obj, func_name, func_data)
            if not action_data:
                continue
            desc = cls._get_method_desc(func_data['func_obj'])
            file_stem = cls._safe_file_stem(desc, func_name)
            normalized_name = file_stem.casefold()
            if normalized_name in used_file_names:
                previous_method = used_file_names[normalized_name]
                raise ValueError(
                    f"关键字模板文件名重复：{cls_obj.__name__}."
                    f"{previous_method}和{func_name} -> {file_stem}.yaml"
                )
            used_file_names[normalized_name] = func_name
            yaml_path = action_path / f"{file_stem}.yaml"
            write_yaml_file(str(yaml_path), action_data)
        print(f"YAML基础关键字模板生成成功: {class_dir_name}")

    @classmethod
    def _create_action_template(
        cls,
        action_class: Type,
        method_name: str,
        func_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """创建单个方法的动作模板"""
        method = func_data['func_obj']
        if isinstance(method, (classmethod, staticmethod)):
            func = method.__func__
        else:
            func = method
        params = cls._get_template_params(func, func_data)

        if action_class.__name__ == "HttpAction":
            for param_name, default_value in HTTP_RESULT_DEFAULTS.items():
                if param_name in params:
                    params[param_name] = default_value

        desc = cls._get_method_desc(method)
        action_template = {
            'action': action_class.__name__,
            'method': method_name,
            'desc': desc,
        }

        if params:
            action_template['params'] = params

        return [action_template]

    @classmethod
    def _get_template_params(
        cls,
        func: Any,
        func_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """按 docstring 参数顺序生成模板，并从函数签名读取默认值。"""
        signature_params = inspect.signature(func).parameters
        params = {}
        for param_name in func_data.get("param_desc") or {}:
            if param_name in {"self", "cls"}:
                continue
            signature_param = signature_params.get(param_name)
            params[param_name] = (
                cls._get_param_default(signature_param)
                if signature_param is not None
                and signature_param.kind not in {
                    Parameter.VAR_POSITIONAL,
                    Parameter.VAR_KEYWORD,
                }
                else None
            )

        if func_data["has_result"]:
            params[RESULT_PARAM_NAME] = RESULT_PARAM_DEFAULT
        return params

    @staticmethod
    def _get_base_action(cls_obj: Type) -> Optional[Type]:
        """获取最上层Action"""
        cls_list = list(inspect.getmro(cls_obj))
        cls_list.reverse()
        for parent in cls_list:
            if parent.__name__.endswith("Action"):
                return parent
        return None

    @staticmethod
    def _get_method_desc(method: Any) -> str:
        """获取方法描述"""
        if not method.__doc__:
            return method.__name__
        return method.__doc__.strip().split('\n')[0].strip()

    @classmethod
    def _get_action_dir_name(cls, action_class: Type) -> str:
        class_doc = (
            inspect.cleandoc(action_class.__doc__)
            if action_class.__doc__
            else None
        )
        raw_name = (
            class_doc.splitlines()[0]
            if class_doc
            else action_class.__name__
        )
        return cls._safe_file_stem(raw_name, action_class.__name__)

    @staticmethod
    def _safe_file_stem(value: Any, fallback: str) -> str:
        """将描述转换为 Windows、macOS 和 Linux 均可用的文件名。"""
        file_stem = INVALID_FILE_NAME_CHARS.sub("_", str(value))
        file_stem = re.sub(r"\s+", " ", file_stem).strip(" ._")
        file_stem = file_stem[:MAX_TEMPLATE_NAME_LENGTH].rstrip(" ._")
        if not file_stem:
            file_stem = fallback
        if file_stem.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
            file_stem = f"_{file_stem}"
        return file_stem

    @staticmethod
    def _get_param_default(param_obj: Parameter) -> Any:
        """获取方法参数默认值"""
        return param_obj.default if param_obj.default is not Parameter.empty else None


if __name__ == "__main__":
    try:
        ActionLoader.load_actions()
        print(ActionLoader.get_registry())
        Generator.generate_actions()
    except Exception as e:
        print(f"生成过程中发生错误: {e}")
        raise
