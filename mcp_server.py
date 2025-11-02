from mcp_servers import load_mcp_server
from fastmcp import FastMCP
from config import mcp_config, kb_config
import json
import os
import httpx


# 初始化 MCP 服务器
def initialize_mcp_server():
    """初始化 MCP 服务器"""
    # 移除异步客户端，使用同步版本

    # 验证配置
    config_errors = mcp_config.validate_config()
    if config_errors:
        print(f"MCP 配置错误: {config_errors}")

    kb_errors = kb_config.validate_config()
    if kb_errors:
        print(f"知识库配置错误: {kb_errors}")

    # AnythingLLM OpenAPI 集成
    openapi = json.load(open(mcp_config.OPENAPI_PATH, encoding="utf-8"))
    # 使用同步版本，不需要客户端
    mcp = FastMCP.from_openapi(
        openapi_spec=openapi, client=httpx.AsyncClient()
    )
    print("AnythingLLM OpenAPI 集成成功")
    # if mcp_config.ENABLE_OPENAPI_INTEGRATION:
    #     try:
    #         if os.path.exists(mcp_config.OPENAPI_PATH):
    #         OpenAPI 集成成功")
    #         else:
    #             print(f"OpenAPI 文件不存在: {mcp_config.OPENAPI_PATH}")
    #     except Exception as e:
    #         print(f"加载 OpenAPI 配置失败: {e}")

    # # 如果 OpenAPI 集成失败，创建基础服务器
    # if mcp is None:
    #     mcp = FastMCP(mcp_config.MCP_SERVER_NAME)
    #     print(f"创建基础 MCP 服务器: {mcp_config.MCP_SERVER_NAME}")

    # 加载自定义 MCP 服务器
    # try:
    #     servers = load_mcp_server()
    #     for server in servers:
    #         mcp.mount(server)
    #     print(f"自定义 MCP 服务器加载完成，共加载 {len(servers)} 个服务器")
    # except Exception as e:
    #     print(f"加载自定义 MCP 服务器失败: {e}")

    return mcp


# 初始化服务器
mcp = initialize_mcp_server()


def mcp_run(mcp_port: int = None):
    """Start Mcp Server"""
    port = mcp_port or mcp_config.MCP_PORT
    host = mcp_config.MCP_HOST
    transport = mcp_config.MCP_TRANSPORT

    print(f"启动 MCP 服务器:")
    print(f"  - 主机: {host}")
    print(f"  - 端口: {port}")
    print(f"  - 传输: {transport}")
    print(f"  - 启用的服务器: {mcp_config.get_enabled_servers()}")

    mcp.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    mcp_run()
