from flask import Blueprint, request
from flasgger import swag_from
from models.dantic.knowledge import (
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    DocumentUploadRequest,
    ChatRequest,
    VectorSearchRequest,
    EmbeddingUpdateRequest,
)
from services.knowledge import get_knowledge_service, KnowledgeBaseException
from utils.response import success, fail
from utils import current_user
from utils.jwt import verify_auth
from loguru import logger

bp = Blueprint("knowledge_base", __name__)


@bp.before_request
def verify():
    verify_auth()


# 工作区管理接口
@bp.get("/workspaces")
@swag_from(
    {
        "tags": ["知识库"],
        "summary": "获取所有工作区",
        "responses": {
            200: {
                "description": "成功",
                "schema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "integer"},
                        "message": {"type": "string"},
                        "data": {
                            "type": "object",
                            "properties": {
                                "workspaces": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                }
                            },
                        },
                    },
                },
            }
        },
    }
)
def list_workspaces():
    """获取所有工作区列表"""
    try:
        service = get_knowledge_service()
        workspaces = service.list_workspaces()
        return success(msg="success", resp={"workspaces": [ws.model_dump() for ws in workspaces]})
    except KnowledgeBaseException as e:
        return fail(msg=e.message, code=e.status_code)
    except Exception as e:
        return fail(msg=str(e))


@bp.get("/workspaces/<slug>")
@swag_from(
    {
        "tags": ["知识库"],
        "summary": "获取工作区详情",
        "parameters": [
            {
                "name": "slug",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "工作区唯一标识符",
            }
        ],
        "responses": {
            200: {"description": "成功"},
            404: {"description": "工作区不存在"},
        },
    }
)
def get_workspace(slug):
    """根据slug获取工作区详情"""
    try:
        service = get_knowledge_service()
        workspace = service.get_workspace(slug)
        if not workspace:
            return fail(msg="工作区不存在", code=404)
        return success(msg="success", resp={"workspace": workspace.model_dump()})
    except KnowledgeBaseException as e:
        return fail(msg=e.message, code=e.status_code)
    except Exception as e:
        return fail(msg=str(e))


@bp.post("/workspaces")
@swag_from(
    {
        "tags": ["知识库"],
        "summary": "创建工作区",
        "parameters": [
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string", "description": "工作区名称"},
                        "description": {"type": "string", "description": "工作区描述"},
                        "openai_temp": {
                            "type": "number",
                            "description": "OpenAI温度设置",
                        },
                        "openai_history": {
                            "type": "integer",
                            "description": "历史消息数量",
                        },
                        "openai_prompt": {
                            "type": "string",
                            "description": "系统提示词",
                        },
                    },
                },
            }
        ],
        "responses": {200: {"description": "创建成功"}},
    }
)
def create_workspace():
    """创建新的工作区"""
    try:
        data = request.get_json()
        request_obj = WorkspaceCreateRequest(**data)
        service = get_knowledge_service()
        workspace = service.create_workspace(request_obj)
        return success(msg="工作区创建成功", resp={"workspace": workspace.model_dump()})
    except KnowledgeBaseException as e:
        return fail(msg=e.message, code=e.status_code)
    except Exception as e:
        return fail(msg=str(e))


@bp.put("/workspaces/<slug>")
@swag_from(
    {
        "tags": ["知识库"],
        "summary": "更新工作区",
        "parameters": [
            {
                "name": "slug",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "工作区唯一标识符",
            },
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "工作区名称"},
                        "description": {"type": "string", "description": "工作区描述"},
                        "openai_temp": {
                            "type": "number",
                            "description": "OpenAI温度设置",
                        },
                        "openai_history": {
                            "type": "integer",
                            "description": "历史消息数量",
                        },
                        "openai_prompt": {
                            "type": "string",
                            "description": "系统提示词",
                        },
                    },
                },
            },
        ],
        "responses": {200: {"description": "更新成功"}},
    }
)
def update_workspace(slug):
    """更新工作区设置"""
    try:
        data = request.get_json()
        request_obj = WorkspaceUpdateRequest(**data)

        service = get_knowledge_service()
        workspace = service.update_workspace(slug, request_obj)
        return success(msg="工作区更新成功", resp={"workspace": workspace.model_dump()})
    except KnowledgeBaseException as e:
        return fail(msg=e.message, code=e.status_code)
    except Exception as e:
        return fail(msg=str(e))


@bp.delete("/workspaces/<slug>")
@swag_from(
    {
        "tags": ["知识库"],
        "summary": "删除工作区",
        "parameters": [
            {
                "name": "slug",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "工作区唯一标识符",
            }
        ],
        "responses": {200: {"description": "删除成功"}},
    }
)
def delete_workspace(slug):
    """删除工作区"""
    try:
        service = get_knowledge_service()
        success_result = service.delete_workspace(slug)
        if success_result:
            return success(msg="工作区删除成功")
        else:
            return fail(msg="删除工作区失败")
    except KnowledgeBaseException as e:
        return fail(msg=e.message, code=e.status_code)
    except Exception as e:
        return fail(msg=str(e))


# 文档管理接口
@bp.get("/documents")
@swag_from(
    {
        "tags": ["知识库"],
        "summary": "获取所有文档",
        "responses": {200: {"description": "成功"}},
    }
)
def list_documents():
    """获取所有文档列表"""
    try:
        service = get_knowledge_service()
        documents = service.list_documents()
        return success(msg="success", resp={"documents": [doc.model_dump() for doc in documents]})
    except KnowledgeBaseException as e:
        return fail(msg=e.message, code=e.status_code)
    except Exception as e:
        return fail(msg=str(e))


@bp.get("/documents/<doc_name>")
@swag_from(
    {
        "tags": ["知识库"],
        "summary": "获取文档详情",
        "parameters": [
            {
                "name": "doc_name",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "文档名称",
            }
        ],
        "responses": {200: {"description": "成功"}, 404: {"description": "文档不存在"}},
    }
)
def get_document(doc_name):
    """根据名称获取文档详情"""
    try:
        service = get_knowledge_service()
        document = service.get_document(doc_name)
        if not document:
            return fail(msg="文档不存在", code=404)
        return success(msg="success", resp={"document": document.model_dump()})
    except KnowledgeBaseException as e:
        return fail(msg=e.message, code=e.status_code)
    except Exception as e:
        return fail(msg=str(e))


@bp.post("/documents/upload-text")
@swag_from(
    {
        "tags": ["知识库"],
        "summary": "上传文本文档",
        "parameters": [
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "required": ["file_name", "content"],
                    "properties": {
                        "file_name": {"type": "string", "description": "文件名"},
                        "content": {"type": "string", "description": "文档内容"},
                        "metadata": {"type": "object", "description": "文档元数据"},
                        "add_to_workspaces": {
                            "type": "string",
                            "description": "添加到工作区(逗号分隔)",
                        },
                    },
                },
            }
        ],
        "responses": {200: {"description": "上传成功"}},
    }
)
def upload_text_document():
    """上传文本文档到知识库"""
    try:
        data = request.get_json()
        request_obj = DocumentUploadRequest(**data)

        service = get_knowledge_service()
        response = service.upload_document_text(request_obj)
        return success(
            msg="文档上传成功" if response.success else "文档上传失败",
            resp=response.model_dump()
        )
    except KnowledgeBaseException as e:
        return fail(msg=e.message, code=e.status_code)
    except Exception as e:
        return fail(msg=str(e))


@bp.post("/documents/upload-url")
@swag_from(
    {
        "tags": ["知识库"],
        "summary": "上传URL文档",
        "parameters": [
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "required": ["url"],
                    "properties": {
                        "url": {"type": "string", "description": "要上传的URL"},
                        "add_to_workspaces": {
                            "type": "string",
                            "description": "添加到工作区(逗号分隔)",
                        },
                    },
                },
            }
        ],
        "responses": {200: {"description": "上传成功"}},
    }
)
def upload_url_document():
    """通过URL上传文档到知识库"""
    try:
        data = request.get_json()
        url = data.get("url")
        add_to_workspaces = data.get("add_to_workspaces")

        service = get_knowledge_service()
        response = service.upload_document_url(url, add_to_workspaces)
        return success(
            msg="URL文档上传成功" if response.success else "URL文档上传失败",
            resp=response.model_dump()
        )
    except KnowledgeBaseException as e:
        return fail(msg=e.message, code=e.status_code)
    except Exception as e:
        return fail(msg=str(e))


# 聊天接口
@bp.post("/workspaces/<slug>/chat")
@swag_from(
    {
        "tags": ["知识库"],
        "summary": "与工作区聊天",
        "parameters": [
            {
                "name": "slug",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "工作区唯一标识符",
            },
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "required": ["message"],
                    "properties": {
                        "message": {"type": "string", "description": "用户消息"},
                        "mode": {
                            "type": "string",
                            "description": "对话模式(chat/query)",
                            "default": "chat",
                        },
                    },
                },
            },
        ],
        "responses": {200: {"description": "聊天成功"}},
    }
)
def chat_with_workspace(slug):
    """与指定工作区进行对话"""
    try:
        data = request.get_json()
        message = data.get("message")
        mode = data.get("mode", "chat")

        request_obj = ChatRequest(message=message, mode=mode, workspace_slug=slug)

        service = get_knowledge_service()
        response = service.chat_with_workspace(request_obj)
        return success(msg="success", resp=response.model_dump())
    except KnowledgeBaseException as e:
        return fail(msg=e.message, code=e.status_code)
    except Exception as e:
        return fail(msg=str(e))


# 向量搜索接口
@bp.post("/workspaces/<slug>/search")
@swag_from(
    {
        "tags": ["知识库"],
        "summary": "向量搜索",
        "parameters": [
            {
                "name": "slug",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "工作区唯一标识符",
            },
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "搜索查询"},
                        "top_k": {
                            "type": "integer",
                            "description": "返回结果数量",
                            "default": 5,
                        },
                        "threshold": {
                            "type": "number",
                            "description": "相似度阈值",
                            "default": 0.7,
                        },
                    },
                },
            },
        ],
        "responses": {200: {"description": "搜索成功"}},
    }
)
def vector_search(slug):
    """在工作区中进行向量相似度搜索"""
    try:
        data = request.get_json()
        query = data.get("query")
        top_k = data.get("top_k", 5)
        threshold = data.get("threshold", 0.7)

        request_obj = VectorSearchRequest(
            query=query, workspace_slug=slug, top_k=top_k, threshold=threshold
        )

        service = get_knowledge_service()
        results = service.vector_search(request_obj)
        return success(msg="success", resp={"results": [result.model_dump() for result in results]})
    except KnowledgeBaseException as e:
        return fail(msg=e.message, code=e.status_code)
    except Exception as e:
        return fail(msg=str(e))


# 嵌入管理接口
@bp.post("/workspaces/<slug>/embeddings")
@swag_from(
    {
        "tags": ["知识库"],
        "summary": "更新工作区嵌入",
        "parameters": [
            {
                "name": "slug",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "工作区唯一标识符",
            },
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "adds": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "要添加的文档路径列表",
                        },
                        "deletes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "要删除的文档路径列表",
                        },
                    },
                },
            },
        ],
        "responses": {200: {"description": "更新成功"}},
    }
)
def update_embeddings(slug):
    """更新工作区的文档嵌入"""
    try:
        data = request.get_json()
        request_obj = EmbeddingUpdateRequest(**data)

        service = get_knowledge_service()
        success_result = service.update_embeddings(slug, request_obj)
        if success_result:
            return success(msg="嵌入更新成功")
        else:
            return fail(msg="嵌入更新失败")
    except KnowledgeBaseException as e:
        return fail(msg=e.message, code=e.status_code)
    except Exception as e:
        return fail(msg=str(e))


# 健康检查接口
@bp.get("/health")
@swag_from(
    {
        "tags": ["知识库"],
        "summary": "知识库服务健康检查",
        "responses": {200: {"description": "服务正常"}},
    }
)
def health_check():
    """检查知识库服务的健康状态"""
    try:
        service = get_knowledge_service()
        workspaces = service.list_workspaces()
        return success(
            msg="知识库服务运行正常",
            resp={
                "status": "healthy",
                "workspace_count": len(workspaces),
                "service_url": service.base_url,
            }
        )
    except KnowledgeBaseException as e:
        return fail(msg=f"知识库服务异常: {e.message}")
    except Exception as e:
        return fail(msg=f"知识库服务异常: {str(e)}")
