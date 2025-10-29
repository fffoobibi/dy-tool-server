"""
路径处理工具 - 帮助处理 PyInstaller 打包后的路径问题
"""

import os
import sys


def is_packaged():
    """
    检查当前环境是否为打包后的环境
    :return: bool
    """
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_app_path():
    """
    获取应用程序的根路径，适用于开发环境和打包后的环境

    Returns:
        str: 应用程序根路径
    """
    if getattr(sys, "frozen", False):
        # PyInstaller 创建了一个临时文件夹，并将应用程序放在其中
        # _MEIPASS 指向这个临时文件夹
        return sys._MEIPASS
    else:
        # 正常情况下，直接返回脚本所在的目录
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_path(relative_path):
    """
    获取资源的绝对路径，不管是在开发环境还是在打包后的环境

    Args:
        relative_path (str): 相对于应用程序根目录的路径

    Returns:
        str: 资源的绝对路径
    """
    base_path = get_app_path()
    return os.path.join(base_path, relative_path)


def setup_environment():
    """
    设置环境变量和路径，确保应用程序可以在打包环境中正常运行
    """
    # 将应用程序根目录添加到系统路径
    app_path = get_app_path()
    if app_path not in sys.path:
        sys.path.insert(0, app_path)

    # 这里可以添加其他环境设置，如临时文件目录等
    os.environ["APP_PATH"] = app_path

    # 打印环境信息，用于调试
    # print(f"应用根目录: {app_path}")
    # print(f"系统路径: {sys.path}")

    return app_path
