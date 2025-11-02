import os
from typing import Optional


class KnowledgeBaseConfig:
    """知识库配置类"""
    
    # AnythingLLM 服务配置
    ANYTHING_LLM_BASE_URL: str = os.getenv("ANYTHING_LLM_BASE_URL", "http://127.0.0.1:3001")
    ANYTHING_LLM_API_KEY: Optional[str] = os.getenv("ANYTHING_LLM_API_KEY")
    
    # 缓存配置
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1小时
    
    # 向量搜索配置
    DEFAULT_TOP_K: int = int(os.getenv("DEFAULT_TOP_K", "5"))
    DEFAULT_THRESHOLD: float = float(os.getenv("DEFAULT_THRESHOLD", "0.7"))
    
    # 聊天配置
    DEFAULT_CHAT_MODE: str = os.getenv("DEFAULT_CHAT_MODE", "chat")
    
    # 文档上传配置
    MAX_DOCUMENT_SIZE: int = int(os.getenv("MAX_DOCUMENT_SIZE", "10485760"))  # 10MB
    ALLOWED_FILE_TYPES: list = [
        "txt", "md", "pdf", "docx", "html", "htm", "json",
        "py", "js", "ts", "jsx", "tsx", "vue", "css", "scss"
    ]
    
    # 工作区配置
    DEFAULT_OPENAI_HISTORY: int = int(os.getenv("DEFAULT_OPENAI_HISTORY", "20"))
    DEFAULT_OPENAI_TEMP: Optional[float] = None
    
    # 超时配置
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "30"))
    
    @classmethod
    def get_base_url(cls) -> str:
        """获取基础URL"""
        return cls.ANYTHING_LLM_BASE_URL.rstrip('/')
    
    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """获取API密钥"""
        return cls.ANYTHING_LLM_API_KEY
    
    @classmethod
    def get_headers(cls) -> dict:
        """获取请求头"""
        headers = {}
        if cls.ANYTHING_LLM_API_KEY:
            headers["Authorization"] = f"Bearer {cls.ANYTHING_LLM_API_KEY}"
        return headers
    
    @classmethod
    def is_file_allowed(cls, filename: str) -> bool:
        """检查文件类型是否被允许"""
        if not filename:
            return False
        ext = filename.lower().split('.')[-1]
        return ext in cls.ALLOWED_FILE_TYPES
    
    @classmethod
    def validate_config(cls) -> list:
        """验证配置，返回错误列表"""
        errors = []
        
        if not cls.ANYTHING_LLM_BASE_URL:
            errors.append("ANYTHING_LLM_BASE_URL 不能为空")
        
        try:
            if cls.DEFAULT_TOP_K <= 0:
                errors.append("DEFAULT_TOP_K 必须大于0")
        except ValueError:
            errors.append("DEFAULT_TOP_K 必须是有效的整数")
        
        try:
            if not 0 <= cls.DEFAULT_THRESHOLD <= 1:
                errors.append("DEFAULT_THRESHOLD 必须在0到1之间")
        except ValueError:
            errors.append("DEFAULT_THRESHOLD 必须是有效的浮点数")
        
        try:
            if cls.MAX_DOCUMENT_SIZE <= 0:
                errors.append("MAX_DOCUMENT_SIZE 必须大于0")
        except ValueError:
            errors.append("MAX_DOCUMENT_SIZE 必须是有效的整数")
        
        return errors


# 创建配置实例
kb_config = KnowledgeBaseConfig()
