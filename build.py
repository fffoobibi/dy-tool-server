"""
Flask应用打包脚本 - 使用PyInstaller将Flask应用打包为可执行文件
"""

import os
import shutil
import subprocess
import sys


# 清理之前的打包文件
def cleanup():
    dirs_to_clean = ["build", "dist"]
    files_to_clean = ["browser.spec"]

    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name)

    for file_name in files_to_clean:
        if os.path.exists(file_name):
            print(f"清理文件: {file_name}")
            os.remove(file_name)


def discover_modules():
    """自动发现项目中所有的Python模块"""
    discovered_modules = []
    module_dirs = ["api", "models", "utils", "constants", "services", "mcp_servers"]

    for module_dir in module_dirs:
        if not os.path.exists(module_dir):
            continue

        for root, _, files in os.walk(module_dir):
            package_path = root.replace(os.path.sep, ".")
            if "__pycache__" in package_path:
                continue

            # 添加包本身
            if package_path != "":
                discovered_modules.append(package_path)

            # 添加包中的模块
            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    module_name = os.path.splitext(file)[0]
                    full_module_path = (
                        f"{package_path}.{module_name}" if package_path else module_name
                    )
                    discovered_modules.append(full_module_path)

    return discovered_modules


def build_app():
    print("开始打包Flask应用...")

    # 确定当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 定义要包含的目录和文件
    include_dirs = [
        "templates",
        "static",
        "api",
        "models",
        "utils",
        "constants",
        "services",
    ]
    include_files = ["app.py", "command.py", "settings.py", "requirements.txt"]

    # 确保api目录中的所有文件都被包含
    api_files = []
    api_dir = os.path.join(current_dir, "api")
    if os.path.exists(api_dir):
        for file in os.listdir(api_dir):
            if file.endswith(".py"):
                api_files.append(os.path.join("api", file))

    # 构建--add-data参数
    add_data_params = []

    # 添加目录
    for dir_name in include_dirs:
        dir_path = os.path.join(current_dir, dir_name)
        if os.path.exists(dir_path):
            # 在Windows上使用分号分隔源和目标，使用绝对路径避免问题
            add_data_params.append(f"--add-data={dir_path};{dir_name}")
            print(f"添加目录: {dir_path} -> {dir_name}")

    # 添加文件
    for file_name in include_files:
        file_path = os.path.join(current_dir, file_name)
        if os.path.exists(file_path):
            # 文件添加到根目录
            add_data_params.append(f"--add-data={file_path};.")
            print(f"添加文件: {file_path} -> .")

    # 我们不再需要单独添加API文件，因为整个api目录已经被添加

    # 自动发现所有模块
    discovered_modules = discover_modules()
    print(f"自动发现的模块: {discovered_modules}")

    # 构建PyInstaller命令
    cmd = [
        "pyinstaller",
        "--name=browser",
        "--onefile",  # 单文件模式
        # '--noconsole',  # 取消注释以隐藏控制台窗口
        "--clean",
        # 基本必要的隐藏导入
        "--hidden-import=waitress",
        "--hidden-import=flask",
        "--hidden-import=peewee",
        "--hidden-import=fastmcp",
        "--hidden-import=fastmcp.server",
        "--hidden-import=fastmcp.server.auth",
        "--hidden-import=fastmcp.server.auth.providers",
        "--hidden-import=fastmcp.server.auth.providers.jwt",
        # 添加 fastmcp 相关的包数据
        "--collect-data=fastmcp",
        "--collect-submodules=fastmcp",
        # 复制 metadata
        "--copy-metadata=fastmcp",
    ]

    # 添加自动发现的模块
    for module in discovered_modules:
        cmd.append(f"--hidden-import={module}")

    # 添加数据目录参数
    cmd.extend(add_data_params)

    # 添加入口点
    cmd.append("win_serve.py")

    # 执行命令
    print(f"执行命令: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    print("打包完成！可执行文件在 dist 目录中。")


if __name__ == "__main__":
    # 清理之前的构建
    cleanup()

    # 执行构建
    build_app()