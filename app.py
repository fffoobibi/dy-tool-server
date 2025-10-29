import os
import sys
import json
import settings
from flask import Flask, request
from flasgger import Swagger
from flask_cors import CORS
from utils import (
    init_jwt,
    init_upload,
    init_blueprints,
    cache,
    init_database,
)
from utils.response import fail
from werkzeug.routing.rules import Rule
from loguru import logger
from pathlib import Path

if sys.platform == "linux":
    from gevent import monkey

    monkey.patch_all()


def create_app():
    # 配置日志
    if not os.environ.get("LOGURU_CONFIGURED"):
        logger.remove()
        log_level = os.environ.get("LOGURU_LEVEL", "DEBUG")
        logger.add(sys.stderr, level=log_level, diagnose=False, backtrace=False)
        os.environ["LOGURU_CONFIGURED"] = "1"

    app = Flask(__name__)
    CORS(app)

    def swagger_rule_filter(rule: Rule):
        return True

    # 配置 Swagger 文档
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "title": "完整 API 文档",
                "rule_filter": swagger_rule_filter,
                "model_filter": lambda tag: True,  # 包含所有标签
            },
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs/",
    }

    swagger_template = json.loads(
        Path("./swagger_template.json").read_text(encoding="utf-8")
    )
    swagger = Swagger(app, config=swagger_config, template=swagger_template)

    app.config["UPLOAD_FOLDER"] = settings.UPLOAD_FOLDER
    app.config["JWT_SECRET_KEY"] = settings.JWT_SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = settings.JWT_ACCESS_TOKEN_EXPIRES
    app.config["JWT_TOKEN_LOCATION"] = settings.JWT_TOKEN_LOCATION

    # 配置缓存
    app.config["CACHE_TYPE"] = settings.CACHE_TYPE  # 内存缓存
    app.config["CACHE_DEFAULT_TIMEOUT"] = (
        settings.CACHE_DEFAULT_TIMEOUT
    )  # 默认超时时间（秒）

    # 配置jwt
    init_jwt(app)

    # 注册路由
    init_blueprints(app)

    # 注册数据库
    init_database(app=app)

    # 配置缓存
    cache.init_app(app)

    # 配置上传
    init_upload(app)

    @app.errorhandler(404)
    def page_not_found(error):
        return fail("API Endpoint Not Found", 404)

    @app.errorhandler(Exception)
    def handle_global_exception(err):
        logger.exception(
            "Global Error Occurred, IP {}",
            request.remote_addr,
        )
        return fail("Internal Server Error: " + str(err), 500)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(port=5000, debug=True, host="0.0.0.0")