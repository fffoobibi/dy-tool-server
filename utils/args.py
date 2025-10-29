import sys
import shlex

import lazy_object_proxy
from argparse import ArgumentParser

from utils.env import T, env
from functools import cached_property
from typing import TYPE_CHECKING
from typing import Literal

from loguru import logger


class ArgsBuilder:
    """用于构建和解析命令行参数的类"""

    if TYPE_CHECKING:
        log_level: Literal[
            "TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"
        ] = "INFO"
        port: int = 5000
        install: bool = False
        expose: bool = False
        generate: bool = False
        mcp_only: bool = False
        mcp_port: int = 8000

    def __init__(self):
        self.parser = ArgumentParser(description="启动Waitress Web服务器")
        self.prefix = "APP_"
        self._env_fields = []
        self._pre_add_arguments()

    def _pre_add_arguments(self):
        """添加命令行参数"""
        self.parser.add_argument(
            "--log-level",
            type=str,
            default="INFO",
            choices=[
                "TRACE",
                "DEBUG",
                "INFO",
                "SUCCESS",
                "WARNING",
                "ERROR",
                "CRITICAL",
            ],
            help="设置日志级别 (默认: INFO)",
        )
        self.parser.add_argument(
            "--port", type=int, default=5000, help="服务器监听端口 (默认: 5000)"
        )
        self.parser.add_argument(
            "--install",
            action="store_true",
            help="安装依赖或配置项",
        )
        self.parser.add_argument(
            "--expose",
            action="store_true",
            help="暴露服务器端口: 默认frp实现",
        )
        self.parser.add_argument(
            "--generate",
            action="store_true",
            help="生成默认配置文件: .env",
        )
        self.parser.add_argument(
            "--mcp-only",
            action="store_true",
            help="仅启动MCP服务",
        )
        self.parser.add_argument(
            "--mcp-port", type=int, default=8000, help="MCP服务端口 (默认: 8000)"
        )

    def _parse(self):
        """解析命令行参数，支持从环境变量APP_COMMAND_ARGS加载默认参数"""
        # 从环境变量获取默认参数
        env_args_str = env.get("APP_COMMAND_ARGS", "", str)

        # 构建参数列表
        args_list = []

        # 如果环境变量中有参数，先添加环境变量参数
        if env_args_str.strip():
            try:
                # 使用shlex.split来正确处理引号和空格
                env_args = shlex.split(env_args_str)
                args_list.extend(env_args)
            except ValueError as e:
                logger.warning(f"警告: 解析环境变量APP_COMMAND_ARGS失败: {e}")

        # 然后添加命令行参数（命令行参数优先级更高）
        args_list.extend(sys.argv[1:])

        # 解析合并后的参数
        return self.parser.parse_args(args_list)

    @cached_property
    def _build(self):
        """构建并返回解析后的参数"""
        return self._parse()

    def __getattr__(self, name: str) -> any:
        """动态获取解析后的参数属性"""
        return getattr(self._build, name)

    def get_value(
        self, key: str, default=None, converter: T = str, lazy: bool = False
    ) -> T:
        """
        获取命令行参数的值

        Args:
            key: 参数名
            default: 默认值，如果参数不存在则返回此值
            converter: 类型转换函数，将字符串转换为需要的类型
            lazy: 是否返回延迟加载的代理对象

        Returns:
            转换后的参数值、默认值或其代理对象
        """
        env_key = f"{self.prefix}{key.lstrip('--').upper().replace('-', '_')}"
        if lazy:
            return env.get(env_key, default, converter, lazy=True)
        else:
            return env.get(env_key, default, converter)

    def arg(
        self,
        key: str,
        default=None,
        converter: T = str,
        desc: str = None,
        attach: bool = True,
    ) -> T:
        """
        获取命令行参数的值

        Args:
            key: 参数名
            default: 默认值，如果参数不存在则返回此值
            converter: 类型转换函数，将字符串转换为需要的类型
            lazy: 是否返回延迟加载的代理对象

        Returns:
            转换后的参数值、默认值或其代理对象
        """
        # 返回延迟加载的代理对象
        env_key = f"{self.prefix}{key.lstrip('--').upper().replace('-', '_')}"
        val = env.get(env_key, default, converter, lazy=True)
        if desc:
            desc = f"环境变量{env_key}中读取, {desc}, 默认值 {default}"
        if attach:
            self._env_fields.append(env_key)
            self.parser.add_argument(key, type=converter or str, default=val, help=desc)
        return val

    def arg_func(
        self,
        function: callable,
        key: str = None,
        default=None,
        desc: str = None,
        converter: T = str,
    ) -> T:
        """
        使用函数返回值作为参数的值, 适用于需要动态计算的参数
        """
        dft = lazy_object_proxy.Proxy(lambda: function())
        if key is not None:
            if desc:
                desc = f"参数: {key}, {desc}"
            else:
                desc = f"参数: {key}"
            env_key = f"{self.prefix}{key.lstrip('--').upper().replace('-', '_')}"
            self._env_fields.append(env_key)
            self.parser.add_argument(key, type=converter or str, default=dft, help=desc)
        return dft

    def desc(self):
        """
        返回参数解析器的描述信息
        """
        return self.parser.format_help()


args_builder = ArgsBuilder()
