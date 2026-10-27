from typing import Any

from jsonpath_ng import parse

from core.keyword import KeywordActionBase, keyword


class JsonAction(KeywordActionBase):

    @keyword
    def get_json_value(self, json_data, json_path) -> Any:
        """获取json中的值
        :param json_data: 原始json数据
        :param json_path: jsonpath表达式
        """
        matches = parse(json_path).find(json_data)
        if not matches:
            raise ValueError(f"JSONPath未匹配到数据：{json_path}")
        value = matches[0].value
        self.log.info(f'获取json中的值成功：{value}')
        return value



