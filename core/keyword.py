import ast
import dis
import inspect
import logging
import textwrap
from functools import wraps
from typing import Any

from core.logger import Log


# YAML 关键字返回值使用的框架保留参数名。
RESULT_PARAM_NAME = "result"
# 未显式指定返回变量名时使用的默认变量名。
RESULT_PARAM_DEFAULT = "result"
# 生成关键字模板时使用的返回值参数说明。
RESULT_PARAM_DESC = "关键字返回结果（可引用）"


def keyword(func):
    """标记需要注册和展示的实例关键字方法。"""
    if not inspect.isfunction(func):
        raise TypeError("@keyword只能用于实例方法")

    @wraps(func)
    def execute_keyword(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as error:
            logger = getattr(self, "log", None)
            if logger is not None and not getattr(logger, "error_logged", False):
                logger.exception("关键字执行失败：%s", error)
            raise

    setattr(execute_keyword, "__keyword__", True)
    return execute_keyword


def is_keyword(func: Any) -> bool:
    """判断方法是否已声明为关键字。"""
    return bool(getattr(func, "__keyword__", False))


def keyword_has_result(func: Any) -> bool:
    """优先根据返回类型、其次根据方法实现判断是否需要保存结果。"""
    func = inspect.unwrap(func)
    annotation = inspect.signature(func).return_annotation
    if annotation is not inspect.Signature.empty:
        return annotation not in {
            None,
            type(None),
            "None",
        }
    return _has_value_return(func)


def _has_value_return(func: Any) -> bool:
    """判断未声明返回类型的方法是否包含带值返回。"""
    try:
        source = textwrap.dedent(inspect.getsource(func))
        tree = ast.parse(source)
        function_node = next(
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        return _ReturnValueVisitor(function_node).has_result
    except (OSError, TypeError, SyntaxError, StopIteration):
        return _bytecode_has_value_return(func)


class _ReturnValueVisitor(ast.NodeVisitor):
    """只检查当前方法，不检查内部函数中的返回语句。"""

    def __init__(self, function_node):
        self.function_node = function_node
        self.has_result = False
        self.visit(function_node)

    def visit_FunctionDef(self, node):
        if node is self.function_node:
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        if node is self.function_node:
            self.generic_visit(node)

    def visit_Lambda(self, node):
        return

    def visit_ClassDef(self, node):
        return

    def visit_Return(self, node):
        if node.value is not None and not (
            isinstance(node.value, ast.Constant)
            and node.value.value is None
        ):
            self.has_result = True


def _bytecode_has_value_return(func: Any) -> bool:
    """源码不可用时通过当前方法的字节码识别带值返回。"""
    instructions = [
        instruction
        for instruction in dis.get_instructions(func)
        if instruction.opname not in {"CACHE", "NOP", "RESUME"}
    ]
    for index, instruction in enumerate(instructions):
        if instruction.opname == "RETURN_CONST":
            if instruction.argval is not None:
                return True
        elif instruction.opname == "RETURN_VALUE" and index:
            previous = instructions[index - 1]
            if not (
                previous.opname == "LOAD_CONST"
                and previous.argval is None
            ):
                return True
    return False


class KeywordLoggerAdapter(logging.LoggerAdapter):
    """为关键字业务日志自动补充统一执行前缀。"""

    def set_context(self, prefix: str) -> None:
        """设置当前关键字日志前缀并重置明细状态。"""
        self.extra["prefix"] = prefix
        self.extra["detail_logged"] = False
        self.extra["error_logged"] = False

    @property
    def detail_logged(self) -> bool:
        """返回当前关键字是否已记录业务明细。"""
        return bool(self.extra.get("detail_logged", False))

    @property
    def error_logged(self) -> bool:
        """返回当前关键字是否已经记录错误。"""
        return bool(self.extra.get("error_logged", False))

    def log(self, level, msg, *args, **kwargs):
        if level >= logging.ERROR:
            self.extra["error_logged"] = True
        return super().log(level, msg, *args, **kwargs)

    def process(self, message, kwargs):
        """拼接关键字执行前缀。"""
        self.extra["detail_logged"] = True
        return f"{self.extra.get('prefix', '')}{message}", kwargs


class KeywordActionBase:
    """定义实例关键字的公共约束和基础能力。"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for method_name, method in cls.__dict__.items():
            if method_name.startswith("_"):
                continue
            if isinstance(method, (classmethod, staticmethod)):
                func = method.__func__
                if not is_keyword(func):
                    continue
                raise TypeError(
                    f"{cls.__name__}.{method_name}必须定义为实例方法"
                )
            if not inspect.isfunction(method) or not is_keyword(method):
                continue

            signature = inspect.signature(method)
            if RESULT_PARAM_NAME in signature.parameters:
                raise TypeError(
                    f"{cls.__name__}.{method_name}不能定义框架虚拟参数result"
                )

    def __init__(self):
        self.log = KeywordLoggerAdapter(
            Log().logger,
            {"prefix": "", "detail_logged": False, "error_logged": False},
        )

    def _set_keyword_context(
        self,
        action_name,
        method_name,
        result_name=None,
    ) -> None:
        """设置当前关键字的日志执行上下文。"""
        result_text = (
            f"，返回值{result_name}" if result_name else ""
        )
        self.log.set_context(
            f"执行{action_name}.{method_name}方法{result_text}==>"
        )

    def _has_logged_detail(self) -> bool:
        """判断当前关键字是否已经记录业务明细。"""
        return self.log.detail_logged
