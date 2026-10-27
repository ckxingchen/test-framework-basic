"""从指定 Python 文件中动态加载函数。"""

import hashlib
import importlib.util
import inspect
from pathlib import Path
import sys
from types import FunctionType
from typing import Optional


def load_function(
    library_path: str,
    module_name: str,
    function_name: str,
) -> Optional[FunctionType]:
    """从库目录中的 Python 模块加载指定函数。"""
    library = Path(library_path).resolve()
    if not library.is_dir():
        raise FileNotFoundError(f"函数库目录不存在: {library}")

    module_file = library / module_name
    if module_file.suffix != ".py":
        module_file = module_file.with_suffix(".py")
    if not module_file.is_file():
        raise ModuleNotFoundError(f"函数库模块不存在: {module_file}")

    library_string = str(library)
    if library_string not in sys.path:
        sys.path.append(library_string)

    module_key = hashlib.sha1(
        str(module_file).encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()
    import_name = f"dynamic_keyword_{module_file.stem}_{module_key}"
    spec = importlib.util.spec_from_file_location(import_name, module_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法创建模块加载器: {module_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[import_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        sys.modules.pop(import_name, None)
        raise ModuleNotFoundError(f"模块{module_name}不存在！\n{error}") from error

    function = getattr(module, function_name, None)
    if not inspect.isfunction(function):
        return None
    return function
