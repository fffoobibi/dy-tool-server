import os
from typing import Dict, List, Optional


class MCPConfig:
    """MCP 服务器配置"""
    
    # 服务器基本配置
    MCP_SERVER_NAME: str = os.getenv("MCP_SERVER_NAME", "dy-tool-server MCP Server")
    MCP_SERVER_VERSION: str = os.getenv("MCP_SERVER_VERSION", "1.0.0")
    
    # 服务器运行配置
    MCP_HOST: str = os.getenv("MCP_HOST", "localhost")
    MCP_PORT: int = int(os.getenv("MCP_PORT", "8000"))
    MCP_TRANSPORT: str = os.getenv("MCP_TRANSPORT", "sse")
    
    # OpenAPI 配置
    OPENAPI_PATH: str = os.getenv("OPENAPI_PATH", "./docker-compose/openapi.json")
    ENABLE_OPENAPI_INTEGRATION: bool = os.getenv("ENABLE_OPENAPI_INTEGRATION", "true").lower() == "true"
    
    # 服务器模块配置
    ENABLE_BROWSER_SERVER: bool = os.getenv("ENABLE_BROWSER_SERVER", "true").lower() == "true"
    ENABLE_MEDIAMZ_SERVER: bool = os.getenv("ENABLE_MEDIAMZ_SERVER", "true").lower() == "true"
    ENABLE_GENERAL_SERVER: bool = os.getenv("ENABLE_GENERAL_SERVER", "true").lower() == "true"
    ENABLE_KNOWLEDGE_BASE_SERVER: bool = os.getenv("ENABLE_KNOWLEDGE_BASE_SERVER", "true").lower() == "true"
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_DEBUG: bool = os.getenv("ENABLE_DEBUG", "false").lower() == "true"
    
    # 安全配置
    ENABLE_AUTH: bool = os.getenv("ENABLE_AUTH", "false").lower() == "true"
    JWT_SECRET_KEY: Optional[str] = os.getenv("JWT_SECRET_KEY")
    
    @classmethod
    def get_enabled_servers(cls) -> List[str]:
        """获取启用的服务器列表"""
        enabled = []
        if cls.ENABLE_BROWSER_SERVER:
            enabled.append("browser")
        if cls.ENABLE_MEDIAMZ_SERVER:
            enabled.append("mediamz")
        if cls.ENABLE_GENERAL_SERVER:
            enabled.append("general")
        if cls.ENABLE_KNOWLEDGE_BASE_SERVER:
            enabled.append("knowledge_base")
        return enabled
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """验证配置"""
        errors = []
        
        if cls.MCP_PORT <= 0 or cls.MCP_PORT > 65535:
            errors.append("MCP_PORT 必须在1-65535之间")
        
        if cls.MCP_TRANSPORT not in ["sse", "stdio"]:
            errors.append("MCP_TRANSPORT 必须是 'sse' 或 'stdio'")
        
        if cls.ENABLE_AUTH and not cls.JWT_SECRET_KEY:
            errors.append("启用认证时必须设置 JWT_SECRET_KEY")
        
        return errors
    
    @classmethod
    def get_server_info(cls) -> Dict:
        """获取服务器信息"""
        return {
            "name": cls.MCP_SERVER_NAME,
            "version": cls.MCP_SERVER_VERSION,
            "host": cls.MCP_HOST,
            "port": cls.MCP_PORT,
            "transport": cls.MCP_TRANSPORT,
            "enabled_servers": cls.get_enabled_servers(),
            "debug": cls.ENABLE_DEBUG,
            "auth_enabled": cls.ENABLE_AUTH
        }


# 创建配置实例
mcp_config = MCPConfig()
