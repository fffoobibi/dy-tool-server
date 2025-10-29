import click
from loguru import logger
from utils import context_db
from models import get_models


@click.option("-i", "--init", is_flag=True, help="数据库操作确认", default=False)
@click.option(
    "-c",
    "--create-env",
    type=click.Choice(["dev", "online"]),
    help="创建环境, dev: 开发环境, online: 线上环境",
    required=True,
)
@click.option(
    "-t",
    "--tables",
    multiple=True,
    help="创建表, 可选参数, 如果不指定则创建所有models表",
)
def main(init, create_env, tables):
    """
    数据库建表操作
    """
    if init:
        with context_db(env=create_env) as db:
            models = get_models()
            selected_models = []
            if tables:
                for table in tables:
                    model = next(
                        (m for m in models if m.__name__.lower() == table.lower()), None
                    )
                    if model:
                        selected_models.append(model)
                    else:
                        logger.error("未找到模型: {}", table)
            else:
                selected_models = models
            logger.info(
                "选中的模型: {} 已创建", [model.__name__ for model in selected_models]
            )
            db.create_tables(selected_models, safe=True)
