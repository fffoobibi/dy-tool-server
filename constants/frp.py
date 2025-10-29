import os
from pathlib import Path
from utils.args import args_builder


FRP_SERVER_ADDR = args_builder.arg(
    "--frp-server-addr",
    desc="设置FRP服务器地址",
)

FRP_SERVER_PORT = args_builder.arg(
    "--frp-server-port",
    converter=int,
    desc="设置FRP服务器端口",
)

FRP_AUTH_TOKEN = args_builder.arg(
    "--frp-auth-token",
    desc="设置FRP认证令牌",
)

FRP_ALLOWED_PORTS = args_builder.arg(
    "--frp-allowed-ports",
    default="10000-30000",
    desc="设置FRP允许的端口范围",
)

FRP_FRPC_PATH = args_builder.arg(
    "--frp-frpc-path",
    default="",
    desc="设置FRP客户端路径",
)