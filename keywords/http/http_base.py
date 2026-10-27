from urllib.parse import urlparse

import urllib3
from urllib3.exceptions import InsecureRequestWarning

from core.comdata import CommonData
from core.container import LocalManager
from core.keyword import KeywordActionBase, keyword
from core.utils.u_config import parse_bool
from core.utils.u_dict import exclude_keys
from keywords.http.session import SessionManager


urllib3.disable_warnings(InsecureRequestWarning)
# HTTP 配置未提供超时时间时使用的秒数。
DEFAULT_REQUEST_TIMEOUT = 30.0
# HTTP 配置未提供证书校验开关时使用的默认值。
DEFAULT_VERIFY_TLS = False


class HttpAction(KeywordActionBase):
    """01Http"""

    @keyword
    def cookies_clear(self) -> None:
        """清空session"""
        SessionManager.get_session().cookies.clear()
        self.log.info("清除Session中的Cookies成功！")




    @keyword
    def request(self, method, url, index=None, **kwargs) -> None:
        """接口请求公共封装
        :param method: 请求方法(get/post等)
        :param url: 请求URL
        :param index: 可选索引
        :param headers: 请求头
        :param params: URL参数
        :param data: 表单数据
        :param json: JSON数据
        :param files: 文件对象
        :param timeout: 请求超时时间（秒）
        :param result_text: 返回响应文本
        :param result_json: 返回响应JSON
        :param result_content: 返回响应内容
        :param result_code: 返回状态码
        """
        result_keys = {
            "result_code",
            "result_json",
            "result_text",
            "result_content",
        }
        request_kwargs = exclude_keys(kwargs, result_keys)
        self.log.info(f"{method}接口调用开始==>{url}")
        self._request_kwargs(method, **request_kwargs)
        response = self._request_send(
            method,
            url,
            index,
            **request_kwargs,
        )
        self._response_kwargs(method, response, **kwargs)
        self.log.info(
            f"{method}接口的响应时间==>"
            f"{str(response.elapsed.total_seconds())}"
        )
        self.log.info(f"{method}接口调用完成==>{url}")

    def _request_send(self, method, url, index=None, **request_kwargs):
        """请求发送"""
        try:
            config_data = CommonData.get_config_data()
            run_config = config_data["项目运行设置"]
            http_config = config_data.get("HTTP自动化配置", {})
            url = self._build_request_url(url, index, run_config)
            timeout = request_kwargs.get("timeout")
            if timeout in (None, ""):
                timeout = http_config.get(
                    "request_timeout",
                    DEFAULT_REQUEST_TIMEOUT,
                )
            request_kwargs["timeout"] = float(timeout)
            if request_kwargs["timeout"] <= 0:
                raise ValueError("请求超时时间必须大于0")
            request_kwargs["verify"] = parse_bool(
                http_config.get("verify_tls"),
                default=DEFAULT_VERIFY_TLS,
                name="verify_tls",
            )
            return SessionManager.get_session().request(
                method,
                url,
                **request_kwargs,
            )
        except Exception as error:
            raise Exception(f"接口请求失败:{error}") from error

    @staticmethod
    def _build_request_url(url, index, config):
        """绝对 URL 原样使用，相对路径与所选环境地址拼接。"""
        request_url = str(url).strip()
        if not request_url:
            raise ValueError("请求URL不能为空")
        parsed_url = urlparse(request_url)
        if parsed_url.scheme:
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                raise ValueError(f"请求URL无效：{request_url}")
            return request_url

        config_key = "test_url" if not index else f"test_url{index}"
        base_url = config.get(config_key, "").strip()
        parsed_base_url = urlparse(base_url)
        if (
            parsed_base_url.scheme not in {"http", "https"}
            or not parsed_base_url.netloc
        ):
            raise ValueError(f"配置项{config_key}不是有效URL：{base_url}")
        return f"{base_url.rstrip('/')}/{request_url.lstrip('/')}"

    def _request_kwargs(self, method, **kwargs):
        """请求参数处理"""
        try:
            if kwargs.get("headers"):
                self.log.info(
                    f"{method}接口请求头headers==>"
                    f"{str(kwargs.get('headers'))}"
                )
            if kwargs.get("params"):
                self.log.info(
                    f"{method}接口查询参数params==>"
                    f"{str(kwargs.get('params'))}"
                )
            if kwargs.get("data"):
                self.log.info(
                    f"{method}接口请求体data==>"
                    f"{str(kwargs.get('data'))}"
                )
            if kwargs.get("json"):
                self.log.info(
                    f"{method}接口请求体json==>"
                    f"{str(kwargs.get('json'))}"
                )
            if kwargs.get("files"):
                self.log.info(
                    f"{method}文件对象files==>"
                    f"{str(kwargs.get('files'))}"
                )
        except Exception as error:
            self.log.warning(f"请求参数日志记录失败：{error}")

    def _response_kwargs(self, method, response, **kwargs):
        """响应参数处理"""
        if kwargs.get("result_code"):
            result_code = response.status_code
            LocalManager.set_value(
                kwargs.get("result_code"),
                str(result_code),
            )
            self.log.debug(f"{method}接口的响应码==>{str(result_code)}")
        if kwargs.get("result_json"):
            result_json = response.json()
            LocalManager.set_value(
                kwargs.get("result_json"),
                result_json,
            )
            self.log.info(f"{method}接口的json响应体==>{str(result_json)}")
        if kwargs.get("result_text"):
            result_text = response.text
            LocalManager.set_value(
                kwargs.get("result_text"),
                result_text,
            )
            self.log.info(f"{method}接口的text响应体：{result_text}")
        if kwargs.get("result_content"):
            result_content = response.content
            LocalManager.set_value(
                kwargs.get("result_content"),
                result_content,
            )
            self.log.debug(f"{method}接口的content响应体：{result_content}")


