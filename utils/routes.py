import importlib
import json
import os
import sys
from flask import Flask, request
from loguru import logger
from utils.packaging import get_resource_path

__all__ = ("init_blueprints",)


def init_blueprints(app: Flask):
    """
    初始化蓝图，注册所有的 API 路由。
    使用 get_resource_path 动态发现和加载 API 模块。
    """
    # logger.debug("开始注册API蓝图...")

    registered_count = 0
    failed_count = 0

    # 1. 先通过文件系统发现所有可能的API模块
    api_path = get_resource_path("api")
    logger.debug(f"API模块路径: {api_path}")

    discovered_modules = []
    known_fallbacks = []  # 备用已知模块列表

    @app.before_request
    def log_request():
        if request.method == "GET":
            logger.info("GET {} {}", request.path, request.query_string)
        else:
            logger.info(
                "{} {} {}",
                request.method,
                request.path,
                ("\n" + json.dumps(request.json, ensure_ascii=False, indent=4)),
            )

    # 尝试从文件系统中发现模块
    try:
        if os.path.exists(api_path) and os.path.isdir(api_path):
            for item in os.listdir(api_path):
                item_path = os.path.join(api_path, item)
                if item.endswith(".py") and not item.startswith("__"):
                    module_name = f"api.{item[:-3]}"
                    discovered_modules.append(module_name)
                    logger.info(f"应用API模块: {module_name}")
    except Exception as e:
        logger.error(f"扫描API目录失败: {str(e)}")

    # 如果没有发现任何模块，使用已知的备用列表
    if not discovered_modules:
        logger.warning(f"未从文件系统发现任何API模块，使用备用列表: {known_fallbacks}")
        discovered_modules = known_fallbacks

    # 2. 动态导入并注册发现的模块
    for module_name in discovered_modules:
        try:
            # logger.info(f"尝试导入API模块: {module_name}")
            module = importlib.import_module(module_name)
            url_prefix = (
                getattr(module, "url_prefix", None) or module_name.split(".")[-1]
            )

            if hasattr(module, "bp"):
                # logger.info(f"注册蓝图: {module_name} 前缀: {url_prefix}")
                app.register_blueprint(module.bp, url_prefix=f"/{url_prefix}")
                registered_count += 1
            else:
                logger.warning(f"模块 {module_name} 没有 'bp' 属性，跳过。")
                failed_count += 1
        except Exception as e:
            logger.error(f"导入模块 {module_name} 失败: {str(e)}")
            failed_count += 1

    # 3. 如果通过动态导入没有成功注册任何模块，尝试使用sys.modules
    if registered_count == 0:
        logger.warning("没有成功注册任何API蓝图，尝试从sys.modules中查找...")

        # 从sys.modules中查找已经导入的API模块
        api_modules_in_sys = [
            m
            for m in sys.modules.keys()
            if m.startswith("api.") and not m.endswith("__init__")
        ]
        logger.info(f"在sys.modules中找到的API模块: {api_modules_in_sys}")

        # 如果sys.modules中没有找到API模块，使用备用列表
        modules_to_check = api_modules_in_sys if api_modules_in_sys else known_fallbacks

        for module_name in modules_to_check:
            try:
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                    url_prefix = (
                        getattr(module, "url_prefix", None)
                        or module_name.split(".")[-1]
                    )

                    if hasattr(module, "bp"):
                        logger.info(
                            f"从sys.modules注册蓝图: {module_name} 前缀: {url_prefix}"
                        )
                        app.register_blueprint(module.bp, url_prefix=f"/{url_prefix}")
                        registered_count += 1
            except Exception as e:
                logger.error(f"从sys.modules加载模块 {module_name} 失败: {str(e)}")

    # 4. 最后的结果日志
    if registered_count > 0:
        logger.info(f"API蓝图注册完成，成功: {registered_count}, 失败: {failed_count}")
    else:
        logger.error(f"所有API蓝图注册失败! 这将导致所有API端点返回404错误。")

        # 紧急措施: 动态创建一个测试API路由
        from flask import Blueprint, jsonify

        emergency_bp = Blueprint("emergency", __name__)

        @emergency_bp.route("/test")
        def emergency_test():
            return jsonify(
                {
                    "status": "ok",
                    "message": "Emergency API is working",
                    "note": "所有常规API模块加载失败，这是应急路由",
                }
            )

        @emergency_bp.route("/info")
        def system_info():
            import platform

            return jsonify(
                {
                    "status": "ok",
                    "python_version": sys.version,
                    "platform": platform.platform(),
                    "modules": list(sys.modules.keys()),
                    "api_path": api_path,
                    "discovered_modules": discovered_modules,
                    "working_directory": os.getcwd(),
                    "sys_path": sys.path,
                }
            )

        app.register_blueprint(emergency_bp, url_prefix="/emergency")
        logger.warning("已创建紧急API路由: /emergency/test 和 /emergency/info")
