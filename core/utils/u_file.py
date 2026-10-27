"""文件和目录操作工具。"""

from pathlib import Path
import shutil
from typing import Literal


FileOperation = Literal["copy", "cut", "delete", "rename"]


def clear_directory(directory: str) -> None:
    """删除目录中的全部内容，但保留目录本身。"""
    target = Path(directory)
    if not target.is_dir():
        print(f"警告：'{directory}' 不是目录或不存在")
        return

    for child in target.iterdir():
        try:
            delete_path(child)
        except Exception as error:
            print(f"删除失败: {child} - {error}")


def file_copy(source_path: str | Path, destination_path: str | Path) -> None:
    """复制文件或目录到目标路径。"""
    source = Path(source_path)
    destination = Path(destination_path)
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy(source, destination)


def move_path(source_path: str | Path, destination_path: str | Path) -> None:
    """移动文件或目录到目标路径。"""
    source = Path(source_path)
    if source.is_dir():
        shutil.copytree(source, destination_path)
        shutil.rmtree(source)
    else:
        shutil.move(str(source), str(destination_path))


def rename_path(source_path: str | Path, destination_path: str | Path) -> None:
    """重命名文件或目录。"""
    shutil.move(str(source_path), str(destination_path))


def delete_path(path: str | Path) -> None:
    """删除文件、符号链接或目录。"""
    target = Path(path)
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)
    else:
        raise FileNotFoundError(f"待删除路径不存在: {target}")


def file_operate(
    operation: FileOperation,
    source_path: str | Path,
    destination_path: str | Path | None = None,
) -> None:
    """按操作名称复制、移动、删除或重命名文件系统对象。"""
    if operation == "delete":
        delete_path(source_path)
        return

    if destination_path is None:
        raise ValueError(f"{operation} 操作必须提供目标路径")

    operations = {
        "copy": file_copy,
        "cut": move_path,
        "rename": rename_path,
    }
    try:
        handler = operations[operation]
    except KeyError as exc:
        raise Exception(f"{operation}操作未实现！") from exc
    handler(source_path, destination_path)


def directory_contains_files(directory: str | Path) -> bool:
    """判断目录的当前层级是否包含文件。"""
    target = Path(directory)
    if not target.is_dir():
        raise Exception(f"{directory}不存在！")
    return any(child.is_file() for child in target.iterdir())
