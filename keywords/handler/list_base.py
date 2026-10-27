from ast import literal_eval
from typing import Any

from core.keyword import KeywordActionBase, keyword


class ListAction(KeywordActionBase):

    @staticmethod
    def _parse_list(value):
        if isinstance(value, str):
            value = literal_eval(value)
        if not isinstance(value, list):
            raise TypeError("列表数据必须是list或合法的列表字符串")
        return value

    @keyword
    def get_list_value(self, list_value, list_index='0') -> Any:
        """列表中取值
        :param list_value: 列表数据
        :param list_index: 列表索引
        """
        list_value = self._parse_list(list_value)
        if isinstance(list_index, str):
            list_index = int(list_index)
        element_value = list_value[list_index]
        self.log.info(f'获取列表中值成功：{element_value}')
        return element_value



