import time
from datetime import datetime
from core.keyword import KeywordActionBase, keyword
from typing import Any


class TimeAction(KeywordActionBase):

    @keyword
    def time_sleep(self, second) -> None:
        """时间等待
        :param second: 时间（秒）
        """
        time.sleep(second)
        self.log.info(f'时间等待{second}秒')

    @keyword
    def get_date_now_str(self, date_format="%Y%m%d%H%M%S") -> Any:
        """获取当前时间字符串
        :param date_format: 时间格式
        """
        now_str = datetime.now()
        # 格式化日期为 YYYYMMDD 的形式
        formatted_date = now_str.strftime(date_format)
        self.log.info(f'获取当前时间成功：{formatted_date}')
        return formatted_date
