"""Playwright 外部浏览器和 FFmpeg 运行环境配置。"""

import os
import sys
from pathlib import Path


def configure_playwright_runtime() -> None:
    """让打包程序使用当前用户环境安装的 Playwright 资源。"""

    if not getattr(sys, "frozen", False):
        return
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return

    if sys.platform == "win32":
        cache_root = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
        browser_root = cache_root / "ms-playwright"
    elif sys.platform == "darwin":
        browser_root = Path.home() / "Library" / "Caches" / "ms-playwright"
    else:
        browser_root = Path.home() / ".cache" / "ms-playwright"

    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_root)
