import re
from typing import Any, Text, Union

from core.keyword import KeywordActionBase, keyword


class CheckAction(KeywordActionBase):
    """04断言"""

    def _verify(self, condition: bool, success_message: str, failure_message: str) -> None:
        if not condition:
            raise AssertionError(failure_message)
        self.log.info(success_message)

    @staticmethod
    def _require(condition: bool, failure_message: str) -> None:
        if not condition:
            raise AssertionError(failure_message)

    @keyword
    def equal(self, real_value: Any, expect_value: Any) -> None:
        """校验两个值相等
        :param real_value: 实际结果
        :param expect_value: 期望结果
        """
        expression = f"{real_value} == {expect_value}"
        self._verify(real_value == expect_value, f"验证成功：{expression}", expression)

    @keyword
    def not_equal(self, real_value: Any, expect_value: Any, message: Text = "") -> None:
        """校验两个值不相等
        :param real_value: 实际结果
        :param expect_value: 期望结果
        """
        expression = f"{real_value} != {expect_value}"
        self._verify(real_value != expect_value, f"验证成功：{expression}", message or expression)

    @keyword
    def greater_than(
        self,
        real_value: Union[int, float],
        expect_value: Union[int, float],
        message: Text = "",
    ) -> None:
        """校验实际结果大于期望结果
        :param real_value: 实际结果
        :param expect_value: 期望结果
        """
        expression = f"{real_value} > {expect_value}"
        self._verify(real_value > expect_value, f"验证成功：{expression}", message or expression)

    @keyword
    def less_than(
        self,
        real_value: Union[int, float],
        expect_value: Union[int, float],
        message: Text = "",
    ) -> None:
        """校验实际结果小于期望结果
        :param real_value: 实际结果
        :param expect_value: 期望结果
        """
        expression = f"{real_value} < {expect_value}"
        self._verify(real_value < expect_value, f"验证成功：{expression}", message or expression)



    @keyword
    def string_equals(self, real_value: Text, expect_value: Any, message: Text = "") -> None:
        """校验两个值转换为字符串后相等
        :param real_value: 实际结果
        :param expect_value: 期望结果
        """
        expression = f"{real_value} = {expect_value}"
        self._verify(
            str(real_value) == str(expect_value),
            f"验证成功：{expression}",
            message or expression,
        )

    @keyword
    def length_equal(self, real_value: Text, expect_value: int, message: Text = "") -> None:
        """校验文本长度等于期望数值
        :param real_value: 实际结果
        :param expect_value: 期望结果
        """
        self._require(
            isinstance(expect_value, int),
            "expect_value should be int type",
        )
        expression = f"len({real_value}) == {expect_value}"
        self._verify(len(real_value) == expect_value, f"验证成功：{expression}", message or expression)






    @keyword
    def contains(self, real_value: Any, expect_value: Any, message: Text = "") -> None:
        """校验实际结果中包含期望结果
        :param real_value: 实际结果
        :param expect_value: 期望结果
        """
        supported = (list, tuple, dict, str, bytes)
        self._require(
            isinstance(real_value, supported),
            "real_value should be list/tuple/dict/str/bytes type",
        )
        expression = f"{expect_value} in {real_value}"
        self._verify(expect_value in real_value, f"验证成功：{expression}", message or expression)




    @keyword
    def regex_match(self, real_value: Text, expect_value: Any, message: Text = "") -> None:
        """校验正则表达式从实际结果开头匹配成功
        :param real_value: 实际结果
        :param expect_value: 期望结果
        """
        self._require(isinstance(expect_value, str), "expect_value should be Text type")
        self._require(isinstance(real_value, str), "real_value should be Text type")
        expression = f"{expect_value} matches {real_value}"
        self._verify(bool(re.match(expect_value, real_value)), f"验证成功：{expression}", message or expression)


