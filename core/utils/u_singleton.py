from functools import wraps
from threading import Lock
from typing import Any, Callable, Optional, Type, TypeVar


InstanceType = TypeVar("InstanceType")


def singleton(cls: Type[InstanceType]) -> Callable[..., InstanceType]:
    """将类包装为线程安全的惰性单例工厂。"""
    instance: Optional[InstanceType] = None
    lock = Lock()

    @wraps(cls)
    def get_instance(*args: Any, **kwargs: Any) -> InstanceType:
        nonlocal instance
        if instance is None:
            with lock:
                if instance is None:
                    instance = cls(*args, **kwargs)
        return instance

    return get_instance
