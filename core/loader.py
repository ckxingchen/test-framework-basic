import importlib
import importlib.util
import inspect
import os
import pkgutil
import sys
from pathlib import Path
from typing import Dict, List, Set
from core.comdata import CommonData
from core.keyword import (
    RESULT_PARAM_DESC,
    KeywordActionBase,
    is_keyword,
    keyword_has_result,
)
from core.logger import Log


class ActionLoader:
    _registry: Dict[str, Dict] = {}

    @classmethod
    def load_actions(cls) -> Dict[str, Dict]:
        """加载内置关键字目录中的 Action 类。"""
        Path(CommonData.BASE_KEYWORD).mkdir(parents=True, exist_ok=True)
        cls._registry.clear()
        try:
            loaded_modules: Set[str] = set()
            import_errors: List[str] = []
            cls._load_actions_from_exe(loaded_modules, import_errors)
            cls._raise_import_errors(import_errors)
            if not getattr(sys, "frozen", False):
                cls._load_actions_from_folder(loaded_modules, import_errors)
                cls._raise_import_errors(import_errors)
            return cls.get_registry()
        except Exception:
            cls._registry.clear()
            raise

    @classmethod
    def _load_actions_from_exe(
        cls,
        loaded_modules: Set[str],
        import_errors: List[str],
    ):
        """从打包进可执行程序的 keywords 包加载 Action 类。"""
        package_path = "keywords"
        try:
            package = importlib.import_module(package_path)
        except ImportError as error:
            import_errors.append(f"{package_path}: {error}")
            return
        if not hasattr(package, "__path__"):
            import_errors.append(f"{package_path}: 不是有效的包路径")
            return

        for module_info in pkgutil.walk_packages(
            package.__path__,
            f"{package.__name__}.",
        ):
            if module_info.ispkg or module_info.name in loaded_modules:
                continue
            try:
                module = importlib.import_module(module_info.name)
                cls._process_module(module, source="builtin")
                loaded_modules.add(module_info.name)
            except Exception as error:
                import_errors.append(
                    f"{module_info.name}: {type(error).__name__}: {error}"
                )

    @classmethod
    def _load_actions_from_folder(
        cls,
        loaded_modules: Set[str],
        import_errors: List[str],
    ):
        """从开发环境物理 keywords 目录加载 Action 类。"""
        keywords_dir = CommonData.KEYWORDS_DIR
        if not keywords_dir or not os.path.isdir(keywords_dir):
            return

        for root, _, files in os.walk(keywords_dir):
            for file_name in files:
                if not file_name.endswith(".py") or file_name == "__init__.py":
                    continue
                file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(
                    file_path,
                    os.path.dirname(keywords_dir),
                )
                module_name = relative_path.replace(os.sep, ".")[:-3]
                if module_name in loaded_modules:
                    continue
                try:
                    spec = importlib.util.spec_from_file_location(
                        module_name,
                        file_path,
                    )
                    if spec is None or spec.loader is None:
                        raise ImportError(f"无法创建模块: {file_path}")
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    cls._process_module(module, source="keywords")
                    loaded_modules.add(module_name)
                except Exception as error:
                    import_errors.append(
                        f"{module_name}: {type(error).__name__}: {error}"
                    )

    @staticmethod
    def _raise_import_errors(import_errors: List[str]) -> None:
        if import_errors:
            error_text = "\n".join(f"- {error}" for error in import_errors)
            raise RuntimeError(f"内置关键字导入失败：\n{error_text}")


    @classmethod
    def _process_module(cls, module, source="builtin"):
        """提取并注册普通模块中的 Action 类。"""
        for class_name, action_class in inspect.getmembers(module, inspect.isclass):
            if not class_name.endswith("Action"):
                continue
            if action_class.__module__ != module.__name__:
                continue
            if not issubclass(action_class, KeywordActionBase):
                raise TypeError(
                    f"{module.__name__}.{class_name}必须继承KeywordActionBase"
                )
            action_name = action_class.__name__
            existing_action = cls._registry.get(action_name)
            if existing_action is not None:
                raise ValueError(
                    f"Action重复：{action_name}，来源为"
                    f"{existing_action.get('module')}和{module.__name__}"
                )
            cls._registry[action_name] = {
                "cls_obj": action_class,
                "funcs": cls._process_class(action_class, source=source),
                "source": source,
                "module": module.__name__,
            }

    @classmethod
    def _process_class(
        cls,
        action_class,
        source="builtin",
    ):
        """提取当前类自身使用 @keyword 标记的实例方法。"""
        methods = {}
        for method_name, method_obj in action_class.__dict__.items():
            if method_name.startswith("_"):
                continue
            if isinstance(method_obj, (classmethod, staticmethod)):
                func = method_obj.__func__
            elif inspect.isfunction(method_obj):
                func = method_obj
            else:
                continue
            if not is_keyword(func):
                continue

            original_func = inspect.unwrap(func)
            doc = inspect.getdoc(original_func) or None
            params_data = cls._parse_docstring(doc) or {}
            has_result = keyword_has_result(original_func)
            if has_result:
                params_data.setdefault("result", RESULT_PARAM_DESC)
            methods[method_name] = {
                "owner_cls": action_class,
                "func_obj": method_obj,
                "param_desc": params_data,
                "has_result": has_result,
                "source": source,
            }
        return methods

    @staticmethod
    def _parse_docstring(doc):
        """从 :param 格式的方法注释中提取参数说明。"""
        if not doc:
            return None
        param_dict = {}
        for line in doc.splitlines():
            stripped = line.strip()
            if not stripped.startswith(":param"):
                continue
            parts = stripped.split(":", 2)
            if len(parts) >= 3:
                param_name = parts[1].strip().split()[-1]
                param_dict[param_name] = parts[2].strip()
        return param_dict


    @classmethod
    def get_registry(cls) -> Dict[str, Dict]:
        """返回 Action 注册表浅拷贝。"""
        return cls._registry.copy()

    @classmethod
    def get_class(cls, class_name) -> Dict:
        """按类名获取已注册 Action 数据。"""
        if class_name not in cls._registry:
            raise KeyError(f"未注册类: {class_name}")
        return cls._registry[class_name]


    @classmethod
    def clear(cls) -> None:
        """清空 Action 注册表。"""
        cls._registry.clear()


if __name__ == "__main__":
    ActionLoader.load_actions()
    print(ActionLoader.get_registry())
