from typing import List
from fastmcp import FastMCP


def load_mcp_server() -> List[FastMCP]:
    """加载MCP服务器"""
    servers = []
    
    try:
        from .browser import create_browser_server
        servers.append(create_browser_server())
        print("浏览器服务器加载成功")
    except ImportError as e:
        print(f"无法加载浏览器服务器: {e}")
    except Exception as e:
        print(f"创建浏览器服务器时出错: {e}")
    
    try:
        from .mediamz import create_mediamz_server  
        servers.append(create_mediamz_server())
        print("Mediamz服务器加载成功")
    except ImportError as e:
        print(f"无法加载Mediamz服务器: {e}")
    except Exception as e:
        print(f"创建Mediamz服务器时出错: {e}")
    
    try:
        from .server import create_server
        servers.append(create_server())
        print("通用服务器加载成功")
    except ImportError as e:
        print(f"无法加载通用服务器: {e}")
    except Exception as e:
        print(f"创建通用服务器时出错: {e}")
    
    try:
        from .knowledge_base import create_knowledge_base_server
        servers.append(create_knowledge_base_server())
        print("知识库服务器加载成功")
    except ImportError as e:
        print(f"无法加载知识库服务器: {e}")
    except Exception as e:
        print(f"创建知识库服务器时出错: {e}")
    
    try:
        from .intelligent_chat import create_intelligent_chat_server
        servers.append(create_intelligent_chat_server())
        print("智能对话服务器加载成功")
    except ImportError as e:
        print(f"无法加载智能对话服务器: {e}")
    except Exception as e:
        print(f"创建智能对话服务器时出错: {e}")
    
    print(f"总共加载了 {len(servers)} 个MCP服务器")
    return servers
