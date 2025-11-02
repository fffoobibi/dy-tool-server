"""
智能对话API接口
"""
from flask import Blueprint, request
from flasgger import swag_from
from loguru import logger
from datetime import datetime

from services.intelligent_chat import get_intelligent_chat_service
from services.intelligent_langchain_chat import get_langchain_chat_service
from utils.response import success, fail
from utils.jwt import verify_auth

bp = Blueprint("intelligent_chat", __name__)


@bp.before_request
def verify():
    verify_auth()


@bp.post("/chat")
@swag_from({
    "tags": ["智能对话"],
    "summary": "RAG增强智能对话",
    "parameters": [{
        "name": "body",
        "in": "body",
        "required": True,
        "schema": {
            "type": "object",
            "required": ["message", "user_id"],
            "properties": {
                "message": {"type": "string", "description": "用户消息"},
                "user_id": {"type": "string", "description": "用户ID"},
                "workspace_slug": {"type": "string", "description": "知识库工作区", "default": "default"},
                "platform": {"type": "integer", "description": "平台类型", "default": 0},
                "use_knowledge": {"type": "boolean", "description": "是否使用知识库", "default": True},
                "max_results": {"type": "integer", "description": "最大检索结果数", "default": 3}
            }
        }
    }],
    "responses": {
        200: {"description": "对话成功"}
    }
})
def chat():
    """RAG增强的智能对话"""
    try:
        data = request.get_json()
        message = data.get("message")
        user_id = data.get("user_id")
        workspace_slug = data.get("workspace_slug", "default")
        platform = data.get("platform", 0)
        use_knowledge = data.get("use_knowledge", True)
        max_results = data.get("max_results", 3)
        
        if not message or not user_id:
            return fail(msg="消息内容和用户ID不能为空")
        
        # 获取智能对话服务实例
        chat_service = get_intelligent_chat_service(workspace_slug)
        
        # 执行RAG对话
        result = chat_service.chat_with_rag(
            user_message=message,
            send_user=user_id,
            platform=platform,
            use_knowledge=use_knowledge,
            max_results=max_results
        )
        
        if result.get("success"):
            return success(
                msg="对话成功",
                resp=result
            )
        else:
            return fail(
                msg=result.get("error", "对话失败"),
                resp=result
            )
            
    except Exception as e:
        logger.error(f"智能对话API异常: {str(e)}")
        return fail(msg=f"对话失败: {str(e)}")


@bp.get("/history/<user_id>")
@swag_from({
    "tags": ["智能对话"],
    "summary": "获取对话历史",
    "parameters": [
        {
            "name": "user_id",
            "in": "path",
            "type": "string",
            "required": True,
            "description": "用户ID"
        },
        {
            "name": "platform",
            "in": "query",
            "type": "integer",
            "required": False,
            "description": "平台类型",
            "default": 0
        },
        {
            "name": "limit",
            "in": "query",
            "type": "integer",
            "required": False,
            "description": "返回记录数量",
            "default": 50
        },
        {
            "name": "workspace_slug",
            "in": "query",
            "type": "string",
            "required": False,
            "description": "工作区标识",
            "default": "default"
        }
    ],
    "responses": {
        200: {"description": "获取成功"}
    }
})
def get_history(user_id):
    """获取用户对话历史"""
    try:
        platform = request.args.get("platform", 0, type=int)
        limit = request.args.get("limit", 50, type=int)
        workspace_slug = request.args.get("workspace_slug", "default")
        
        # 获取智能对话服务实例
        chat_service = get_intelligent_chat_service(workspace_slug)
        
        # 获取对话历史
        history = chat_service.get_conversation_history(
            send_user=user_id,
            platform=platform,
            limit=limit
        )
        
        return success(
            msg="获取对话历史成功",
            resp={
                "user_id": user_id,
                "platform": platform,
                "total_count": len(history),
                "conversations": history
            }
        )
        
    except Exception as e:
        logger.error(f"获取对话历史失败: {str(e)}")
        return fail(msg=f"获取对话历史失败: {str(e)}")


@bp.delete("/history/<user_id>")
@swag_from({
    "tags": ["智能对话"],
    "summary": "清除对话历史",
    "parameters": [
        {
            "name": "user_id",
            "in": "path",
            "type": "string",
            "required": True,
            "description": "用户ID"
        },
        {
            "name": "platform",
            "in": "query",
            "type": "integer",
            "required": False,
            "description": "平台类型",
            "default": 0
        },
        {
            "name": "workspace_slug",
            "in": "query",
            "type": "string",
            "required": False,
            "description": "工作区标识",
            "default": "default"
        }
    ],
    "responses": {
        200: {"description": "清除成功"}
    }
})
def clear_history(user_id):
    """清除用户对话历史"""
    try:
        platform = request.args.get("platform", 0, type=int)
        workspace_slug = request.args.get("workspace_slug", "default")
        
        # 获取智能对话服务实例
        chat_service = get_intelligent_chat_service(workspace_slug)
        
        # 清除对话历史
        success_cleared = chat_service.clear_conversation_history(
            send_user=user_id,
            platform=platform
        )
        
        if success_cleared:
            return success(msg="对话历史清除成功")
        else:
            return fail(msg="对话历史清除失败")
            
    except Exception as e:
        logger.error(f"清除对话历史失败: {str(e)}")
        return fail(msg=f"清除对话历史失败: {str(e)}")


@bp.get("/knowledge/search")
@swag_from({
    "tags": ["智能对话"],
    "summary": "知识库检索测试",
    "parameters": [
        {
            "name": "query",
            "in": "query",
            "type": "string",
            "required": True,
            "description": "检索查询"
        },
        {
            "name": "workspace_slug",
            "in": "query",
            "type": "string",
            "required": False,
            "description": "工作区标识",
            "default": "default"
        },
        {
            "name": "max_results",
            "in": "query",
            "type": "integer",
            "required": False,
            "description": "最大结果数",
            "default": 5
        }
    ],
    "responses": {
        200: {"description": "检索成功"}
    }
})
def knowledge_search():
    """测试知识库检索功能"""
    try:
        query = request.args.get("query")
        workspace_slug = request.args.get("workspace_slug", "default")
        max_results = request.args.get("max_results", 5, type=int)
        
        if not query:
            return fail(msg="查询内容不能为空")
        
        # 获取智能对话服务实例
        chat_service = get_intelligent_chat_service(workspace_slug)
        
        # 执行知识检索
        knowledge_texts, sources = chat_service._retrieve_knowledge(query, max_results)
        
        return success(
            msg="知识库检索成功",
            resp={
                "query": query,
                "workspace_slug": workspace_slug,
                "knowledge_count": len(knowledge_texts),
                "knowledge_texts": knowledge_texts,
                "sources": sources
            }
        )
        
    except Exception as e:
        logger.error(f"知识库检索失败: {str(e)}")
        return fail(msg=f"知识库检索失败: {str(e)}")


@bp.get("/health")
@swag_from({
    "tags": ["智能对话"],
    "summary": "智能对话服务健康检查",
    "responses": {
        200: {"description": "服务正常"}
    }
})
def health_check():
    """智能对话服务健康检查"""
    try:
        # 测试服务初始化
        chat_service = get_intelligent_chat_service()
        
        # 测试知识库连接
        from services.knowledge import get_knowledge_service
        knowledge_service = get_knowledge_service()
        workspaces = knowledge_service.list_workspaces()
        
        return success(
            msg="智能对话服务运行正常",
            resp={
                "status": "healthy",
                "service": "intelligent_chat",
                "knowledge_service": "connected",
                "available_workspaces": len(workspaces),
                "workspace_list": [ws.name for ws in workspaces]
            }
        )
        
    except Exception as e:
        logger.error(f"智能对话服务健康检查失败: {str(e)}")
        return fail(
            msg=f"智能对话服务异常: {str(e)}",
            resp={"status": "unhealthy"}
        )

# ==================== LangChain 智能对话接口 ====================

@bp.post("/langchain/chat")
@swag_from({
    "tags": ["LangChain智能对话"],
    "summary": "基于LangChain的RAG增强智能对话",
    "parameters": [{
        "name": "body",
        "in": "body",
        "required": True,
        "schema": {
            "type": "object",
            "required": ["message", "user_id"],
            "properties": {
                "message": {"type": "string", "description": "用户消息"},
                "user_id": {"type": "string", "description": "用户ID"},
                "workspace_slug": {"type": "string", "description": "知识库工作区", "default": "default"},
                "platform": {"type": "integer", "description": "平台类型", "default": 0},
                "use_knowledge": {"type": "boolean", "description": "是否使用知识库", "default": True},
                "max_results": {"type": "integer", "description": "最大检索结果数", "default": 3},
                "temperature": {"type": "number", "description": "模型温度", "default": 0.7, "minimum": 0, "maximum": 2}
            }
        }
    }],
    "responses": {
        200: {"description": "对话成功"}
    }
})
def langchain_chat():
    """基于LangChain的RAG增强智能对话"""
    try:
        data = request.get_json()
        message = data.get("message")
        user_id = data.get("user_id")
        workspace_slug = data.get("workspace_slug", "default")
        platform = data.get("platform", 0)
        use_knowledge = data.get("use_knowledge", True)
        max_results = data.get("max_results", 3)
        temperature = data.get("temperature", 0.7)
        
        if not message or not user_id:
            return fail(msg="消息内容和用户ID不能为空")
        
        # 获取LangChain智能对话服务实例
        langchain_service = get_langchain_chat_service(workspace_slug)
        
        # 执行LangChain RAG对话
        result = langchain_service.chat_with_rag(
            user_message=message,
            send_user=user_id,
            platform=platform,
            use_knowledge=use_knowledge,
            max_results=max_results,
            temperature=temperature
        )
        
        if result.get("success"):
            return success(
                msg="LangChain对话成功",
                resp=result
            )
        else:
            return fail(
                msg=result.get("error", "LangChain对话失败"),
                resp=result
            )
            
    except Exception as e:
        logger.error(f"LangChain智能对话API异常: {str(e)}")
        return fail(msg=f"LangChain对话失败: {str(e)}")


@bp.get("/langchain/history/<user_id>")
@swag_from({
    "tags": ["LangChain智能对话"],
    "summary": "获取LangChain对话历史",
    "parameters": [
        {
            "name": "user_id",
            "in": "path",
            "type": "string",
            "required": True,
            "description": "用户ID"
        },
        {
            "name": "platform",
            "in": "query",
            "type": "integer",
            "required": False,
            "description": "平台类型",
            "default": 0
        },
        {
            "name": "limit",
            "in": "query",
            "type": "integer",
            "required": False,
            "description": "返回记录数量",
            "default": 50
        },
        {
            "name": "workspace_slug",
            "in": "query",
            "type": "string",
            "required": False,
            "description": "工作区标识",
            "default": "default"
        }
    ],
    "responses": {
        200: {"description": "获取成功"}
    }
})
def langchain_get_history(user_id):
    """获取LangChain用户对话历史"""
    try:
        platform = request.args.get("platform", 0, type=int)
        limit = request.args.get("limit", 50, type=int)
        workspace_slug = request.args.get("workspace_slug", "default")
        
        # 获取LangChain智能对话服务实例
        langchain_service = get_langchain_chat_service(workspace_slug)
        
        # 获取对话历史
        history = langchain_service.get_conversation_history(
            send_user=user_id,
            platform=platform,
            limit=limit
        )
        
        return success(
            msg="获取LangChain对话历史成功",
            resp={
                "user_id": user_id,
                "platform": platform,
                "service_type": "langchain",
                "total_count": len(history),
                "conversations": history
            }
        )
        
    except Exception as e:
        logger.error(f"获取LangChain对话历史失败: {str(e)}")
        return fail(msg=f"获取LangChain对话历史失败: {str(e)}")


@bp.delete("/langchain/history/<user_id>")
@swag_from({
    "tags": ["LangChain智能对话"],
    "summary": "清除LangChain对话历史",
    "parameters": [
        {
            "name": "user_id",
            "in": "path",
            "type": "string",
            "required": True,
            "description": "用户ID"
        },
        {
            "name": "platform",
            "in": "query",
            "type": "integer",
            "required": False,
            "description": "平台类型",
            "default": 0
        },
        {
            "name": "workspace_slug",
            "in": "query",
            "type": "string",
            "required": False,
            "description": "工作区标识",
            "default": "default"
        }
    ],
    "responses": {
        200: {"description": "清除成功"}
    }
})
def langchain_clear_history(user_id):
    """清除LangChain用户对话历史"""
    try:
        platform = request.args.get("platform", 0, type=int)
        workspace_slug = request.args.get("workspace_slug", "default")
        
        # 获取LangChain智能对话服务实例
        langchain_service = get_langchain_chat_service(workspace_slug)
        
        # 清除对话历史
        success_cleared = langchain_service.clear_conversation_history(
            send_user=user_id,
            platform=platform
        )
        
        if success_cleared:
            return success(msg="LangChain对话历史清除成功")
        else:
            return fail(msg="LangChain对话历史清除失败")
            
    except Exception as e:
        logger.error(f"清除LangChain对话历史失败: {str(e)}")
        return fail(msg=f"清除LangChain对话历史失败: {str(e)}")


@bp.post("/langchain/config")
@swag_from({
    "tags": ["LangChain智能对话"],
    "summary": "更新LangChain LLM配置",
    "parameters": [{
        "name": "body",
        "in": "body",
        "required": True,
        "schema": {
            "type": "object",
            "properties": {
                "workspace_slug": {"type": "string", "description": "工作区标识", "default": "default"},
                "temperature": {"type": "number", "description": "模型温度", "minimum": 0, "maximum": 2},
                "max_tokens": {"type": "integer", "description": "最大token数", "minimum": 1, "maximum": 4000},
                "model_name": {"type": "string", "description": "模型名称"}
            }
        }
    }],
    "responses": {
        200: {"description": "配置更新成功"}
    }
})
def langchain_update_config():
    """更新LangChain LLM配置"""
    try:
        data = request.get_json()
        workspace_slug = data.get("workspace_slug", "default")
        
        # 获取LangChain智能对话服务实例
        langchain_service = get_langchain_chat_service(workspace_slug)
        
        # 提取配置参数
        config_updates = {}
        for key in ["temperature", "max_tokens", "model_name"]:
            if key in data:
                config_updates[key] = data[key]
        
        if not config_updates:
            return fail(msg="没有提供有效的配置参数")
        
        # 更新配置
        langchain_service.update_llm_config(**config_updates)
        
        # 获取更新后的配置信息
        service_info = langchain_service.get_service_info()
        
        return success(
            msg="LangChain配置更新成功",
            resp={
                "updated_config": config_updates,
                "current_service_info": service_info
            }
        )
        
    except Exception as e:
        logger.error(f"更新LangChain配置失败: {str(e)}")
        return fail(msg=f"更新LangChain配置失败: {str(e)}")


@bp.get("/langchain/info")
@swag_from({
    "tags": ["LangChain智能对话"],
    "summary": "获取LangChain服务信息",
    "parameters": [
        {
            "name": "workspace_slug",
            "in": "query",
            "type": "string",
            "required": False,
            "description": "工作区标识",
            "default": "default"
        }
    ],
    "responses": {
        200: {"description": "获取成功"}
    }
})
def langchain_service_info():
    """获取LangChain服务信息"""
    try:
        workspace_slug = request.args.get("workspace_slug", "default")
        
        # 获取LangChain智能对话服务实例
        langchain_service = get_langchain_chat_service(workspace_slug)
        
        # 获取服务信息
        service_info = langchain_service.get_service_info()
        
        # 测试知识库连接
        from services.knowledge import get_knowledge_service
        knowledge_service = get_knowledge_service()
        try:
            workspaces = knowledge_service.list_workspaces()
            knowledge_status = "connected"
            workspace_count = len(workspaces)
        except Exception as e:
            knowledge_status = f"error: {str(e)}"
            workspace_count = 0
        
        return success(
            msg="获取LangChain服务信息成功",
            resp={
                **service_info,
                "knowledge_service_status": knowledge_status,
                "available_workspaces_count": workspace_count,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
        
    except Exception as e:
        logger.error(f"获取LangChain服务信息失败: {str(e)}")
        return fail(msg=f"获取LangChain服务信息失败: {str(e)}")


@bp.get("/langchain/health")
@swag_from({
    "tags": ["LangChain智能对话"],
    "summary": "LangChain智能对话服务健康检查",
    "responses": {
        200: {"description": "服务正常"}
    }
})  
def langchain_health_check():
    """LangChain智能对话服务健康检查"""
    try:
        # 测试服务初始化
        langchain_service = get_langchain_chat_service()
        service_info = langchain_service.get_service_info()
        
        # 测试知识库连接
        from services.knowledge import get_knowledge_service
        knowledge_service = get_knowledge_service()
        workspaces = knowledge_service.list_workspaces()
        
        health_status = {
            "status": "healthy",
            "service": "langchain_intelligent_chat",
            "langchain_available": service_info.get("langchain_available", False),
            "knowledge_service": "connected",
            "available_workspaces": len(workspaces),
            "workspace_list": [ws.name for ws in workspaces],
            "service_info": service_info,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return success(
            msg="LangChain智能对话服务运行正常",
            resp=health_status
        )
        
    except Exception as e:
        logger.error(f"LangChain智能对话服务健康检查失败: {str(e)}")
        return fail(
            msg=f"LangChain智能对话服务异常: {str(e)}",
            resp={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
