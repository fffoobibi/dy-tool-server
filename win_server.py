#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Waitress Web服务器启动脚本
用于Windows环境下启动Flask应用
"""
import os
import sys
import importlib

from loguru import logger
from waitress import serve

from app import create_app
from utils.packaging import is_packaged
from utils.network import get_local_ip
from dotenv import load_dotenv
from utils.args import args_builder
from pathlib import Path
from impls.tunnel.frp import FrpTunnel

from constants import load_args


if (Path(os.getcwd()) / ".env").exists():
    logger.success("加载环境变量文件: .env")
    load_dotenv(os.getcwd() + "/.env")

# 定义全局变量
current_dir = None


def configure_logging(log_level):
    """配置日志系统"""
    # 设置环境变量，控制全局日志级别
    os.environ["LOGURU_LEVEL"] = log_level
    os.environ["LOGURU_CONFIGURED"] = "1"  # 标记日志已配置，防止其他模块重新配置

    if is_packaged():
        # 打包环境下的日志配置
        logger.remove()  # 清除所有现有的日志处理器

        # 日志格式, 带有线程信息
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
            "<magenta>{thread.name: <10}</magenta> - <level>{message}</level>"
        )

        # 添加标准错误输出处理器
        logger.add(
            sys.stderr,
            level=log_level,
            format=log_format,
            colorize=True,
            backtrace=False,  # 关闭异常回溯
            diagnose=False,  # 关闭诊断信息
        )


def setup_path_environment():
    """设置路径环境"""
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 确保当前目录在sys.path中
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    # 设置打包环境
    try:
        from utils.packaging import setup_environment

        app_path = setup_environment()
        logger.info(f"应用路径: {app_path}")
        # 当前目录，是打包后的exe 文件运行所在目录
        work_dir = os.getcwd()
        logger.info("当前目录: {}", work_dir)
        return current_dir, app_path
    except ImportError:
        logger.warning("无法导入 utils.packaging 模块，可能影响打包后的运行")
        return current_dir, None


def discover_and_preload_modules(base_dir):
    """动态发现并预加载应用程序的关键模块

    Args:
        base_dir: 应用程序的根目录

    Returns:
        set: 已加载的模块集合
    """
    logger.debug("开始动态发现并预加载模块...")

    # 需要预加载的基础目录
    base_dirs = ["api", "models", "utils"]
    loaded_modules = set()

    # 1. 确保所有关键目录都在sys.path中
    for dir_name in base_dirs:
        dir_path = os.path.join(base_dir, dir_name)
        if (
            os.path.exists(dir_path)
            and os.path.isdir(dir_path)
            and dir_path not in sys.path
        ):
            sys.path.insert(0, dir_path)
            logger.debug(f"添加目录到sys.path: {dir_path}")

    # 2. 预加载基础模块
    base_modules = ["api", "models", "utils"]
    for module_name in base_modules:
        try:
            importlib.import_module(module_name)
            loaded_modules.add(module_name)
            logger.debug(f"已加载基础模块: {module_name}")
        except Exception as e:
            logger.error(f"加载基础模块 {module_name} 失败: {str(e)}")

    # 3. 动态发现并加载API模块
    api_dir = os.path.join(base_dir, "api")
    if os.path.exists(api_dir) and os.path.isdir(api_dir):
        logger.debug(f"扫描API目录: {api_dir}")
        for item in os.listdir(api_dir):
            if item.endswith(".py") and not item.startswith("__"):
                module_name = f"api.{item[:-3]}"
                try:
                    importlib.import_module(module_name)
                    loaded_modules.add(module_name)
                    logger.debug(f"已加载API模块: {module_name}")
                except Exception as e:
                    logger.error(f"加载API模块 {module_name} 失败: {str(e)}")

    # 4. 加载关键的模型模块
    try:
        for model_name in ["account", "browser"]:
            module_name = f"models.{model_name}"
            try:
                importlib.import_module(module_name)
                loaded_modules.add(module_name)
                logger.debug(f"已加载模型模块: {module_name}")
            except Exception as e:
                logger.error(f"加载模型模块 {module_name} 失败: {str(e)}")
    except Exception as e:
        logger.error(f"加载模型模块失败: {str(e)}")

    # 5. 显示加载结果
    logger.debug(f"成功加载了 {len(loaded_modules)} 个模块")
    api_modules = [
        m
        for m in sys.modules.keys()
        if m.startswith("api.") and not m.endswith("__init__")
    ]
    if api_modules:
        logger.info("已加载的API模块:")
        for m in sorted(api_modules):
            logger.info(f"  - {m}")
    else:
        logger.warning("未加载任何API模块!")

    return loaded_modules


def main():
    """主函数，初始化应用程序"""
    global current_dir

    # 配置日志系统
    configure_logging(args_builder._build.log_level)

    # 设置路径环境
    current_dir, app_path = setup_path_environment()

    # 执行模块发现和预加载
    discover_and_preload_modules(current_dir)

    # 导入并创建应用
    app = create_app()

    return app


def start_server(app):
    """
    启动Waitress服务器

    Args:
        app: Flask应用实例
    """
    port = args_builder.port
    log_level = args_builder.log_level
    
    if args_builder.mcp_only:
        from mcp_server import mcp_run
        mcp_run(args_builder.mcp_port)
        if args_builder.expose:
            frp = FrpTunnel("mcp", args_builder.mcp_port)
            frp.start()
        return

    if args_builder.generate:
        # 生成默认配置文件
        env_path = Path(os.getcwd()) / ".env"
        if env_path.exists():
            logger.warning(f".env 文件已存在: {env_path}")
        else:
            logger.info(f"正在生成默认配置文件: {env_path}")
            try:
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write(
                        """
APP_FRP_SERVER_ADDR = "frp.example.com"
APP_FRP_SERVER_PORT = 7000
APP_FRP_AUTH_TOKEN = "your_frp_user"
APP_FRP_ALLOWED_PORTS = "10000-30000"
APP_COMMAND_ARGS = "--log-level INFO --port 5000"
    """.strip()
                    )
                logger.success(f"成功生成默认配置文件: {env_path}")
            except Exception as e:
                logger.error(f"生成 .env 文件失败: {e}")
        return

    if args_builder.expose:
        frp = FrpTunnel("waitress", port)
        frp.start()

    logger.success(f"启动 Waitress 服务器，监听 0.0.0.0:{port}")
    logger.success(f"局域网访问地址: http://{get_local_ip()}:{port}")
    if args_builder.expose:
        logger.success(f"公网访问地址: http://{frp.frp_server_addr}:{frp.remote_port}")

    logger.info(f"日志级别设置为: {log_level}")
    
    serve(
        app,
        host="0.0.0.0",
        port=port,
        threads=os.cpu_count(),  # 工作线程数量 (推荐设置为 CPU 核心数)
        connection_limit=1000,  # 最大并发连接数
        channel_timeout=30,  # 连接超时时间（秒）
        cleanup_interval=30,  # 清理无效连接的间隔（秒）
        backlog=1024,  # 挂起连接队列的最大长度
        url_scheme="http",  # URL 协议方案 ('http' 或 'https')
    )


if __name__ == "__main__":
    load_args()
    app = main()
    start_server(app)