import os
from datetime import timedelta
from pathlib import Path
from typing import Literal
from os import getenv
from dotenv import load_dotenv

load_dotenv()

DEBUG = getenv("DEBUG", "true").lower() in ("true", "1", "t")
APP_ROOT = os.getcwd()  # 应用根目录
STATIC_FOLDER = "static"

# utils/jwt.py
JWT_SECRET_KEY = getenv("JWT_SECRET_KEY")
JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
JWT_TOKEN_LOCATION = ["headers", "cookies", "json", "query_string"]
SKIP_AUTH_TOKEN = getenv("SKIP_AUTH_TOKEN")  # 跳过验证的 Token

# utils/cache.py
CACHE_TYPE = "SimpleCache"  # 内存缓存
CACHE_DEFAULT_TIMEOUT = 300  # 默认超时时间（秒）

# utils/redis.py
REDIS_CONNECTION_POOL_COUNT = 8  # Redis 连接池大小
REDIS_CONFIG = {
    "host": getenv("REDIS_HOST"),
    "port": int(getenv("REDIS_PORT") or 6379),
    "db": int(getenv("REDIS_DB") or 0),
    "password": getenv("REDIS_PASSWORD"),
}

# OpenAI配置
OPENAI_API_KEY = getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")  # 支持自定义API地址
OPENAI_MODEL = getenv("OPENAI_MODEL", "gpt-3.5-turbo")  # 默认模型

# utils/upload.py
UPLOAD_FOLDER = os.path.abspath("./uploads")
UPLOAD_DOMAIN = getenv("UPLOAD_DOMAIN")  # 上传文件的域名或地址
if Path(UPLOAD_FOLDER).exists() is False:
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)


# utils/database.py
# SQLite配置
SQLITE_DB_PATH = os.path.join(APP_ROOT, "./data")
if not os.path.exists(SQLITE_DB_PATH):
    os.makedirs(SQLITE_DB_PATH, exist_ok=True)

# SQLite连接池配置 - 针对多线程优化
SQLITE_POOL_MAX_CONNECTIONS = 20  # 减少到20个连接，避免资源竞争
SQLITE_POOL_STALE_TIMEOUT = 300  # 减少到5分钟，更快回收连接
SQLITE_POOL_TIMEOUT = 30  # 减少到30秒，更快超时

# 数据库配置
sql_type: Literal["sqlite", "mysql", "postgresql"] = (
    getenv("SQL_TYPE", "sqlite").lower().strip()
)

if sql_type == "sqlite":
    SQL_CONFIG = {
        "database": os.path.join(SQLITE_DB_PATH, "app.db"),
        # 连接池配置
        "max_connections": SQLITE_POOL_MAX_CONNECTIONS,
        "stale_timeout": SQLITE_POOL_STALE_TIMEOUT,
        "timeout": SQLITE_POOL_TIMEOUT,
        # SQLite多线程安全配置
        "check_same_thread": False,  # 允许多线程访问
        # SQLite性能优化配置
        "pragmas": {
            "journal_mode": "WAL",  # WAL模式，支持并发读写
            "cache_size": -32768,  # 32MB缓存
            "foreign_keys": 1,  # 启用外键
            "synchronous": "NORMAL",  # 平衡安全性和性能
            "temp_store": "MEMORY",  # 临时表存储在内存
            "mmap_size": 268435456,  # 256MB内存映射
            "busy_timeout": 30000,  # 30秒忙等待超时
            "wal_autocheckpoint": 1000,  # WAL自动检查点
            "optimize": None,  # 启用查询优化
        },
    }

    DEV_SQL_CONFIG = {
        "database": os.path.join(SQLITE_DB_PATH, "dev_app.db"),
        # 连接池配置
        "max_connections": SQLITE_POOL_MAX_CONNECTIONS,
        "stale_timeout": SQLITE_POOL_STALE_TIMEOUT,
        "timeout": SQLITE_POOL_TIMEOUT,
        # SQLite多线程安全配置
        "check_same_thread": False,  # 允许多线程访问
        # SQLite性能优化配置
        "pragmas": {
            "journal_mode": "WAL",  # WAL模式，支持并发读写
            "cache_size": -32768,  # 32MB缓存
            "foreign_keys": 1,  # 启用外键
            "synchronous": "NORMAL",  # 平衡安全性和性能
            "temp_store": "MEMORY",  # 临时表存储在内存
            "mmap_size": 268435456,  # 256MB内存映射
            "busy_timeout": 30000,  # 30秒忙等待超时
            "wal_autocheckpoint": 1000,  # WAL自动检查点
            "optimize": None,  # 启用查询优化
        },
    }
elif sql_type == "mysql":
    SQL_CONFIG = {
        "host": getenv("DB_HOST"),
        "port": int(getenv("DB_PORT")),
        "user": getenv("DB_USER"),
        "password": getenv("DB_PASSWORD"),
        "database": getenv("DB_DATABASE"),
        "charset": "utf8mb4",
        "timeout": 30,
    }

    DEV_SQL_CONFIG = {
        "host": getenv("DB_HOST"),
        "port": int(getenv("DB_PORT")),
        "user": getenv("DB_USER"),
        "password": getenv("DB_PASSWORD"),
        "database": getenv("DB_DATABASE"),
        "charset": "utf8mb4",
        "timeout": 30,
    }

elif sql_type == "postgresql":
    SQL_CONFIG = {
        "host": getenv("DB_HOST"),
        "port": int(getenv("DB_PORT")),
        "user": getenv("DB_USER"),
        "password": getenv("DB_PASSWORD"),
        "database": getenv("DB_DATABASE"),
        "charset": "utf8mb4",
        "timeout": 30,
    }
    DEV_SQL_CONFIG = {
        "host": getenv("DB_HOST"),
        "port": int(getenv("DB_PORT")),
        "user": getenv("DB_USER"),
        "password": getenv("DB_PASSWORD"),
        "database": getenv("DB_DATABASE"),
        "charset": "utf8mb4",
        "timeout": 30,
    }