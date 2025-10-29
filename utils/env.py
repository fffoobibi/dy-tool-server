import os
from typing import Any, Dict, Optional, TypeVar, Callable, Union, cast
from functools import lru_cache
from dotenv import load_dotenv

import lazy_object_proxy


T = TypeVar("T")


class EnvLoader:
    """环境变量延迟加载器

    支持:
    1. 延迟加载环境变量
    2. 类型转换
    3. 缓存结果，避免重复读取
    4. 支持回调函数处理复杂逻辑
    """

    _instance = None
    _initialized = False
    _env_cache: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EnvLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # 初始化代码
            self._initialized = True

    @staticmethod
    def load_env_file(env_file: Optional[str] = None):
        """加载环境变量文件"""
        if env_file and os.path.exists(env_file):
            load_dotenv(env_file)
            return True
        return False

    @lru_cache(maxsize=128)
    def get(
        self,
        key: str,
        default: Optional[T] = None,
        converter: Optional[Callable[[str], T]] = None,
        lazy: bool = False,
    ) -> T:
        """获取环境变量，支持类型转换和默认值

        Args:
            key: 环境变量名
            default: 默认值，如果环境变量不存在则返回此值
            converter: 类型转换函数，将字符串转换为需要的类型
            lazy: 是否返回延迟加载的代理对象

        Returns:
            转换后的环境变量值、默认值或其代理对象
        """
        if lazy:
            # 返回延迟加载的代理对象
            return lazy_object_proxy.Proxy(
                lambda: self._get_value(key, default, converter)
            )
        else:
            # 直接返回值
            return self._get_value(key, default, converter)

    def _get_value(
        self,
        key: str,
        default: Optional[T] = None,
        converter: Optional[Callable[[str], T]] = None,
    ) -> T:
        """实际获取环境变量值的内部方法"""
        # 先检查缓存
        if key in self._env_cache:
            return self._env_cache[key]

        # 从环境变量获取
        value = os.environ.get(key)

        # 如果环境变量不存在，返回默认值
        if value is None:
            return default

        # 如果提供了转换函数，应用转换
        if converter:
            try:
                value = converter(value)
            except Exception as e:
                print(f"环境变量 {key} 转换失败: {e}，使用默认值")
                return default

        # 缓存结果
        self._env_cache[key] = value
        return value

    def get_int(
        self, key: str, default: Optional[int] = None, lazy: bool = False
    ) -> Optional[int]:
        """获取整数类型环境变量"""
        return self.get(key, default, int, lazy)

    def get_float(
        self, key: str, default: Optional[float] = None, lazy: bool = False
    ) -> Optional[float]:
        """获取浮点类型环境变量"""
        return self.get(key, default, float, lazy)

    def get_bool(
        self, key: str, default: Optional[bool] = None, lazy: bool = False
    ) -> Optional[bool]:
        """获取布尔类型环境变量"""

        def parse_bool(val: str) -> bool:
            return val.lower() in ("true", "1", "yes", "y", "on")

        return self.get(key, default, parse_bool, lazy)

    def get_path(
        self, key: str, default: Optional[str] = None, lazy: bool = False
    ) -> Optional[str]:
        """获取文件路径类型环境变量"""
        if lazy:
            return lazy_object_proxy.Proxy(lambda: self._get_path_value(key, default))
        else:
            return self._get_path_value(key, default)

    def _get_path_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取路径值的内部方法"""
        path = self.get(key, default)
        if path and not os.path.isabs(path):
            # 将相对路径转换为绝对路径
            path = os.path.abspath(path)
        return path

    def clear_cache(self):
        """清除缓存，强制重新读取环境变量"""
        self._env_cache.clear()
        self.get.cache_clear()  # 清除lru_cache


# 创建全局单例实例
env = EnvLoader()
