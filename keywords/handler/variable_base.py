from core.comdata import CommonData
from core.container import LocalManager
from core.keyword import KeywordActionBase, keyword
from typing import Any


class VariableAction(KeywordActionBase):

    @keyword
    def set_variable(self, name, value) -> None:
        """设置变量
        :param str name: 变量名
        :param str value: 变量值
        """
        LocalManager.set_value(name, value)
        self.log.info(f'设置局部变量{name}的值为：{value}')

    @keyword
    def get_config_value(self, title_type) -> Any:
        """获取配置文件中值
        :param title_type: 配置项标题
        """
        title_config = CommonData.get_config_item(title_type)
        self.log.info(f'获取配置{title_type}成功：{title_config}')
        return title_config
