from core.keyword import KeywordActionBase, keyword
from typing import Any


class DictAction(KeywordActionBase):

    @keyword
    def dict_add_value(self, dict_data, key, value) -> Any:
        """字典中增加值
        :param dict_data: 字典数据
        :param key: 字典的KEY
        :param value: 字典的VALUE
        """
        dict_data[key] = value
        self.log.info(f'字典中增加值成功：{str(dict_data)}')
        return dict_data

    @keyword
    def dict_update(self, dict_data, new_dict) -> Any:
        """字典合并更新
        :param dict_data: 字典数据
        :param new_dict: 新的字典数据
        """
        dict_data.update(new_dict)
        self.log.info(f'两个字典合并更新成功：{str(dict_data)}')
        return dict_data


