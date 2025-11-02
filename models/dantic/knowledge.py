from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_serializer
from enum import Enum


class DocumentType(str, Enum):
    """文档类型枚举"""
    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"


class WorkspaceStatus(str, Enum):
    """工作区状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROCESSING = "processing"
    ERROR = "error"


class Document(BaseModel):
    """文档模型"""
    id: Optional[str] = None
    name: str = Field(..., description="文档名称")
    type: DocumentType = Field(..., description="文档类型")
    size: int = Field(..., description="文档大小（字节）")
    content: Optional[str] = Field(None, description="文档内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="文档元数据")
    url: Optional[str] = Field(None, description="文档URL")
    title: str = Field(..., description="文档标题")
    doc_author: Optional[str] = Field(None, description="文档作者")
    description: Optional[str] = Field(None, description="文档描述")
    doc_source: Optional[str] = Field(None, description="文档来源")
    chunk_source: Optional[str] = Field(None, description="分块来源")
    published: Optional[str] = Field(None, description="发布时间")
    word_count: Optional[int] = Field(None, description="词数统计")
    token_count_estimate: Optional[int] = Field(None, description="Token数量估计")
    location: Optional[str] = Field(None, description="存储位置")
    cached: bool = Field(default=False, description="是否已缓存")
    pinned_workspaces: List[str] = Field(default_factory=list, description="固定到的工作区")
    watched: bool = Field(default=False, description="是否监控")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.strftime('%Y-%m-%d %H:%M:%S') if value else None


class Workspace(BaseModel):
    """工作区模型"""
    id: Optional[int] = None
    name: str = Field(..., description="工作区名称")
    slug: str = Field(..., description="工作区唯一标识")
    description: Optional[str] = Field(None, description="工作区描述")
    status: WorkspaceStatus = Field(default=WorkspaceStatus.ACTIVE, description="状态")
    settings: Dict[str, Any] = Field(default_factory=dict, description="工作区设置")
    openai_temp: Optional[float] = Field(None, description="OpenAI 温度设置")
    openai_history: Optional[int] = Field(20, description="历史消息数量")
    openai_prompt: Optional[str] = Field(None, description="系统提示词")
    documents: List[Document] = Field(default_factory=list, description="文档列表")
    threads: List[Dict[str, Any]] = Field(default_factory=list, description="对话线程")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    last_updated_at: Optional[datetime] = Field(None, description="最后更新时间")
    
    @field_serializer('created_at', 'last_updated_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.strftime('%Y-%m-%d %H:%M:%S') if value else None


class ChatMessage(BaseModel):
    """聊天消息模型"""
    id: Optional[str] = None
    role: str = Field(..., description="消息角色 (user/assistant)")
    content: str = Field(..., description="消息内容")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="引用来源")
    sent_at: Optional[int] = Field(None, description="发送时间戳")
    workspace_slug: str = Field(..., description="工作区标识")
    thread_slug: Optional[str] = Field(None, description="线程标识")


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户消息")
    mode: str = Field(default="chat", description="对话模式 (chat/query)")
    workspace_slug: str = Field(..., description="工作区标识")
    thread_slug: Optional[str] = Field(None, description="线程标识")


class ChatResponse(BaseModel):
    """聊天响应模型"""
    id: str = Field(..., description="响应ID")
    type: str = Field(..., description="响应类型")
    text_response: str = Field(..., description="文本响应")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="引用来源")
    close: bool = Field(default=True, description="是否结束")
    error: Optional[str] = Field(None, description="错误信息")


class VectorSearchRequest(BaseModel):
    """向量搜索请求模型"""
    query: str = Field(..., description="搜索查询")
    workspace_slug: str = Field(..., description="工作区标识")
    top_k: int = Field(default=5, description="返回结果数量")
    threshold: float = Field(default=0.7, description="相似度阈值")


class VectorSearchResult(BaseModel):
    """向量搜索结果模型"""
    id: str = Field(..., description="文档ID")
    text: str = Field(..., description="文档内容")
    metadata: Dict[str, Any] = Field(..., description="元数据")
    distance: float = Field(..., description="距离")
    score: float = Field(..., description="相似度分数")


class DocumentUploadRequest(BaseModel):
    """文档上传请求模型"""
    file_name: str = Field(..., description="文件名")
    content: Optional[str] = Field(None, description="文档内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    add_to_workspaces: Optional[str] = Field(None, description="添加到工作区（逗号分隔）")
    folder_name: Optional[str] = Field(None, description="文件夹名称")


class DocumentUploadResponse(BaseModel):
    """文档上传响应模型"""
    success: bool = Field(..., description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")
    documents: List[Document] = Field(default_factory=list, description="上传的文档")


class WorkspaceCreateRequest(BaseModel):
    """工作区创建请求模型"""
    name: str = Field(..., description="工作区名称")
    description: Optional[str] = Field(None, description="工作区描述")
    openai_temp: Optional[float] = Field(None, description="OpenAI 温度设置")
    openai_history: Optional[int] = Field(20, description="历史消息数量")
    openai_prompt: Optional[str] = Field(None, description="系统提示词")


class WorkspaceUpdateRequest(BaseModel):
    """工作区更新请求模型"""
    name: Optional[str] = Field(None, description="工作区名称")
    description: Optional[str] = Field(None, description="工作区描述")
    openai_temp: Optional[float] = Field(None, description="OpenAI 温度设置")
    openai_history: Optional[int] = Field(None, description="历史消息数量")
    openai_prompt: Optional[str] = Field(None, description="系统提示词")


class EmbeddingUpdateRequest(BaseModel):
    """嵌入更新请求模型"""
    adds: List[str] = Field(default_factory=list, description="要添加的文档")
    deletes: List[str] = Field(default_factory=list, description="要删除的文档")


class PinUpdateRequest(BaseModel):
    """固定更新请求模型"""
    document_path: str = Field(..., description="文档路径")
    pinned: bool = Field(..., description="是否固定")
