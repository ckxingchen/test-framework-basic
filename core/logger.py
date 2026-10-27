import logging
import os
import sys
import time
from typing import Optional, Union
from core.comdata import CommonData
from core.utils.u_singleton import singleton


# 框架统一日志格式，修改后同时影响控制台和文件日志。
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# 项目未配置日志级别时使用的默认级别。
DEFAULT_LOG_LEVEL = "INFO"


@singleton
class Log:
    """管理框架控制台日志和当前项目的运行日志。"""

    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name
        self._logger = logging.getLogger(name)
        self._formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
        self._file_handler: Optional[logging.FileHandler] = None
        self._bound_project: Optional[str] = None
        self._stream_handler = self._create_stream_handler()

        self._configure_logger()

    @property
    def logger(self) -> logging.Logger:
        """返回日志器，并确保文件日志绑定到当前项目。"""
        self._bind_project_file_handler()
        return self._logger

    def _configure_logger(self) -> None:
        """初始化日志级别并挂载控制台处理器。"""
        self._logger.setLevel(DEFAULT_LOG_LEVEL)
        self._logger.addHandler(self._stream_handler)

    def _create_stream_handler(self) -> logging.StreamHandler:
        """创建用于控制台输出的日志处理器。"""
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(DEFAULT_LOG_LEVEL)
        stream_handler.setFormatter(self._formatter)
        return stream_handler

    def _bind_project_file_handler(self) -> None:
        """项目变化时切换运行日志文件，避免写入旧项目。"""
        project_name = CommonData.RUN_DATA.get("project_name")
        if project_name == self._bound_project and self._file_handler is not None:
            return
        self._remove_project_file_handler()
        if not project_name:
            return

        run_config = CommonData.get_config_item("项目运行设置")
        log_level = run_config.get("log_level", DEFAULT_LOG_LEVEL)
        log_file_name = (
            time.strftime("%Y%m%d_%H", time.localtime())
            + ".log"
        )
        log_path = os.path.join(CommonData.get_log_path(), log_file_name)

        self._file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        self._file_handler.setLevel(log_level)
        self._file_handler.setFormatter(self._formatter)

        self._stream_handler.setLevel(log_level)
        self._logger.setLevel(log_level)
        self._logger.addHandler(self._file_handler)
        self._bound_project = project_name

    def _remove_project_file_handler(self) -> None:
        if self._file_handler is None:
            self._bound_project = None
            return
        self._logger.removeHandler(self._file_handler)
        self._file_handler.close()
        self._file_handler = None
        self._bound_project = None

    @staticmethod
    def redirect_console_output(file_path: Union[str, os.PathLike]) -> None:
        """将标准输出和标准错误重定向到 Terminal.log。"""
        terminal_log_path = os.path.join(file_path, "Terminal.log")
        terminal_stream = open(terminal_log_path, mode="w")
        sys.stdout = terminal_stream
        sys.stderr = terminal_stream


if __name__ == "__main__":
    first_logger = Log().logger
    print(first_logger)
    second_logger = Log().logger
    print(second_logger)
