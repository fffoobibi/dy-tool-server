import platform
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from loguru import logger
import subprocess

def main():
    """
    更新 {{ project_name }}.ini
    """
    root = Path(__file__).parent.parent
    is_windows = platform.system().lower() == "windows"

    env = Environment(loader=FileSystemLoader(root))
    template = env.get_template(r"{{ project_name }}.ini")
    project_path = root.resolve().__str__().replace("\\", "/")
    project_name = root.name
    if is_windows is False:
        path = subprocess.check_output("which python", shell=True).decode().strip()
        venv_path = Path(path).parent.parent.resolve().__str__().replace("\\", "/")
    else:
        venv_path = str(root / "venv").replace("\\", "/")
    venv_bin = "Scripts" if is_windows else "bin"
    render_string = template.render(
        {
            "project_path": project_path,
            "project_name": project_name,
            "venv_path": venv_path,
            "venv_bin": venv_bin,
        }
    )
    (root / f"{project_name}.ini").write_text(render_string, encoding="utf-8")
    logger.success(f"更新 {project_name}.ini 成功")
