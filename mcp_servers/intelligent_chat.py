"""
智能对话 MCP 服务器工具
"""
from fastmcp import FastMCP
from typing import List, Dict, Any, Optional
import json
from services.intelligent_chat import get_intelligent_chat_service
from services.intelligent_langchain_chat import get_langchain_chat_service
from loguru import logger


def create_intelligent_chat_server() -> FastMCP:
    """创建智能对话 MCP 服务器"""
    
    # 创建MCP服务器实例
    mcp = FastMCP("Intelligent Chat MCP Server")

    @mcp.tool()
    def rag_chat(
        message: str,
        user_id: str,
        workspace_slug: str = "default",
        platform: int = 0,
        use_knowledge: bool = True,
        max_results: int = 3
    ) -> Dict[str, Any]:
        """
        RAG增强的智能对话
        
        Args:
            message: 用户消息
            user_id: 用户ID
            workspace_slug: 知识库工作区标识
            platform: 平台类型 (0: douyin)
            use_knowledge: 是否使用知识库检索
            max_results: 最大检索结果数量
            
        Returns:
            Dict: 对话结果，包含回复内容、知识来源等
        """
        try:
            chat_service = get_intelligent_chat_service(workspace_slug)
            
            result = chat_service.chat_with_rag(
                user_message=message,
                send_user=user_id,
                platform=platform,
                use_knowledge=use_knowledge,
                max_results=max_results
            )
            
            return result
        except Exception as e:
            logger.error(f"RAG对话失败: {str(e)}")
            return {"error": f"RAG对话失败: {str(e)}"}

    @mcp.tool()
    def get_chat_history(
        user_id: str,
        workspace_slug: str = "default",
        platform: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取用户对话历史
        
        Args:
            user_id: 用户ID
            workspace_slug: 知识库工作区标识
            platform: 平台类型
            limit: 返回记录数量
            
        Returns:
            List[Dict]: 对话历史列表
        """
        try:
            chat_service = get_intelligent_chat_service(workspace_slug)
            
            history = chat_service.get_conversation_history(
                send_user=user_id,
                platform=platform,
                limit=limit
            )
            
            return history
        except Exception as e:
            logger.error(f"获取对话历史失败: {str(e)}")
            return [{"error": f"获取对话历史失败: {str(e)}"}]

    @mcp.tool()
    def clear_chat_history(
        user_id: str,
        workspace_slug: str = "default",
        platform: int = 0
    ) -> Dict[str, Any]:
        """
        清除用户对话历史
        
        Args:
            user_id: 用户ID
            workspace_slug: 知识库工作区标识
            platform: 平台类型
            
        Returns:
            Dict: 清除结果
        """
        try:
            chat_service = get_intelligent_chat_service(workspace_slug)
            
            success = chat_service.clear_conversation_history(
                send_user=user_id,
                platform=platform
            )
            
            return {
                "success": success,
                "message": "对话历史清除成功" if success else "对话历史清除失败"
            }
        except Exception as e:
            logger.error(f"清除对话历史失败: {str(e)}")
            return {"error": f"清除对话历史失败: {str(e)}"}

    @mcp.tool()
    def knowledge_search(
        query: str,
        workspace_slug: str = "default",
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        知识库检索测试
        
        Args:
            query: 检索查询
            workspace_slug: 知识库工作区标识
            max_results: 最大结果数量
            
        Returns:
            Dict: 检索结果
        """
        try:
            chat_service = get_intelligent_chat_service(workspace_slug)
            
            knowledge_texts, sources = chat_service._retrieve_knowledge(query, max_results)
            
            return {
                "query": query,
                "workspace_slug": workspace_slug,
                "knowledge_count": len(knowledge_texts),
                "knowledge_texts": knowledge_texts,
                "sources": sources
            }
        except Exception as e:
            logger.error(f"知识库检索失败: {str(e)}")
            return {"error": f"知识库检索失败: {str(e)}"}

    @mcp.tool()
    def batch_chat(
        messages: List[str],
        user_id: str,
        workspace_slug: str = "default",
        platform: int = 0,
        use_knowledge: bool = True
    ) -> List[Dict[str, Any]]:
        """
        批量对话处理
        
        Args:
            messages: 消息列表
            user_id: 用户ID
            workspace_slug: 知识库工作区标识
            platform: 平台类型
            use_knowledge: 是否使用知识库
            
        Returns:
            List[Dict]: 批量对话结果
        """
        try:
            chat_service = get_intelligent_chat_service(workspace_slug)
            results = []
            
            for i, message in enumerate(messages):
                try:
                    result = chat_service.chat_with_rag(
                        user_message=message,
                        send_user=user_id,
                        platform=platform,
                        use_knowledge=use_knowledge,
                        max_results=3
                    )
                    result["batch_index"] = i
                    results.append(result)
                except Exception as e:
                    results.append({
                        "batch_index": i,
                        "error": f"处理消息失败: {str(e)}",
                        "user_message": message
                    })
            
            return results
        except Exception as e:
            logger.error(f"批量对话失败: {str(e)}")
            return [{"error": f"批量对话失败: {str(e)}"}]

    @mcp.tool()
    def get_chat_stats(
        user_id: str,
        workspace_slug: str = "default",
        platform: int = 0
    ) -> Dict[str, Any]:
        """
        获取用户对话统计信息
        
        Args:
            user_id: 用户ID
            workspace_slug: 知识库工作区标识
            platform: 平台类型
            
        Returns:
            Dict: 统计信息
        """
        try:
            chat_service = get_intelligent_chat_service(workspace_slug)
            
            # 获取所有历史记录来计算统计
            history = chat_service.get_conversation_history(
                send_user=user_id,
                platform=platform,
                limit=1000  # 获取更多记录来统计
            )
            
            user_messages = [msg for msg in history if msg["role"] == "user"]
            assistant_messages = [msg for msg in history if msg["role"] == "assistant"]
            
            # 统计有知识来源的回复
            knowledge_enhanced_replies = sum(
                1 for msg in assistant_messages 
                if msg.get("sources") and len(msg["sources"]) > 0
            )
            
            return {
                "user_id": user_id,
                "workspace_slug": workspace_slug,
                "platform": platform,
                "total_conversations": len(history),
                "user_messages_count": len(user_messages),
                "assistant_messages_count": len(assistant_messages),
                "knowledge_enhanced_replies": knowledge_enhanced_replies,
                "knowledge_usage_rate": (
                    knowledge_enhanced_replies / len(assistant_messages) 
                    if assistant_messages else 0
                ),
                "latest_conversation_time": (
                    history[-1]["timestamp"] if history else None
                )
            }
        except Exception as e:
            logger.error(f"获取对话统计失败: {str(e)}")
            return {"error": f"获取对话统计失败: {str(e)}"}

    @mcp.tool()
    def intelligent_chat_health_check() -> Dict[str, Any]:
        """
        智能对话服务健康检查
        
        Returns:
            Dict: 健康状态信息
        """
        try:
            # 测试服务初始化
            chat_service = get_intelligent_chat_service()
            
            # 测试知识库连接
            from services.knowledge import get_knowledge_service
            knowledge_service = get_knowledge_service()
            workspaces = knowledge_service.list_workspaces()
            
            return {
                "status": "healthy",
                "service": "intelligent_chat",
                "knowledge_service": "connected",
                "available_workspaces": len(workspaces),
                "workspace_list": [ws.name for ws in workspaces],
                "message": "智能对话服务运行正常"
            }
        except Exception as e:
            logger.error(f"智能对话健康检查失败: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "智能对话服务异常"
            }

    # ==================== LangChain 智能对话工具 ====================
    
    @mcp.tool()
    def langchain_rag_chat(
        message: str,
        user_id: str,
        workspace_slug: str = "default",
        platform: int = 0,
        use_knowledge: bool = True,
        max_results: int = 3,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        基于 LangChain 的 RAG 增强智能对话
        
        Args:
            message: 用户消息
            user_id: 用户ID
            workspace_slug: 知识库工作区标识
            platform: 平台类型 (0: douyin)
            use_knowledge: 是否使用知识库检索
            max_results: 最大检索结果数量
            temperature: 模型温度 (0.0-2.0)
            
        Returns:
            Dict: 对话结果，包含回复内容、知识来源等
        """
        try:
            langchain_service = get_langchain_chat_service(workspace_slug)
            
            result = langchain_service.chat_with_rag(
                user_message=message,
                send_user=user_id,
                platform=platform,
                use_knowledge=use_knowledge,
                max_results=max_results,
                temperature=temperature
            )
            
            return result
            
        except Exception as e:
            logger.error(f"LangChain RAG 对话失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "user_message": message,
                "assistant_response": "抱歉，LangChain 服务暂时无法使用。"
            }

    @mcp.tool()
    def langchain_get_conversation_history(
        user_id: str,
        workspace_slug: str = "default",
        platform: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取 LangChain 用户对话历史
        
        Args:
            user_id: 用户ID
            workspace_slug: 知识库工作区标识
            platform: 平台类型
            limit: 获取记录数量限制
            
        Returns:
            Dict: 对话历史列表
        """
        try:
            langchain_service = get_langchain_chat_service(workspace_slug)
            
            history = langchain_service.get_conversation_history(
                send_user=user_id,
                platform=platform,
                limit=limit
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "platform": platform,
                "service_type": "langchain",
                "total_count": len(history),
                "conversations": history
            }
            
        except Exception as e:
            logger.error(f"获取 LangChain 对话历史失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "conversations": []
            }

    @mcp.tool()
    def langchain_clear_conversation_history(
        user_id: str,
        workspace_slug: str = "default",
        platform: int = 0
    ) -> Dict[str, Any]:
        """
        清除 LangChain 用户对话历史
        
        Args:
            user_id: 用户ID
            workspace_slug: 知识库工作区标识
            platform: 平台类型
            
        Returns:
            Dict: 清除结果
        """
        try:
            langchain_service = get_langchain_chat_service(workspace_slug)
            
            success_cleared = langchain_service.clear_conversation_history(
                send_user=user_id,
                platform=platform
            )
            
            return {
                "success": success_cleared,
                "message": "LangChain 对话历史清除成功" if success_cleared else "LangChain 对话历史清除失败",
                "user_id": user_id,
                "platform": platform
            }
            
        except Exception as e:
            logger.error(f"清除 LangChain 对话历史失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"清除失败: {str(e)}"
            }

    @mcp.tool()
    def langchain_update_llm_config(
        workspace_slug: str = "default",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新 LangChain LLM 配置
        
        Args:
            workspace_slug: 知识库工作区标识
            temperature: 模型温度
            max_tokens: 最大token数
            model_name: 模型名称
            
        Returns:
            Dict: 配置更新结果
        """
        try:
            langchain_service = get_langchain_chat_service(workspace_slug)
            
            # 构建更新配置
            config_updates = {}
            if temperature is not None:
                config_updates["temperature"] = temperature
            if max_tokens is not None:
                config_updates["max_tokens"] = max_tokens
            if model_name is not None:
                config_updates["model_name"] = model_name
            
            if not config_updates:
                return {
                    "success": False,
                    "error": "没有提供有效的配置参数"
                }
            
            # 更新配置
            langchain_service.update_llm_config(**config_updates)
            
            # 获取更新后的服务信息
            service_info = langchain_service.get_service_info()
            
            return {
                "success": True,
                "message": "LangChain 配置更新成功",
                "updated_config": config_updates,
                "current_service_info": service_info
            }
            
        except Exception as e:
            logger.error(f"更新 LangChain 配置失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"配置更新失败: {str(e)}"
            }

    @mcp.tool()
    def langchain_get_service_info(workspace_slug: str = "default") -> Dict[str, Any]:
        """
        获取 LangChain 服务信息和状态
        
        Args:
            workspace_slug: 知识库工作区标识
            
        Returns:
            Dict: 服务信息
        """
        try:
            langchain_service = get_langchain_chat_service(workspace_slug)
            service_info = langchain_service.get_service_info()
            
            # 测试知识库连接状态
            from services.knowledge import get_knowledge_service
            knowledge_service = get_knowledge_service()
            
            try:
                workspaces = knowledge_service.list_workspaces()
                knowledge_status = "connected"
                workspace_count = len(workspaces)
                workspace_names = [ws.name for ws in workspaces]
            except Exception as ke:
                knowledge_status = f"error: {str(ke)}"
                workspace_count = 0
                workspace_names = []
            
            from datetime import datetime
            
            return {
                "success": True,
                "service_info": service_info,
                "knowledge_service_status": knowledge_status,
                "available_workspaces_count": workspace_count,
                "available_workspaces": workspace_names,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"获取 LangChain 服务信息失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"获取服务信息失败: {str(e)}"
            }

    @mcp.tool()
    def compare_chat_services(
        message: str,
        user_id: str,
        workspace_slug: str = "default",
        platform: int = 0,
        use_knowledge: bool = True,
        max_results: int = 3
    ) -> Dict[str, Any]:
        """
        对比普通智能对话和 LangChain 智能对话的效果
        
        Args:
            message: 用户消息
            user_id: 用户ID
            workspace_slug: 知识库工作区标识
            platform: 平台类型
            use_knowledge: 是否使用知识库检索
            max_results: 最大检索结果数量
            
        Returns:
            Dict: 两种服务的对话结果对比
        """
        try:
            # 获取两种服务
            basic_service = get_intelligent_chat_service(workspace_slug)
            langchain_service = get_langchain_chat_service(workspace_slug)
            
            # 分别调用两种服务
            basic_result = basic_service.chat_with_rag(
                user_message=message,
                send_user=f"{user_id}_basic_test",
                platform=platform,
                use_knowledge=use_knowledge,
                max_results=max_results
            )
            
            langchain_result = langchain_service.chat_with_rag(
                user_message=message,
                send_user=f"{user_id}_langchain_test",
                platform=platform,
                use_knowledge=use_knowledge,
                max_results=max_results
            )
            
            return {
                "success": True,
                "message": "服务对比完成",
                "user_message": message,
                "basic_service_result": basic_result,
                "langchain_service_result": langchain_result,
                "comparison": {
                    "basic_success": basic_result.get("success", False),
                    "langchain_success": langchain_result.get("success", False),
                    "basic_knowledge_used": basic_result.get("knowledge_used", False),
                    "langchain_knowledge_used": langchain_result.get("knowledge_used", False),
                    "basic_sources_count": len(basic_result.get("sources", [])),
                    "langchain_sources_count": len(langchain_result.get("sources", []))
                }
            }
            
        except Exception as e:
            logger.error(f"服务对比失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"服务对比失败: {str(e)}"
            }

    return mcp
