#!/usr/bin/env python3
"""
Gunicorn 配置文件
用于生产环境部署 {{ project_name }}
"""

import multiprocessing
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
port = os.getenv("BASE_URL", "").strip("/").split(":")[-1]

# 获取项目根目录
BASE_DIR = Path(__file__).parent
if not (BASE_DIR / "logs").exists():
    (BASE_DIR / "logs").mkdir()

# 服务器配置
bind = f"0.0.0.0:{port}"
cpu_count = multiprocessing.cpu_count()
default_workers = cpu_count
workers = min(int(os.getenv("GUNICORN_WORKERS", default_workers)), cpu_count * 2)

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
pidfile = str(BASE_DIR / "{{ project_name }}.pid")


# 钩子函数
def on_starting(server):
    """服务器启动钩子 - 预加载 FastText 模型"""
    print(f"{{ project_name }} starting on {bind}")
    # 预加载 FastText 模型（在主进程中加载，fork 后所有 worker 共享）
    try:
        from services.language_detect import LanguageDetectService

        print("Preloading FastText model in master process...")
        model = LanguageDetectService.get_fasttext_model()
        if model:
            print("✅ FastText model preloaded successfully")
        else:
            print("⚠️ FastText model not loaded (file may not exist)")
    except Exception as e:
        print(f"⚠️ Failed to preload FastText model: {e}")


def when_ready(server):
    """服务器就绪钩子"""
    print(f"{{ project_name }} ready. PID: {os.getpid()}")


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
