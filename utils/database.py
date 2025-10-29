import importlib
import os
import settings
import typing as t
import threading
import time
import sqlite3
from pathlib import Path
from models import db, get_models
from playhouse.pool import (
    PooledSqliteDatabase,
    PooledMySQLDatabase,
    PooledPostgresqlDatabase
)
from contextlib import contextmanager
from utils.packaging import get_resource_path
from loguru import logger
from flask import Flask, request


from functools import lru_cache

__all__ = (
    "init_database",
    "context_db",
    "reset_db_connections",
    "ThreadSafeSQLiteDatabase",
)

# 线程本地存储，用于每个线程维护独立的数据库连接
_thread_local = threading.local()


class ThreadSafeSQLiteDatabase(PooledSqliteDatabase):
    """线程安全的SQLite数据库连接类"""

    def __init__(self, *args, **kwargs):
        # 确保SQLite以线程安全模式运行
        kwargs.setdefault("check_same_thread", False)
        kwargs.setdefault("timeout", 60)  # 60秒超时
        super().__init__(*args, **kwargs)
        self._local = threading.local()
        self._connection_lock = threading.RLock()

    def _connect(self):
        """创建线程安全的数据库连接"""
        with self._connection_lock:
            conn = super()._connect()
            # 设置SQLite的线程安全模式和优化参数
            conn.execute("PRAGMA journal_mode=WAL")  # WAL模式支持并发读写
            conn.execute("PRAGMA synchronous=NORMAL")  # 平衡安全性和性能
            conn.execute("PRAGMA cache_size=-32000")  # 32MB缓存
            conn.execute("PRAGMA temp_store=MEMORY")  # 临时数据存储在内存
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB内存映射
            conn.execute("PRAGMA busy_timeout=60000")  # 60秒忙等待超时
            return conn

    def get_conn(self):
        """获取当前线程的数据库连接"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = self._connect()
        return self._local.conn

    def close_conn(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except:
                pass
            finally:
                self._local.conn = None


@lru_cache(maxsize=1)
def _create_models():
    tables = db.get_tables()
    models = get_models()
    for m in models:
        if m._meta.table_name not in tables:
            logger.warning(f"创建表: {m._meta.table_name}")
            db.create_tables([m], safe=True)
        else:
            logger.debug(f"表已存在: {m._meta.table_name}")


def init_database(
    create_tables: bool = False,
    app: Flask = None,
    *,
    create_env: t.Literal["dev", "online"] | None = None,
):
    """
    数据库初始化
    root ad1123aa--=12323
    """
    global db
    model_path = Path(get_resource_path("models"))
    for file in model_path.glob("*.py"):
        if file.name == "__init__.py":
            continue
        else:
            logger.debug("import model: {}", file.stem)
            importlib.import_module(f"models.{file.stem}")

    if create_env is not None:
        if create_env == "dev":
            config = settings.DEV_SQL_CONFIG.copy()
            logger.debug("开发环境数据库初始化 ({})", settings.sql_type)
        elif create_env == "online":
            config = settings.SQL_CONFIG.copy()
            logger.debug("线上环境数据库初始化 ({})", settings.sql_type)
        else:
            raise ValueError(f"未知的环境: {create_env}")
    else:
        if settings.DEBUG is False:
            config = settings.SQL_CONFIG.copy()
            logger.debug("正式服数据库初始化 ({})", settings.sql_type)
        else:
            config = settings.DEV_SQL_CONFIG.copy()
            logger.debug("开发环境数据库初始化 ({})", settings.sql_type)

    if settings.sql_type == "sqlite":
        # 确保数据库目录存在
        db_path = config.get("database")
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.debug(f"创建SQLite数据库目录: {db_dir}")

        # 多线程安全配置
        config.update(
            {
                "check_same_thread": False,  # 允许多线程访问
                "timeout": 60,  # 数据库锁等待超时
            }
        )

        # 日志输出连接池配置
        max_conn = config.get("max_connections", settings.SQLITE_POOL_MAX_CONNECTIONS)
        stale_timeout = config.get("stale_timeout", settings.SQLITE_POOL_STALE_TIMEOUT)
        logger.debug(f"SQLite数据库路径: {db_path}")
        logger.debug(
            f"SQLite连接池配置: 最大连接数={max_conn}, 连接超时={stale_timeout}秒"
        )

    logger.info("数据库配置: {}", config)
    # 使用线程安全的数据库类
    if settings.sql_type == "sqlite":
        db.initialize(ThreadSafeSQLiteDatabase(**config))
    elif settings.sql_type == "mysql":
        db.initialize(PooledMySQLDatabase(**config))
    elif settings.sql_type == "postgresql":
        db.initialize(PooledPostgresqlDatabase(**config))

    if create_tables is True:
        _create_models()
        from models.account import User
        logger.debug("表创建完成, 检查root账号")
        if User.get_or_none(username="root") is None:
            logger.info("创建初始账号")
            account = "root"
            passwd = "root"
            User.create_user(username=account, password=passwd)
            logger.debug("账号: {}, 密码: {}", account, passwd)
        db.close()

    if app is not None:
        logger.debug("注册数据库连接到app")
        @app.before_request
        def _db_connect():
            if request.headers.get("x-use-db", True):
                # 使用线程安全的连接方式
                if db.is_closed():
                    try:
                        db.connect(reuse_if_open=True)
                        # 为每个请求设置SQLite优化参数
                        if settings.sql_type == "sqlite":
                            try:
                                db.execute_sql("PRAGMA synchronous=NORMAL")
                                db.execute_sql("PRAGMA journal_mode=WAL")
                                db.execute_sql("PRAGMA busy_timeout=30000")
                            except Exception as e:
                                logger.warning(f"设置SQLite优化参数失败: {e}")
                    except Exception as e:
                        logger.error(f"数据库连接失败: {e}")
                        # 如果连接失败，尝试关闭所有连接并重新连接
                        if settings.sql_type == "sqlite":
                            reset_db_connections()
                        try:
                            db.connect(reuse_if_open=True)
                        except Exception as retry_e:
                            logger.error(f"重试连接数据库失败: {retry_e}")
                            raise

        @app.teardown_request
        def _db_close(exc):
            if request.headers.get("x-use-db", True):
                if not db.is_closed():
                    try:
                        db.close()
                    except Exception as e:
                        logger.error(f"关闭数据库连接失败: {e}")
                        # 如果关闭失败，强制关闭所有连接
                        try:
                            if settings.sql_type == "sqlite":
                                reset_db_connections()
                        except:
                            pass


def reset_db_connections():
    """
    重置数据库连接池中的所有连接 - 线程安全版本
    当出现连接池耗尽或连接出错时调用此函数
    """
    try:
        logger.warning("重置数据库连接池...")

        # 如果使用的是我们自定义的线程安全数据库类
        if hasattr(db.obj, "close_conn"):
            db.obj.close_conn()

        # 关闭所有连接
        if hasattr(db, "close_all"):
            db.close_all()
        else:
            db.close()

        # 清理线程本地存储
        if hasattr(_thread_local, "conn"):
            delattr(_thread_local, "conn")

        logger.info("数据库连接池已重置")
        return True
    except Exception as e:
        logger.error(f"重置数据库连接池失败: {e}")
        return False


def execute_with_retry(operation, max_retries=3, delay=0.1):
    """
    带重试机制的数据库操作执行器

    Args:
        operation: 要执行的数据库操作函数
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            error_msg = str(e).lower()
            if "database is locked" in error_msg or "busy" in error_msg:
                if attempt < max_retries:
                    logger.warning(f"数据库忙碌，第{attempt+1}次重试 (错误: {e})")
                    time.sleep(delay * (2**attempt))  # 指数退避
                    continue
                else:
                    logger.error(f"数据库操作失败，已达到最大重试次数: {e}")
                    raise
            else:
                # 其他类型的错误直接抛出
                raise
        except Exception as e:
            logger.error(f"数据库操作发生未预期错误: {e}")
            raise


@contextmanager
def context_db(
    atomic: bool = True,
    *,
    env: t.Literal["dev", "online"] | None = None,
    retry_count: int = 3,
    timeout: float = 30.0,
):
    """
    线程安全的数据库上下文管理器

    Args:
        atomic: 是否使用事务
        env: 环境设置，可选 "dev" 或 "online"
        retry_count: 连接失败时的重试次数
        timeout: 操作超时时间（秒）
    """
    connection_established = False

    def db_operation():
        nonlocal connection_established

        # 初始化数据库
        init_database(create_env=env)

        # 尝试连接数据库
        if db.is_closed():
            db.connect(reuse_if_open=True)
            connection_established = True
            if settings.sql_type == "sqlite":
                # 设置连接级别的SQLite优化参数
                try:
                    db.execute_sql("PRAGMA busy_timeout=30000")  # 30秒忙等待
                    db.execute_sql("PRAGMA journal_mode=WAL")  # WAL模式
                    db.execute_sql("PRAGMA synchronous=NORMAL")  # 平衡模式
                except Exception as e:
                    logger.warning(f"设置SQLite参数失败: {e}")

        # 执行业务逻辑
        if atomic:
            with db.atomic():
                return db
        else:
            return db

    # 使用重试机制执行数据库操作
    for attempt in range(retry_count + 1):
        try:
            result = execute_with_retry(db_operation, max_retries=2)
            yield result
            break  # 成功完成后退出重试循环

        except Exception as e:
            error_msg = str(e).lower()

            # 检查是否是可重试的错误
            if any(
                keyword in error_msg
                for keyword in ["locked", "busy", "timeout", "connection"]
            ):
                if attempt < retry_count:
                    logger.warning(f"数据库操作失败，第{attempt+1}次重试: {e}")
                    reset_db_connections()  # 重置连接池
                    time.sleep(0.1 * (2**attempt))  # 指数退避
                    continue
                else:
                    logger.error(f"数据库操作失败，已达到最大重试次数: {e}")
                    raise
            else:
                # 不可重试的错误直接抛出
                logger.error(f"数据库操作错误: {e}")
                raise

        finally:
            # 确保在任何情况下都清理连接
            try:
                if connection_established and not db.is_closed():
                    db.close()
                    connection_established = False
            except Exception as cleanup_error:
                logger.error(f"清理数据库连接失败: {cleanup_error}")
                # 强制重置连接池
                try:
                    reset_db_connections()
                except:
                    pass
