import ast
import os
from typing import Any

from playwright.sync_api import expect

from core.comdata import CommonData
from core.keyword import KeywordActionBase, keyword
from keywords.web.page import PageManager


class WebAction(KeywordActionBase):
    """02Web"""

    _timeout = 10000

    def __init__(self):
        super().__init__()
        self.page = PageManager

    def _parse_kwargs(self, kwargs) -> dict:
        """将GUI文本参数转换为Playwright辅助定位参数。"""
        if kwargs is None or kwargs == "":
            return {}
        if isinstance(kwargs, str):
            try:
                kwargs = ast.literal_eval(kwargs)
            except (SyntaxError, ValueError) as error:
                raise ValueError(
                    f"kwargs格式错误，应为字典文本：{kwargs}"
                ) from error
        if not isinstance(kwargs, dict):
            raise TypeError("kwargs必须为字典或可转换为字典的文本")
        return kwargs

    def _find_element(
        self,
        locator_type,
        locator_value,
        timeout=_timeout,
        kwargs=None,
        many=False,
        wait=True,
    ) -> Any:
        """按定位方式和值获取一个或多个元素。"""
        target = self.page.get_page()
        locator_kwargs = self._parse_kwargs(kwargs)
        locator_type = str(locator_type).lower()

        if locator_type == "id":
            element = target.locator(f"#{locator_value}", **locator_kwargs)
        elif locator_type == "name":
            element = target.locator(
                f"[name='{locator_value}']", **locator_kwargs
            )
        elif locator_type in {"class", "class_name"}:
            element = target.locator(f".{locator_value}", **locator_kwargs)
        elif locator_type in {"css", "css_selector"}:
            element = target.locator(locator_value, **locator_kwargs)
        elif locator_type == "xpath":
            element = target.locator(
                f"xpath={locator_value}", **locator_kwargs
            )
        elif locator_type == "role":
            element = target.get_by_role(locator_value, **locator_kwargs)
        elif locator_type == "text":
            element = target.get_by_text(locator_value, **locator_kwargs)
        elif locator_type == "label":
            element = target.get_by_label(locator_value, **locator_kwargs)
        elif locator_type == "placeholder":
            element = target.get_by_placeholder(
                locator_value, **locator_kwargs
            )
        elif locator_type in {"alt", "alt_text"}:
            element = target.get_by_alt_text(
                locator_value, **locator_kwargs
            )
        elif locator_type == "title":
            element = target.get_by_title(locator_value, **locator_kwargs)
        elif locator_type in {"test_id", "testid"}:
            element = target.get_by_test_id(locator_value)
        else:
            element = target.locator(locator_value, **locator_kwargs)

        if wait:
            element.first.wait_for(
                state="visible",
                timeout=int(float(timeout)),
            )
        return element.all() if many else element.first





    @keyword
    def open_url(self, url, wait_until="load") -> None:
        """打开浏览器地址
        :param url: 浏览器测试地址
        :param wait_until: 页面等待状态
        """
        requested_url = str(url or "").strip()
        target_url = self._build_browser_url(
            requested_url,
            CommonData.get_config_item("项目运行设置"),
        )
        if target_url != requested_url:
            self.log.info(
                f"浏览器地址解析：{requested_url} -> {target_url}"
            )
        self.page.get_current_page().goto(
            target_url, wait_until=wait_until
        )
        self.log.info(f"打开浏览器地址：{target_url}")

    @staticmethod
    def _build_browser_url(url, run_config) -> str:
        """完整 URL 原样使用，相对路径与项目 test_url 拼接。"""
        requested_url = str(url or "").strip()
        if not requested_url:
            raise ValueError("浏览器地址不能为空")
        if requested_url.startswith(("http://", "https://")):
            return requested_url
        if requested_url.startswith("//") or "://" in requested_url:
            raise ValueError(f"浏览器地址无效：{requested_url}")

        base_url = str(run_config.get("test_url", "") or "").strip()
        if not base_url.startswith(("http://", "https://")):
            raise ValueError(f"配置项test_url不是有效URL：{base_url}")
        return f"{base_url.rstrip('/')}/{requested_url.lstrip('/')}"

    @keyword
    def get_url(self) -> str:
        """获取当前页面地址"""
        url = self.page.get_current_page().url
        self.log.info(f"获取当前页面地址：{url}")
        return url

    @keyword
    def get_title(self) -> str:
        """获取页面标题"""
        title = self.page.get_current_page().title()
        self.log.info(f"获取页面标题：{title}")
        return title







    @keyword
    def click_element(
        self,
        locator_type,
        locator_value,
        click_type="left",
        no_wait_after=False,
        kwargs=None,
    ) -> None:
        """点击元素
        :param locator_type: 页面元素定位方式
        :param locator_value: 页面元素定位值
        :param click_type: 点击类型，支持left、double、right
        :param no_wait_after: 点击后是否跳过导航等待
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        click_type = str(click_type).lower()
        if click_type not in {"left", "double", "right"}:
            raise ValueError(
                f"点击类型只支持left、double、right：{click_type}"
            )
        element = self._find_element(
            locator_type, locator_value, kwargs=kwargs
        )
        if click_type == "double":
            element.dblclick(no_wait_after=no_wait_after)
        elif click_type == "right":
            element.click(
                button="right", no_wait_after=no_wait_after
            )
        else:
            element.click(no_wait_after=no_wait_after)
        self.log.info(
            f"点击元素：{locator_type}={locator_value}，"
            f"点击类型：{click_type}"
        )

    @keyword
    def clear_input(
        self, locator_type, locator_value, kwargs=None
    ) -> None:
        """清空输入框
        :param locator_type: 页面元素定位方式
        :param locator_value: 页面元素定位值
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        self._find_element(
            locator_type, locator_value, kwargs=kwargs
        ).clear()
        self.log.info(
            f"清空输入框：{locator_type}={locator_value}"
        )

    @keyword
    def input_text(
        self,
        locator_type,
        locator_value,
        text="",
        kwargs=None,
    ) -> None:
        """输入文本
        :param locator_type: 页面元素定位方式
        :param locator_value: 页面元素定位值
        :param text: 输入文本
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        self._find_element(
            locator_type, locator_value, kwargs=kwargs
        ).fill(text)
        self.log.info(
            f"输入文本成功：{locator_type}={locator_value}"
        )


    @keyword
    def press_key(
        self,
        locator_type,
        locator_value,
        key,
        kwargs=None,
    ) -> None:
        """在元素上按键
        :param locator_type: 页面元素定位方式
        :param locator_value: 页面元素定位值
        :param key: Playwright支持的按键名称
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        self._find_element(
            locator_type, locator_value, kwargs=kwargs
        ).press(key)
        self.log.info(
            f"在元素上按键{key}：{locator_type}={locator_value}"
        )




    @keyword
    def get_text(
        self, locator_type, locator_value, kwargs=None
    ) -> str:
        """获取元素文本
        :param locator_type: 页面元素定位方式
        :param locator_value: 页面元素定位值
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        text = self._find_element(
            locator_type, locator_value, kwargs=kwargs
        ).text_content()
        text = text or ""
        self.log.info(
            f"获取元素文本：{locator_type}={locator_value}，"
            f"文本：{text}"
        )
        return text

    @keyword
    def get_attribute(
        self,
        locator_type,
        locator_value,
        name,
        kwargs=None,
    ) -> str:
        """获取元素属性
        :param locator_type: 页面元素定位方式
        :param locator_value: 页面元素定位值
        :param name: 属性名称
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        value = self._find_element(
            locator_type, locator_value, kwargs=kwargs
        ).get_attribute(name)
        value = value or ""
        self.log.info(
            f"获取元素属性{name}：{locator_type}={locator_value}，"
            f"属性值：{value}"
        )
        return value

    @keyword
    def is_visible(
        self, locator_type, locator_value, kwargs=None
    ) -> bool:
        """判断元素是否可见
        :param locator_type: 页面元素定位方式
        :param locator_value: 页面元素定位值
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        visible = self._find_element(
            locator_type,
            locator_value,
            kwargs=kwargs,
            wait=False,
        ).is_visible()
        self.log.info(
            f"元素可见状态：{locator_type}={locator_value}，"
            f"结果：{visible}"
        )
        return visible



    @keyword
    def select_option(
        self,
        locator_type,
        locator_value,
        value,
        select_type="value",
        kwargs=None,
    ) -> list:
        """选择下拉框选项
        :param locator_type: 页面元素定位方式
        :param locator_value: 页面元素定位值
        :param value: 下拉选项值
        :param select_type: 选择方式，支持value、text、label、index
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        select_type = str(select_type).lower()
        element = self._find_element(
            locator_type, locator_value, kwargs=kwargs
        )
        if select_type == "index":
            selected = element.select_option(index=int(value))
        elif select_type in {"text", "label"}:
            selected = element.select_option(label=value)
        elif select_type == "value":
            selected = element.select_option(value=value)
        else:
            raise ValueError(f"下拉选择方式不支持：{select_type}")
        self.log.info(
            f"选择下拉框选项：{locator_type}={locator_value}，"
            f"选择方式：{select_type}，选项：{value}"
        )
        return selected

    @keyword
    def set_checked(
        self,
        locator_type,
        locator_value,
        checked=True,
        kwargs=None,
    ) -> None:
        """设置复选框或单选框状态
        :param locator_type: 页面元素定位方式
        :param locator_value: 页面元素定位值
        :param checked: 是否选中
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        self._find_element(
            locator_type, locator_value, kwargs=kwargs
        ).set_checked(checked)
        self.log.info(
            f"设置元素选中状态：{locator_type}={locator_value}，"
            f"状态：{checked}"
        )

    @keyword
    def upload_file(
        self,
        locator_type,
        locator_value,
        file_path,
        kwargs=None,
    ) -> None:
        """上传文件
        :param locator_type: 页面元素定位方式
        :param locator_value: 页面元素定位值
        :param file_path: 上传文件路径
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"上传文件不存在：{file_path}")
        self._find_element(
            locator_type,
            locator_value,
            kwargs=kwargs,
            wait=False,
        ).set_input_files(file_path)
        self.log.info(f"上传文件：{file_path}")

    @keyword
    def download_by_click(
        self,
        locator_type,
        locator_value,
        save_path=None,
        kwargs=None,
    ) -> str:
        """点击元素并下载文件
        :param locator_type: 页面元素定位方式
        :param locator_value: 页面元素定位值
        :param save_path: 下载文件保存路径
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        page = self.page.get_current_page()
        with page.expect_download() as download_info:
            self.click_element(
                locator_type, locator_value, kwargs=kwargs
            )
        download = download_info.value
        if save_path:
            if os.path.isdir(save_path):
                save_path = os.path.join(
                    save_path, download.suggested_filename
                )
            os.makedirs(
                os.path.dirname(os.path.abspath(save_path)),
                exist_ok=True,
            )
            download.save_as(save_path)
            self.log.info(f"下载文件并保存到：{save_path}")
            return save_path
        download_path = download.path()
        self.log.info(f"下载文件成功：{download_path}")
        return download_path

    @keyword
    def switch_to_frame(
        self, locator_type, locator_value, kwargs=None
    ) -> Any:
        """切换到iframe
        :param locator_type: iframe定位方式
        :param locator_value: iframe定位值
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        iframe = self._find_element(
            locator_type,
            locator_value,
            kwargs=kwargs,
            wait=False,
        )
        iframe.wait_for(state="attached", timeout=self._timeout)
        handle = iframe.element_handle()
        frame = handle.content_frame() if handle else None
        if frame is None:
            raise RuntimeError(
                f"未获取到iframe：{locator_type}={locator_value}"
            )
        self.page.set_frame(frame)
        self.log.info(
            f"切换到iframe：{locator_type}={locator_value}"
        )
        return frame

    @keyword
    def switch_to_main_frame(self) -> Any:
        """切换回主页面"""
        page = self.page.switch_to_main_frame()
        self.log.info("切换回主页面成功")
        return page









    @keyword
    def wait_for_url(self, url, timeout=None) -> None:
        """等待页面地址匹配
        :param url: 页面地址、glob或正则
        :param timeout: 超时时间，单位毫秒
        """
        wait_timeout = (
            self._timeout
            if timeout is None
            else int(float(timeout))
        )
        self.page.get_current_page().wait_for_url(
            url, timeout=wait_timeout
        )
        self.log.info(f"等待页面地址匹配完成：{url}")

    @keyword
    def assert_visible(
        self, locator_type, locator_value, kwargs=None
    ) -> None:
        """断言元素可见
        :param locator_type: 页面元素定位方式
        :param locator_value: 页面元素定位值
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        element = self._find_element(
            locator_type,
            locator_value,
            kwargs=kwargs,
            wait=False,
        )
        expect(element).to_be_visible(timeout=self._timeout)
        self.log.info(
            f"断言元素可见成功：{locator_type}={locator_value}"
        )


    @keyword
    def assert_text(
        self,
        locator_type,
        locator_value,
        text,
        kwargs=None,
    ) -> None:
        """断言元素文本完全匹配
        :param locator_type: 页面元素定位方式
        :param locator_value: 页面元素定位值
        :param text: 期望文本
        :param kwargs: Playwright辅助定位参数，可填写字典文本
        """
        element = self._find_element(
            locator_type,
            locator_value,
            kwargs=kwargs,
            wait=False,
        )
        expect(element).to_have_text(text, timeout=self._timeout)
        self.log.info(
            f"断言元素文本完全匹配成功："
            f"{locator_type}={locator_value}"
        )






    @keyword
    def screenshot(self, path=None, full_page=True) -> bytes:
        """截取页面截图
        :param path: 截图保存路径
        :param full_page: 是否截取完整页面
        """
        if path:
            os.makedirs(
                os.path.dirname(os.path.abspath(path)),
                exist_ok=True,
            )
        image = self.page.get_current_page().screenshot(
            path=path, full_page=full_page
        )
        self.log.info(
            f"截取页面截图成功：{path or '未保存到文件'}"
        )
        return image



