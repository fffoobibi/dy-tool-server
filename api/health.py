from flask import Blueprint
from utils.jwt import verify_auth
from utils.response import success

bp = Blueprint("health", __name__)


@bp.before_request
def verify():
    verify_auth()


@bp.get("/check")
def health_check():
    """health check endpoint
    ---
    tags:
      - health
    summary: 获取健康状态
    description: 获取服务的健康状态
    security:
      - Bearer: []
      - SkipAuth: []
    responses:
      200:
        description: 获取成功
    """
    return success("success", {"status": "ok"})
