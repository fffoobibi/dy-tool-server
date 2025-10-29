import time

from flask_caching import Cache
from loguru import logger
from flask import request
from flask_jwt_extended import current_user
import hashlib

__all__ = ("cache", "cache_call", "clear_cache_call", "user_fp_cache_key")
cache = Cache()


# 自定义缓存键函数
def user_fp_cache_key():
    json_data = request.get_json(silent=True)  # 获取请求体中的 JSON 数据
    __cache = json_data.get("__cache")
    user_id = current_user["id"]
    finger = current_user["fp"]
    if json_data and (__cache is not None):
        # 将 JSON 数据转换为字符串并生成哈希值作为缓存键
        json_str = str(f"{user_id}_{finger}_" + str(sorted(json_data.items())))  # 确保字典顺序一致
        return hashlib.md5(json_str.encode('utf-8')).hexdigest()

    return f"{user_id}_{finger}_" + str(time.time())


def cache_call(func, *args, **kwargs):
    try:
        vs = cache.get(func.__name__)
        if vs is not None:
            logger.info("get from cache  {}", func.__name__)
            return vs
        rs = func(*args, **kwargs)
        logger.info("cache func run {}: {}", func.__name__, rs)
        cache.set(func.__name__, rs)
        return rs
    except:
        logger.error("error in cache call")
        return False


def clear_cache_call(func):
    if isinstance(func, str):
        cache.delete(func)
    else:
        cache.delete(func.__name__)
