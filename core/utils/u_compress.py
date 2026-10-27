"""压缩文件相关工具。"""

import os
from zipfile import ZIP_DEFLATED, ZipFile


def create_zip_archive(source_directory: str, archive_path: str) -> str:
    """将目录及其内容压缩为 ZIP 文件，并返回压缩文件路径。"""
    source_parent_length = len(os.path.dirname(source_directory))
    with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as archive:
        for parent, _, file_names in os.walk(source_directory):
            for file_name in file_names:
                file_path = os.path.join(parent, file_name)
                archive_name = file_path[source_parent_length:].strip(os.path.sep)
                archive.write(file_path, archive_name)
    return archive_path
