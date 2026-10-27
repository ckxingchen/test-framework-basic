from typing import Any

from core.keyword import KeywordActionBase, keyword


class DemoAction(KeywordActionBase):
    """自定义关键字示例"""

    @keyword
    def demo_func_without_return(self, parameter1) -> None:
        """无返回值的方法示例
        :param parameter1: 参数说明
        """
        print(str(parameter1))
        self.log.info(f"处理参数完成：{parameter1}")

    @keyword
    def demo_func_with_return(
        self,
        parameter1,
        parameter2,
    ) -> Any:
        """有返回值的方法示例
        :param parameter1: 参数说明
        :param parameter2: 参数说明
        """
        result = parameter1 + parameter2
        self.log.info("计算返回结果完成")
        return result
