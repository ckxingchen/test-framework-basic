import os
from core.comdata import CommonData
from core.keyword import KeywordActionBase, keyword
from typing import Any


class FileAction(KeywordActionBase):

    @keyword
    def get_file_joined_path(self, file_name) -> Any:
        """获取file目录文件路径
        :param file_name: 文件名称
        """
        testcase_path = CommonData.get_testcase_path()
        file_path = os.path.join(testcase_path, 'casedata', 'file', file_name)  # noqa
        self.log.info(f'获取file目录文件路径成功：{file_path}')
        return file_path

    @keyword
    def get_file_content(self, file_path, mode) -> Any:
        """获取文件内容
        :param file_path: 文件路径
        :param mode: 模式(r/rb/w/wb)
        """
        with open(file_path, mode) as file:
            content = file.read()
        self.log.info(f'获取文件内容成功：{content}')
        return content

    @keyword
    def get_file_object(self, file_path, mode) -> Any:
        """获取文件对象
        :param file_path: 文件路径
        :param mode: 模式(r/rb/w/wb)
        """
        file_object = open(file_path, mode)
        self.log.info(f'获取文件对象成功：{file_object}')
        return file_object

    @keyword
    def write_file_content(self, file_path, mode, content) -> None:
        """写入文件内容
        :param file_path: 文件路径
        :param mode: 模式(r/rb/w/wb)
        :param content: 文本内容
        """
        with open(file_path, mode) as file:
            file.write(content)
        self.log.info('写入文件内容成功！')

    @keyword
    def is_file_exist(self, file_path) -> Any:
        """判断文件是否存在
        :param file_path: 文件路径
        """
        is_exist = os.path.exists(file_path)
        self.log.info(f'判断文件是否存在：{str(is_exist)}')
        return is_exist


