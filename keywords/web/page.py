import hashlib
import os
import re

from playwright.sync_api import sync_playwright

from core.comdata import CommonData
from core.logger import Log
from core.utils.u_config import parse_bool


class PageManager:
    """管理 Playwright 浏览器、页面、Frame 和弹窗状态。"""

    _browser = None
    _context = None
    _page = None
    _target = None
    _playwright = None
    _dialog = None
    _videos = []
    _trace_started = False
    _record_video = True
    _record_trace = True
    _artifact_name = "web_failure"

    @classmethod
    def prepare_case_artifacts(cls, node_id):
        """根据测试节点设置当前用例的产物文件名。"""
        cls._load_web_options()
        test_name = str(node_id).split("::")[-1]
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", test_name).strip(" ._")
        safe_name = safe_name[:80] or "web_failure"
        digest = hashlib.sha1(str(node_id).encode("utf-8")).hexdigest()[:8]
        cls._artifact_name = f"{safe_name}_{digest}"
        if cls._record_video:
            CommonData.get_artifact_path("video")
        if cls._record_trace:
            CommonData.get_artifact_path("trace")

    @classmethod
    def get_artifact_options(cls):
        """返回当前项目是否启用失败录像和 Trace。"""
        web_config = CommonData.get_config_item("WEB自动化配置")
        return {
            "video": parse_bool(
                web_config.get("record_video"),
                default=True,
                name="record_video",
            ),
            "trace": parse_bool(
                web_config.get("record_trace"),
                default=True,
                name="record_trace",
            ),
        }

    @classmethod
    def get_page(cls):
        """获取当前操作的 Page 或 Frame 对象。"""
        if cls._page is None or cls._page.is_closed():
            cls._init_page()
        return cls._target or cls._page

    @classmethod
    def get_current_page(cls):
        """获取当前操作目标所属的 Page 对象。"""
        target = cls.get_page()
        if hasattr(target, "context"):
            return target
        return target.page

    @classmethod
    def set_page(cls, page):
        """设置当前操作的 Page 对象。"""
        cls._page = page
        cls._target = page
        video = getattr(page, "video", None)
        if video is not None and all(
            video is not current_video for current_video in cls._videos
        ):
            cls._videos.append(video)
        page.on("dialog", cls.set_dialog)

    @classmethod
    def set_frame(cls, frame):
        """设置当前操作的 Frame 对象。"""
        cls._target = frame

    @classmethod
    def switch_to_main_frame(cls):
        """将当前操作目标恢复为 Page。"""
        cls._target = cls.get_current_page()
        cls._page = cls._target
        return cls._target

    @classmethod
    def set_dialog(cls, dialog):
        """保存当前浏览器弹窗对象。"""
        cls._dialog = dialog

    @classmethod
    def get_dialog(cls):
        """获取当前浏览器弹窗对象。"""
        return cls._dialog

    @classmethod
    def clear_dialog(cls):
        """清空当前浏览器弹窗对象。"""
        cls._dialog = None

    @classmethod
    def _init_page(cls):
        """初始化 Playwright、浏览器上下文和页面。"""
        web_config = CommonData.get_config_item("WEB自动化配置")
        browser_type, headless = cls._get_browser_options(web_config)
        browser_path = cls._get_browser_path(web_config)
        browser_size = cls._get_browser_size(web_config)
        maximize = browser_size is None and not headless
        cls._load_web_options(web_config)
        try:
            cls._playwright = sync_playwright().start()
            cls._browser = cls._launch_browser(
                browser_type,
                headless,
                maximize,
                browser_path,
            )
            if browser_size is None and headless:
                browser_size = {"width": 1920, "height": 1080}
            # 新建上下文不继承用户桌面浏览器的语言设置，必须显式指定，
            # 否则相同站点在 Linux 执行器上可能返回英文页面。
            locale = str(web_config.get("locale") or "").strip() or "zh-CN"
            context_options = {"ignore_https_errors": True, "locale": locale}
            if browser_size is None:
                context_options["no_viewport"] = True
            else:
                context_options["viewport"] = browser_size
            if cls._record_video:
                context_options["record_video_dir"] = (
                    CommonData.get_artifact_path("video")
                )
                context_options["record_video_size"] = browser_size or {
                    "width": 1920,
                    "height": 1080,
                }
            cls._context = cls._browser.new_context(**context_options)
            if cls._record_trace:
                cls._context.tracing.start(
                    screenshots=True,
                    snapshots=True,
                    sources=True,
                )
                cls._trace_started = True
            cls.set_page(cls._context.new_page())
            mode = "无头" if headless else "有界面"
            Log().logger.info(
                "已启动 %s 浏览器（%s），语言：%s", browser_type, mode, locale
            )
        except Exception as error:
            cls._close_resources()
            raise TypeError(f"浏览器初始化失败：{error}") from error

    @classmethod
    def _launch_browser(
        cls,
        browser_type,
        headless=False,
        maximize=False,
        browser_path=None,
    ):
        """按配置启动浏览器。"""
        launch_options = {"headless": headless}
        if browser_path:
            launch_options["executable_path"] = browser_path

        if browser_type == "chrome":
            browser_launcher = cls._playwright.chromium
            if not browser_path:
                launch_options["channel"] = "chrome"
        elif browser_type == "edge":
            browser_launcher = cls._playwright.chromium
            if not browser_path:
                launch_options["channel"] = "msedge"
        elif browser_type == "firefox":
            browser_launcher = cls._playwright.firefox
        elif browser_type == "webkit":
            browser_launcher = cls._playwright.webkit
        else:
            raise TypeError(
                "浏览器类型仅支持：chrome/edge/firefox/webkit"
            )

        if maximize and browser_type in {"chrome", "edge"}:
            launch_options["args"] = ["--start-maximized"]
        return browser_launcher.launch(**launch_options)

    @classmethod
    def _get_browser_options(cls, web_config):
        browser_type = str(web_config.get("browser", "")).strip().lower()
        headless = parse_bool(
            web_config.get("headless"),
            default=False,
            name="headless",
        )
        if browser_type not in {
            "chrome",
            "edge",
            "firefox",
            "webkit",
        }:
            raise TypeError(
                "浏览器类型仅支持：chrome/edge/firefox/webkit"
            )
        return browser_type, headless

    @staticmethod
    def _get_browser_path(web_config):
        """解析并校验可选的浏览器可执行文件路径。"""
        value = str(web_config.get("browser_path", "") or "").strip()
        if not value:
            return None
        browser_path = os.path.abspath(
            os.path.expandvars(os.path.expanduser(value))
        )
        if not os.path.isfile(browser_path):
            raise ValueError(
                f"browser_path 指向的浏览器文件不存在：{browser_path}"
            )
        return browser_path

    @staticmethod
    def _get_browser_size(web_config):
        """解析最大化或“宽x高”格式的浏览器尺寸。"""
        value = str(web_config.get("browser_size", "maximize")).strip().lower()
        if value == "maximize":
            return None
        match = re.fullmatch(r"(\d+)\s*[x×]\s*(\d+)", value)
        if match is None:
            raise ValueError("browser_size 仅支持 maximize 或宽x高格式")
        width, height = map(int, match.groups())
        if width <= 0 or height <= 0:
            raise ValueError("browser_size 的宽和高必须大于 0")
        return {"width": width, "height": height}

    @classmethod
    def _load_web_options(cls, web_config=None):
        web_config = web_config or CommonData.get_config_item("WEB自动化配置")
        cls._record_video = parse_bool(
            web_config.get("record_video"),
            default=True,
            name="record_video",
        )
        cls._record_trace = parse_bool(
            web_config.get("record_trace"),
            default=True,
            name="record_trace",
        )

    @classmethod
    def close_page(cls, keep_artifacts=False):
        """关闭浏览器资源，并按用例结果保留或删除产物。"""
        artifacts = cls._close_resources(keep_artifacts=keep_artifacts)
        Log().logger.info("浏览器资源已释放")
        return artifacts

    @classmethod
    def _close_resources(cls, keep_artifacts=False):
        """停止 Trace、释放浏览器，并处理当前用例录像。"""
        logger = Log().logger
        artifacts = {"videos": [], "trace": None}
        videos = list(cls._videos)
        context_closed = cls._context is None
        try:
            if cls._context is not None:
                for page in list(cls._context.pages):
                    video = getattr(page, "video", None)
                    if video is not None and all(
                        video is not current_video for current_video in videos
                    ):
                        videos.append(video)

                if keep_artifacts:
                    for page in cls._context.pages:
                        if not page.is_closed():
                            # 为极短失败用例预留首帧写入时间，避免生成空录像。
                            page.wait_for_timeout(300)
                            break

                if cls._trace_started:
                    try:
                        if keep_artifacts:
                            trace_path = os.path.join(
                                CommonData.get_artifact_path("trace"),
                                f"{cls._artifact_name}.zip",
                            )
                            if os.path.isfile(trace_path):
                                os.remove(trace_path)
                            cls._context.tracing.stop(path=trace_path)
                            artifacts["trace"] = trace_path
                        else:
                            cls._context.tracing.stop()
                    except Exception as error:
                        logger.warning("Playwright Trace 停止失败：%s", error)

                try:
                    cls._context.close()
                    context_closed = True
                except Exception as error:
                    logger.warning("浏览器 Context 关闭失败：%s", error)

            if context_closed:
                cls._process_videos(
                    videos,
                    keep_artifacts=keep_artifacts,
                    artifacts=artifacts,
                )
            elif videos:
                logger.warning("浏览器 Context 未正常关闭，无法保存录像")

            if cls._browser is not None:
                try:
                    cls._browser.close()
                except Exception as error:
                    logger.warning("浏览器 Browser 关闭失败：%s", error)
        finally:
            if cls._playwright is not None:
                try:
                    cls._playwright.stop()
                except Exception as error:
                    logger.warning("Playwright 停止失败：%s", error)
            cls._browser = None
            cls._context = None
            cls._page = None
            cls._target = None
            cls._playwright = None
            cls._dialog = None
            cls._videos = []
            cls._trace_started = False
            cls._record_video = True
            cls._record_trace = True
            cls._artifact_name = "web_failure"
        return artifacts

    @classmethod
    def _process_videos(cls, videos, keep_artifacts, artifacts):
        """保存失败录像，并删除 Playwright 生成的随机录像文件。"""
        logger = Log().logger
        video_count = len(videos)
        for index, video in enumerate(videos, start=1):
            try:
                if keep_artifacts:
                    suffix = f"_{index}" if video_count > 1 else ""
                    video_path = os.path.join(
                        CommonData.get_artifact_path("video"),
                        f"{cls._artifact_name}{suffix}.webm",
                    )
                    if os.path.isfile(video_path):
                        os.remove(video_path)
                    video.save_as(video_path)
                    artifacts["videos"].append(video_path)
                video.delete()
            except Exception as error:
                if keep_artifacts or "Page closed" not in str(error):
                    logger.warning("Playwright 录像处理失败：%s", error)
