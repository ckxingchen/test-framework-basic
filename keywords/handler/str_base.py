import re
from core.keyword import KeywordActionBase, keyword
from typing import Any


class StrAction(KeywordActionBase):

    @keyword
    def re_match_str(self, str_value, pattern) -> Any:
        """字符串正则匹配
        :param str_value: 字符串值
        :param pattern: 正则表达式
        """
        if isinstance(str_value, (dict, list)):
            str_value = str(str_value)
        new_value = re.findall(pattern, str_value)
        self.log.info(f'字符串正则匹配成功：{new_value}')
        return new_value

    @keyword
    def str_join(self, str_var1, str_var2) -> Any:
        """字符串拼接
        :param str_var1: 字符串1
        :param str_var2: 字符串2
        """
        new_str = str(str_var1) + str(str_var2)
        self.log.info(f'字符串拼接成功：{new_str}')
        return new_str


