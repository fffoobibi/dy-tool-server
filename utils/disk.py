"""磁盘相关工具函数.

提供获取当前系统中可用空间( free space )最大的磁盘盘符的方法。
仅在 Windows 平台有效，其他平台返回 None。
"""

from __future__ import annotations

import os
import string
import shutil  # 新增
from typing import Optional
from . import local_storage

__all__ = ["get_max_drive_letter"]

# 进程级缓存
_persisted_drive_letter: Optional[str] = None
_default_cache_file = "max_drive_letter.cache"


def get_max_drive_letter(
    *, persist: bool = True, cache_file_name: str = _default_cache_file, force_refresh: bool = False
) -> Optional[str]:
    """获取当前系统中可用空间( free space )最大的磁盘盘符。

    说明:
        以前版本按字母序最大；现改为按当前可用空间最大的盘符。如果需要强制重新计算，设置 force_refresh=True。

    Args:
        persist: 是否启用持久化（内存 + 文件）。
        cache_file_name: 缓存文件名称（位于 local_storage 根目录下）。
        force_refresh: 忽略内存与文件缓存，强制重新探测（仍会覆盖缓存）。

    Returns:
        例如: "D:"；未找到或非 Windows 返回 None。
    """
    global _persisted_drive_letter
    storage = local_storage.storage

    if os.name != "nt":
        return None

    if persist and not force_refresh and _persisted_drive_letter is not None:
        return _persisted_drive_letter

    if (
        persist
        and not force_refresh
        and _persisted_drive_letter is None
        and storage.exists(cache_file_name)
    ):
        cached = storage.read(cache_file_name, default="") or ""
        cached = cached.strip()
        if cached:
            _persisted_drive_letter = cached
            return _persisted_drive_letter

    # 遍历所有存在的盘符，寻找可用空间最大的
    max_free = -1
    max_drive: Optional[str] = None
    for letter in string.ascii_uppercase:
        root_path = f"{letter}:\\"
        if not os.path.exists(root_path):
            continue
        try:
            total, used, free = shutil.disk_usage(root_path)
            if free > max_free:
                max_free = free
                max_drive = f"{letter}:"
        except Exception:
            continue

    if persist and max_drive:
        _persisted_drive_letter = max_drive
        storage.write(cache_file_name, max_drive)

    return max_drive
