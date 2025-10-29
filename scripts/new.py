import click
from loguru import logger
from utils import context_db
from models import get_models
from pathlib import Path


@click.option(
    "-n",
    "--name",
    help="新建的API接口名称",
    type=str,
)
@click.option("-d", "--delete", is_flag=True, help="删除已存在的API接口", default=False)
def main(name, delete):
    """
    新建api接口
    """
    if name:
        api_path = Path("api") / f"{name}.py"
        service_path = Path("services") / f"{name}.py"
        model_path = Path("models") / f"{name}.py"
        if delete:
            if api_path.exists():
                api_path.unlink()
            logger.success("接口 {} 删除成功", name)

            if service_path.exists():
                service_path.unlink()
            logger.success("服务 {} 删除成功", name)

            if model_path.exists():
                model_path.unlink()
            logger.success("模型 {} 删除成功", name)
            return

        template = f"""
from flask import Blueprint, request
from utils.response import success, fail, paginate
from utils import current_user, verify_auth
from services.{name} import {name}_service

bp = Blueprint("{name}", __name__)

@bp.before_request
def verify():
    verify_auth()
        """.strip()

        if api_path.exists():
            logger.warning("接口 {} 已存在", name)
        else:
            api_path.write_text(template)
            logger.success("接口 {} 创建成功", name)

        service_template = f"""
class {name.capitalize()}Service:
    def __init__(self):
        self.name = "{name}"


{name}_service = {name.capitalize()}Service()
        """.strip()

        if service_path.exists():
            logger.warning("服务 {} 已存在", name)
        else:
            service_path.write_text(service_template)
            logger.success("服务 {} 创建成功", name)

        model_template = f"""
from models import BaseModel

class {name.capitalize()}Model(BaseModel):

    class Meta:
        table_name = "tbl_{name.lower()}"
        """.strip()

        if model_path.exists():
            logger.warning("模型 {} 已存在", name)
        else:
            model_path.write_text(model_template)
            logger.success("模型 {} 创建成功", name)
