#!/usr/bin/env python3
"""
Gunicorn 配置文件
用于生产环境部署 dy-tool-server
"""

import multiprocessing
import os
from pathlib import Path

# 获取项目根目录
BASE_DIR = Path(__file__).parent
if not (BASE_DIR / "logs").exists():
    (BASE_DIR / "logs").mkdir()

# 服务器配置
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 1000

# 性能优化
max_requests = 1000
max_requests_jitter = 50
preload_app = True
timeout = 30
keepalive = 5

# 日志配置
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
accesslog = str(BASE_DIR / "logs" / "access.log")
errorlog = str(BASE_DIR / "logs" / "error.log")
loglevel = "info"
capture_output = True

# 进程管理
daemon = False
pidfile = str(BASE_DIR / "dy-tool-server.pid")


# 钩子函数
def on_starting(server):
    """服务器启动钩子"""
    print(f"dy-tool-server starting on {bind}")


def when_ready(server):
    """服务器就绪钩子"""
    print(f"dy-tool-server ready. PID: {os.getpid()}")


def worker_int(worker):
    """工作进程中断钩子"""
    print(f"Worker {worker.pid} interrupted")


def post_fork(server, worker):
    """工作进程创建后钩子"""
    print(f"Worker {worker.pid} spawned")


# 安全配置
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190