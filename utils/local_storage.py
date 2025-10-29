"""本地持久化统一管理模块。

提供统一的本地持久化目录及便捷的读写方法，面向对象封装为 Storage 类。
"""

from __future__ import annotations

import os
import json
import tempfile
import shutil
import time
from pathlib import Path
from typing import Optional, Any, Iterable, Union

# 默认本地存储根目录：用户主目录下 .app_local_storage
_DEFAULT_ROOT = Path(os.path.expanduser("~")) / ".app_local_storage"
try:
    _DEFAULT_ROOT.mkdir(parents=True, exist_ok=True)
except Exception:  # 忽略目录创建异常
    pass

__all__ = [
    "Storage",
    "storage",
]


class Storage:
    """本地存储封装类，支持多种快捷访问方式。

    使用示例:
        storage.write_text("a.txt", "hello")
        storage.write("a.txt", "hello")                # 简写
        storage["a.txt"] = "hello"                      # 赋值语法
        txt = storage.read_text("a.txt")
        txt2 = storage.read("a.txt")
        txt3 = storage["a.txt"]                         # 取值语法
        storage.set("config.json", {"a":1})            # JSON 自动序列化
        cfg = storage.get("config.json")                 # JSON 自动反序列化
        for f in storage.list(): ...                     # 列出文件
        storage.delete("a.txt")

        # 缓存功能
        storage.write("cache.txt", "data", cache_ttl=3600)  # 1小时缓存
        storage.set("cache.json", {"data": 123}, cache_ttl=1800)  # 30分钟缓存
    """

    def __init__(self, root: Path | str | None = None) -> None:
        if root is None:
            self._root = _DEFAULT_ROOT
        else:
            self._root = Path(root)
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _get_cache_info_path(self, name: str) -> Path:
        """获取缓存信息文件路径"""
        return self._root / f".{name}.cache_info"

    def _is_cache_valid(self, name: str) -> bool:
        """检查缓存是否有效"""
        cache_info_path = self._get_cache_info_path(name)
        if not cache_info_path.exists():
            return False

        try:
            with open(cache_info_path, "r") as f:
                cache_data = json.load(f)

            ttl = cache_data.get("ttl", 0)
            if ttl <= 0:
                return True  # 永久缓存

            created_time = cache_data.get("created_time", 0)
            return time.time() - created_time < ttl
        except Exception:
            return False

    def _set_cache_info(self, name: str, cache_ttl: Union[int, float]) -> None:
        """设置缓存信息"""
        if cache_ttl <= 0:
            return

        cache_info_path = self._get_cache_info_path(name)
        cache_data = {"ttl": cache_ttl, "created_time": time.time()}

        try:
            with open(cache_info_path, "w") as f:
                json.dump(cache_data, f)
        except Exception:
            pass

    def _clean_cache_info(self, name: str) -> None:
        """清理缓存信息文件"""
        cache_info_path = self._get_cache_info_path(name)
        try:
            cache_info_path.unlink(missing_ok=True)
        except Exception:
            pass

    # --- 基础路径 ---
    @property
    def root(self) -> Path:
        return self._root

    def path(self, name: str) -> Path:
        return self._root / name

    # --- 核心文本读写（原有接口保留） ---
    def read_text(
        self,
        name: str,
        default: Optional[str] = None,
        encoding: str = "utf-8",
        check_cache: bool = True,
    ) -> Optional[str]:
        # 检查缓存有效性
        if check_cache and not self._is_cache_valid(name):
            return default

        try:
            with open(self.path(name), "r", encoding=encoding) as f:
                return f.read()
        except Exception:
            return default

    def write_text(
        self,
        name: str,
        data: str,
        encoding: str = "utf-8",
        atomic: bool = True,
        cache_ttl: Union[int, float] = 0,
    ) -> bool:
        """写文本。atomic=True 时使用临时文件原子替换，减少部分写入风险.

        Args:
            name: 文件名
            data: 文本数据
            encoding: 编码
            atomic: 是否原子写入
            cache_ttl: 缓存时间（秒），0表示不设置缓存过期
        """
        target = self.path(name)
        try:
            if not atomic:
                with open(target, "w", encoding=encoding) as f:
                    f.write(data)
            else:
                tmp_fd, tmp_path = tempfile.mkstemp(prefix="._tmp_", dir=str(self.root))
                try:
                    with os.fdopen(tmp_fd, "w", encoding=encoding) as f:
                        f.write(data)
                    shutil.move(tmp_path, target)
                finally:
                    if os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass

            # 设置缓存信息
            self._set_cache_info(name, cache_ttl)
            return True
        except Exception:
            return False

    # --- 简写别名 ---
    def read(
        self, name: str, default: Optional[str] = None, encoding: str = "utf-8"
    ) -> Optional[str]:
        return self.read_text(name, default=default, encoding=encoding)

    def write(
        self,
        name: str,
        data: str,
        encoding: str = "utf-8",
        atomic: bool = True,
        cache_ttl: Union[int, float] = 0,
    ) -> bool:
        return self.write_text(
            name, data, encoding=encoding, atomic=atomic, cache_ttl=cache_ttl
        )

    # --- JSON 读写 ---
    def set(
        self,
        name: str,
        obj: Any,
        encoding: str = "utf-8",
        ensure_ascii: bool = False,
        indent: int | None = None,
        cache_ttl: Union[int, float] = 0,
    ) -> bool:
        try:
            data = json.dumps(obj, ensure_ascii=ensure_ascii, indent=indent)
            return self.write_text(name, data, encoding=encoding, cache_ttl=cache_ttl)
        except Exception:
            return False

    def get(self, name: str, default: Any = None, encoding: str = "utf-8") -> Any:
        txt = self.read_text(name, default=None, encoding=encoding)
        if txt is None:
            return default
        try:
            return json.loads(txt)
        except Exception:
            return txt  # 回退为原始文本

    # --- 文件管理 ---
    def exists(self, name: str) -> bool:
        return self.path(name).exists()

    def delete(self, name: str) -> bool:
        try:
            self.path(name).unlink(missing_ok=True)
            # 同时清理缓存信息
            self._clean_cache_info(name)
            return True
        except Exception:
            return False

    def is_cache_expired(self, name: str) -> bool:
        """检查缓存是否已过期"""
        return not self._is_cache_valid(name)

    def clear_expired_cache(self) -> int:
        """清理所有过期的缓存文件，返回清理的文件数量"""
        cleared_count = 0
        try:
            for p in self.root.iterdir():
                if p.is_file() and not p.name.startswith("."):
                    if not self._is_cache_valid(p.name):
                        try:
                            p.unlink()
                            self._clean_cache_info(p.name)
                            cleared_count += 1
                        except Exception:
                            pass
        except Exception:
            pass
        return cleared_count

    def list(self) -> Iterable[str]:
        try:
            for p in self.root.iterdir():
                if p.is_file() and not p.name.startswith("."):  # 排除缓存信息文件
                    yield p.name
        except Exception:
            return []

    # --- 下标语法 ---
    def __getitem__(self, name: str) -> Optional[str]:
        return self.read(name)

    def __setitem__(self, name: str, value: Any) -> None:
        # 如果是基本类型/字典/列表 -> 走 JSON, 否则转字符串
        if isinstance(value, (dict, list, tuple, int, float, bool)):
            self.set(name, value)
        else:
            self.write(name, str(value))


# 默认实例供全局使用
storage = Storage()

if __name__ == "__main__":
    # 测试代码
    storage.write_text("test.txt", "Hello, World!")
    print(storage.read_text("test.txt"))
    storage.set("config.json", {"key": "value"})
    print(storage.get("config.json"))
    print(list(storage.list()))
    storage.delete("test.txt")
    print(storage.exists("test.txt"))  # 应该返回 False
