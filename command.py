import click
import importlib

from pathlib import Path
from functools import wraps



@click.group()
def cli():
    """
    命令行
    """
    pass


def _wrapper(func):
    @wraps(func)
    def inner(*args, **kwargs):
        return func(*args, **kwargs)

    return inner


for file in Path("./scripts").iterdir():
    if file.is_file() and file.name.endswith("py"):
        module_name = file.name.replace(".py", "")
        module = importlib.import_module(f"scripts.{module_name}")
        func = module.main
        if isinstance(func, click.Command) is False:
            command = cli.command(name=module_name)(_wrapper(func))


if __name__ == "__main__":
    cli()