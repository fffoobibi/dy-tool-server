# -*- coding: utf-8 -*-
from fastmcp import FastMCP
from typing import List, Dict, Any, Optional
from services.knowledge import get_knowledge_service, KnowledgeBaseException
from models.knowledge import (
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    DocumentUploadRequest,
    ChatRequest,
    VectorSearchRequest,
    EmbeddingUpdateRequest,
    PinUpdateRequest,
)


def create_knowledge_base_server() -> FastMCP:
    """创建知识库MCP服务器（同步版本）"""
    
    # 创建MCP服务器实例
    mcp = FastMCP("Knowledge Base MCP Server")
    
    # 获取知识库服务实例
    kb_service = get_knowledge_service()

    @mcp.tool()
    def list_workspaces() -> List[Dict[str, Any]]:
        """
        获取所有工作区列表
        
        Returns:
            List[Dict]: 工作区列表，包含每个工作区的详细信息
        """
        try:
            workspaces = kb_service.list_workspaces()
            return [ws.model_dump() for ws in workspaces]
        except KnowledgeBaseException as e:
            return [{"error": f"获取工作区列表失败: {e.message}"}]
        except Exception as e:
            return [{"error": f"获取工作区列表失败: {str(e)}"}]

    @mcp.tool()
    def get_workspace(slug: str) -> Dict[str, Any]:
        """
        根据slug获取工作区详情
        
        Args:
            slug: 工作区的唯一标识符
            
        Returns:
            Dict: 工作区详细信息，如果不存在则返回错误信息
        """
        try:
            workspace = kb_service.get_workspace(slug)
            if workspace:
                return workspace.model_dump()
            else:
                return {"error": "工作区不存在"}
        except KnowledgeBaseException as e:
            return {"error": f"获取工作区失败: {e.message}"}
        except Exception as e:
            return {"error": f"获取工作区失败: {str(e)}"}

    @mcp.tool()
    def create_workspace(
        name: str,
        description: Optional[str] = None,
        openai_temp: Optional[float] = None,
        openai_history: Optional[int] = 20,
        openai_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建新的工作区
        
        Args:
            name: 工作区名称
            description: 工作区描述（可选）
            openai_temp: OpenAI温度设置（可选）
            openai_history: 历史消息数量（可选，默认20）
            openai_prompt: 系统提示词（可选）
            
        Returns:
            Dict: 创建的工作区信息
        """
        try:
            request = WorkspaceCreateRequest(
                name=name,
                description=description,
                openai_temp=openai_temp,
                openai_history=openai_history,
                openai_prompt=openai_prompt
            )
            workspace = kb_service.create_workspace(request)
            return workspace.model_dump()
        except KnowledgeBaseException as e:
            return {"error": f"创建工作区失败: {e.message}"}
        except Exception as e:
            return {"error": f"创建工作区失败: {str(e)}"}

    @mcp.tool()
    def update_workspace(
        slug: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        openai_temp: Optional[float] = None,
        openai_history: Optional[int] = None,
        openai_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新工作区设置
        
        Args:
            slug: 工作区标识符
            name: 新的工作区名称（可选）
            description: 新的工作区描述（可选）
            openai_temp: 新的OpenAI温度设置（可选）
            openai_history: 新的历史消息数量（可选）
            openai_prompt: 新的系统提示词（可选）
            
        Returns:
            Dict: 更新后的工作区信息
        """
        try:
            request = WorkspaceUpdateRequest(
                name=name,
                description=description,
                openai_temp=openai_temp,
                openai_history=openai_history,
                openai_prompt=openai_prompt
            )
            workspace = kb_service.update_workspace(slug, request)
            return workspace.model_dump()
        except KnowledgeBaseException as e:
            return {"error": f"更新工作区失败: {e.message}"}
        except Exception as e:
            return {"error": f"更新工作区失败: {str(e)}"}

    @mcp.tool()
    def delete_workspace(slug: str) -> Dict[str, Any]:
        """
        删除工作区
        
        Args:
            slug: 要删除的工作区标识符
            
        Returns:
            Dict: 删除结果
        """
        try:
            success = kb_service.delete_workspace(slug)
            return {
                "success": success,
                "message": "工作区删除成功" if success else "工作区删除失败"
            }
        except KnowledgeBaseException as e:
            return {"error": f"删除工作区失败: {e.message}"}
        except Exception as e:
            return {"error": f"删除工作区失败: {str(e)}"}

    @mcp.tool()
    def list_documents() -> List[Dict[str, Any]]:
        """
        获取所有文档列表
        
        Returns:
            List[Dict]: 文档列表，包含每个文档的详细信息
        """
        try:
            documents = kb_service.list_documents()
            return [doc.model_dump() for doc in documents]
        except KnowledgeBaseException as e:
            return [{"error": f"获取文档列表失败: {e.message}"}]
        except Exception as e:
            return [{"error": f"获取文档列表失败: {str(e)}"}]

    @mcp.tool()
    def get_document(doc_name: str) -> Dict[str, Any]:
        """
        根据名称获取文档详情
        
        Args:
            doc_name: 文档名称
            
        Returns:
            Dict: 文档详细信息
        """
        try:
            document = kb_service.get_document(doc_name)
            if document:
                return document.model_dump()
            else:
                return {"error": "文档不存在"}
        except KnowledgeBaseException as e:
            return {"error": f"获取文档失败: {e.message}"}
        except Exception as e:
            return {"error": f"获取文档失败: {str(e)}"}

    @mcp.tool()
    def upload_text_document(
        file_name: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        add_to_workspaces: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        上传文本文档到知识库
        
        Args:
            file_name: 文件名
            content: 文档内容
            metadata: 文档元数据（可选）
            add_to_workspaces: 添加到工作区，逗号分隔（可选）
            
        Returns:
            Dict: 上传结果
        """
        try:
            request = DocumentUploadRequest(
                file_name=file_name,
                content=content,
                metadata=metadata or {},
                add_to_workspaces=add_to_workspaces
            )
            response = kb_service.upload_document_text(request)
            return response.model_dump()
        except KnowledgeBaseException as e:
            return {"error": f"上传文档失败: {e.message}"}
        except Exception as e:
            return {"error": f"上传文档失败: {str(e)}"}

    @mcp.tool()
    def upload_url_document(
        url: str,
        add_to_workspaces: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        通过URL上传文档到知识库
        
        Args:
            url: 要上传的URL
            add_to_workspaces: 添加到工作区，逗号分隔（可选）
            
        Returns:
            Dict: 上传结果
        """
        try:
            response = kb_service.upload_document_url(url, add_to_workspaces)
            return response.model_dump()
        except KnowledgeBaseException as e:
            return {"error": f"上传URL文档失败: {e.message}"}
        except Exception as e:
            return {"error": f"上传URL文档失败: {str(e)}"}

    @mcp.tool()
    def chat_with_workspace(
        workspace_slug: str,
        message: str,
        mode: str = "chat",
        thread_slug: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        与工作区进行对话
        
        Args:
            workspace_slug: 工作区标识符
            message: 用户消息
            mode: 对话模式，chat或query（默认chat）
            thread_slug: 线程标识符（可选）
            
        Returns:
            Dict: 聊天响应
        """
        try:
            request = ChatRequest(
                message=message,
                mode=mode,
                workspace_slug=workspace_slug,
                thread_slug=thread_slug
            )
            response = kb_service.chat_with_workspace(request)
            return response.model_dump()
        except KnowledgeBaseException as e:
            return {"error": f"聊天失败: {e.message}"}
        except Exception as e:
            return {"error": f"聊天失败: {str(e)}"}

    @mcp.tool()
    def vector_search(
        workspace_slug: str,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        在工作区中进行向量相似度搜索
        
        Args:
            workspace_slug: 工作区标识符
            query: 搜索查询
            top_k: 返回结果数量（默认5）
            threshold: 相似度阈值（默认0.7）
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        try:
            request = VectorSearchRequest(
                query=query,
                workspace_slug=workspace_slug,
                top_k=top_k,
                threshold=threshold
            )
            results = kb_service.vector_search(request)
            return [result.model_dump() for result in results]
        except KnowledgeBaseException as e:
            return [{"error": f"向量搜索失败: {e.message}"}]
        except Exception as e:
            return [{"error": f"向量搜索失败: {str(e)}"}]

    @mcp.tool()
    def update_embeddings(
        workspace_slug: str,
        adds: List[str] = None,
        deletes: List[str] = None
    ) -> Dict[str, Any]:
        """
        更新工作区的文档嵌入
        
        Args:
            workspace_slug: 工作区标识符
            adds: 要添加的文档路径列表（可选）
            deletes: 要删除的文档路径列表（可选）
            
        Returns:
            Dict: 更新结果
        """
        try:
            request = EmbeddingUpdateRequest(
                adds=adds or [],
                deletes=deletes or []
            )
            success = kb_service.update_embeddings(workspace_slug, request)
            return {
                "success": success,
                "message": "嵌入更新成功" if success else "嵌入更新失败"
            }
        except KnowledgeBaseException as e:
            return {"error": f"更新嵌入失败: {e.message}"}
        except Exception as e:
            return {"error": f"更新嵌入失败: {str(e)}"}

    @mcp.tool()
    def update_pin_status(
        workspace_slug: str,
        document_path: str,
        pinned: bool
    ) -> Dict[str, Any]:
        """
        更新文档在工作区中的固定状态
        
        Args:
            workspace_slug: 工作区标识符
            document_path: 文档路径
            pinned: 是否固定
            
        Returns:
            Dict: 更新结果
        """
        try:
            request = PinUpdateRequest(
                document_path=document_path,
                pinned=pinned
            )
            success = kb_service.update_pin_status(workspace_slug, request)
            return {
                "success": success,
                "message": "固定状态更新成功" if success else "固定状态更新失败"
            }
        except KnowledgeBaseException as e:
            return {"error": f"更新固定状态失败: {e.message}"}
        except Exception as e:
            return {"error": f"更新固定状态失败: {str(e)}"}

    @mcp.tool()
    def get_workspace_stats(workspace_slug: str) -> Dict[str, Any]:
        """
        获取工作区的统计信息
        
        Args:
            workspace_slug: 工作区标识符
            
        Returns:
            Dict: 工作区统计信息
        """
        try:
            workspace = kb_service.get_workspace(workspace_slug)
            if not workspace:
                return {"error": "工作区不存在"}
            
            stats = {
                "workspace_name": workspace.name,
                "document_count": len(workspace.documents),
                "thread_count": len(workspace.threads),
                "created_at": workspace.created_at.isoformat() if workspace.created_at else None,
                "last_updated_at": workspace.last_updated_at.isoformat() if workspace.last_updated_at else None,
                "settings": {
                    "openai_temp": workspace.openai_temp,
                    "openai_history": workspace.openai_history,
                    "has_custom_prompt": bool(workspace.openai_prompt)
                }
            }
            return stats
        except KnowledgeBaseException as e:
            return {"error": f"获取统计信息失败: {e.message}"}
        except Exception as e:
            return {"error": f"获取统计信息失败: {str(e)}"}

    @mcp.tool()
    def get_accepted_file_types() -> Dict[str, Any]:
        """
        获取系统支持的文件类型
        
        Returns:
            Dict: 支持的文件类型字典
        """
        try:
            file_types = kb_service.get_accepted_file_types()
            return {"types": file_types}
        except KnowledgeBaseException as e:
            return {"error": f"获取文件类型失败: {e.message}"}
        except Exception as e:
            return {"error": f"获取文件类型失败: {str(e)}"}

    @mcp.tool()
    def get_metadata_schema() -> Dict[str, Any]:
        """
        获取文档元数据的模式定义
        
        Returns:
            Dict: 元数据模式定义
        """
        try:
            schema = kb_service.get_metadata_schema()
            return {"schema": schema}
        except KnowledgeBaseException as e:
            return {"error": f"获取元数据模式失败: {e.message}"}
        except Exception as e:
            return {"error": f"获取元数据模式失败: {str(e)}"}

    @mcp.tool()
    def health_check() -> Dict[str, Any]:
        """
        检查知识库服务的健康状态
        
        Returns:
            Dict: 服务健康状态信息
        """
        try:
            workspaces = kb_service.list_workspaces()
            return {
                "status": "healthy",
                "workspace_count": len(workspaces),
                "service_url": kb_service.base_url,
                "message": "知识库服务运行正常"
            }
        except KnowledgeBaseException as e:
            return {
                "status": "unhealthy",
                "error": e.message,
                "service_url": kb_service.base_url,
                "message": "知识库服务异常"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "service_url": kb_service.base_url,
                "message": "知识库服务异常"
            }

    return mcp
