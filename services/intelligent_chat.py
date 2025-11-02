"""
智能对话服务 - 结合知识库RAG检索和LLM生成
"""
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

from models.chat_message import ChatMessage
from models.knowledge import ChatRequest, ChatResponse, VectorSearchRequest
from services.knowledge import get_knowledge_service, KnowledgeBaseException
from utils.database import db


class IntelligentChatService:
    """智能对话服务类"""
    
    def __init__(self, workspace_slug: str = None, default_workspace: str = "default"):
        self.knowledge_service = get_knowledge_service()
        self.workspace_slug = workspace_slug or default_workspace
        self.max_history_length = 10  # 最大历史对话长度
        self.relevance_threshold = 0.6  # 知识库相关性阈值
        
    def chat_with_rag(
        self,
        user_message: str,
        send_user: str,
        recv_user: str = "assistant",
        platform: int = 0,
        use_knowledge: bool = True,
        max_results: int = 3
    ) -> Dict[str, Any]:
        """
        RAG增强的智能对话
        
        Args:
            user_message: 用户消息
            send_user: 发送者ID
            recv_user: 接收者ID (默认assistant)
            platform: 平台类型 (0: douyin)
            use_knowledge: 是否使用知识库检索
            max_results: 最大检索结果数量
            
        Returns:
            Dict: 包含回复内容、知识来源、对话ID等信息
        """
        try:
            # 1. 保存用户消息到历史记录
            user_chat = self._save_chat_message(
                content=user_message,
                send_user=send_user,
                recv_user=recv_user,
                platform=platform,
                message_type="user"
            )
            
            # 2. 获取对话历史
            chat_history = self._get_chat_history(send_user, recv_user, platform)
            
            # 3. 知识库检索 (如果启用)
            knowledge_context = []
            sources = []
            if use_knowledge:
                knowledge_context, sources = self._retrieve_knowledge(
                    user_message, max_results
                )
            
            # 4. 构建增强prompt
            enhanced_prompt = self._build_enhanced_prompt(
                user_message, chat_history, knowledge_context
            )
            
            # 5. 调用LLM生成回复
            assistant_response = self._generate_llm_response(enhanced_prompt)
            
            # 6. 保存助手回复到历史记录
            assistant_chat = self._save_chat_message(
                content=assistant_response,
                send_user=recv_user,
                recv_user=send_user,
                platform=platform,
                message_type="assistant",
                sources=sources
            )
            
            return {
                "success": True,
                "conversation_id": f"{send_user}_{recv_user}_{platform}",
                "user_message_id": user_chat.id,
                "assistant_message_id": assistant_chat.id,
                "user_message": user_message,
                "assistant_response": assistant_response,
                "sources": sources,
                "knowledge_used": len(knowledge_context) > 0,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"智能对话失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "user_message": user_message,
                "assistant_response": "抱歉，我现在无法回答您的问题，请稍后再试。"
            }
    
    def _retrieve_knowledge(
        self, 
        query: str, 
        max_results: int = 3
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        从知识库检索相关信息
        
        Args:
            query: 查询文本
            max_results: 最大结果数量
            
        Returns:
            Tuple[List[str], List[Dict]]: (知识文本列表, 来源信息列表)
        """
        try:
            # 构建检索请求
            search_request = VectorSearchRequest(
                query=query,
                workspace_slug=self.workspace_slug,
                top_k=max_results,
                threshold=self.relevance_threshold
            )
            
            # 执行向量搜索
            search_results = self.knowledge_service.vector_search(search_request)
            
            knowledge_texts = []
            sources = []
            
            for result in search_results:
                if result.score >= self.relevance_threshold:
                    knowledge_texts.append(result.text)
                    sources.append({
                        "title": result.metadata.get("title", "未知文档"),
                        "source": result.metadata.get("source", ""),
                        "score": result.score,
                        "chunk": result.text[:200] + "..." if len(result.text) > 200 else result.text
                    })
            
            logger.info(f"知识库检索完成，找到 {len(knowledge_texts)} 条相关信息")
            return knowledge_texts, sources
            
        except KnowledgeBaseException as e:
            logger.warning(f"知识库检索失败: {e.message}")
            return [], []
        except Exception as e:
            logger.error(f"知识库检索异常: {str(e)}")
            return [], []
    
    def _get_chat_history(
        self, 
        send_user: str, 
        recv_user: str, 
        platform: int
    ) -> List[Dict[str, str]]:
        """
        获取对话历史记录
        
        Args:
            send_user: 发送者
            recv_user: 接收者
            platform: 平台
            
        Returns:
            List[Dict]: 历史对话列表
        """
        try:
            # 查询双向对话历史
            history_query = (
                ChatMessage
                .select()
                .where(
                    (
                        (ChatMessage.send_user == send_user) & 
                        (ChatMessage.recv_user == recv_user)
                    ) | (
                        (ChatMessage.send_user == recv_user) & 
                        (ChatMessage.recv_user == send_user)
                    )
                )
                .where(ChatMessage.platform == platform)
                .order_by(ChatMessage.created_at.desc())
                .limit(self.max_history_length)
            )
            
            history = []
            for msg in history_query:
                role = "user" if msg.send_user == send_user else "assistant"
                history.append({
                    "role": role,
                    "content": msg.content or "",
                    "timestamp": msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            # 按时间正序排列（最早的在前面）
            history.reverse()
            return history
            
        except Exception as e:
            logger.error(f"获取对话历史失败: {str(e)}")
            return []
    
    def _build_enhanced_prompt(
        self,
        user_message: str,
        chat_history: List[Dict[str, str]],
        knowledge_context: List[str]
    ) -> str:
        """
        构建增强的prompt
        
        Args:
            user_message: 用户消息
            chat_history: 对话历史
            knowledge_context: 知识库上下文
            
        Returns:
            str: 增强的prompt
        """
        prompt_parts = []
        
        # 系统角色设定
        prompt_parts.append("""你是一个智能助手，能够基于提供的知识库信息和对话历史来回答用户问题。请遵循以下原则：
1. 优先使用知识库中的准确信息来回答问题
2. 结合对话历史提供连贯的回复
3. 如果知识库中没有相关信息，基于常识礼貌回答
4. 保持回答简洁、准确、有帮助
5. 如果不确定答案，请诚实说明""")
        
        # 添加知识库上下文
        if knowledge_context:
            prompt_parts.append("\n【知识库信息】:")
            for i, knowledge in enumerate(knowledge_context, 1):
                prompt_parts.append(f"{i}. {knowledge}")
        
        # 添加对话历史
        if chat_history:
            prompt_parts.append("\n【对话历史】:")
            for msg in chat_history[-5:]:  # 只取最近5轮对话
                role_name = "用户" if msg["role"] == "user" else "助手"
                prompt_parts.append(f"{role_name}: {msg['content']}")
        
        # 添加当前用户问题
        prompt_parts.append(f"\n【当前问题】:\n用户: {user_message}")
        prompt_parts.append("\n助手:")
        
        return "\n".join(prompt_parts)
    
    def _generate_llm_response(self, prompt: str) -> str:
        """
        调用LLM生成回复
        
        Args:
            prompt: 增强的prompt
            
        Returns:
            str: LLM生成的回复
        """
        try:
            # 构建聊天请求
            chat_request = ChatRequest(
                message=prompt,
                mode="chat",
                workspace_slug=self.workspace_slug
            )
            
            # 调用知识库服务的聊天功能
            chat_response = self.knowledge_service.chat_with_workspace(chat_request)
            
            if chat_response and chat_response.text_response:
                return chat_response.text_response.strip()
            else:
                return "抱歉，我现在无法生成回复，请稍后再试。"
                
        except Exception as e:
            logger.error(f"LLM生成回复失败: {str(e)}")
            return "抱歉，我现在无法回答您的问题，请稍后再试。"
    
    def _save_chat_message(
        self,
        content: str,
        send_user: str,
        recv_user: str,
        platform: int,
        message_type: str = "user",
        sources: List[Dict[str, Any]] = None
    ) -> ChatMessage:
        """
        保存聊天消息到数据库
        
        Args:
            content: 消息内容
            send_user: 发送者
            recv_user: 接收者
            platform: 平台
            message_type: 消息类型 (user/assistant)
            sources: 知识来源 (仅对assistant消息)
            
        Returns:
            ChatMessage: 保存的消息对象
        """
        try:
            with db.atomic():
                chat_message = ChatMessage.create(
                    content=content,
                    send_user=send_user,
                    recv_user=recv_user,
                    platform=platform
                )
                
                # 如果是助手消息且有知识来源，可以考虑添加额外字段存储
                if message_type == "assistant" and sources:
                    # 可以在translate_content字段中存储JSON格式的sources信息
                    chat_message.translate_content = json.dumps(sources, ensure_ascii=False)
                    chat_message.save()
                
                return chat_message
                
        except Exception as e:
            logger.error(f"保存聊天消息失败: {str(e)}")
            raise
    
    def get_conversation_history(
        self,
        send_user: str,
        recv_user: str = "assistant",
        platform: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取完整的对话历史
        
        Args:
            send_user: 发送者
            recv_user: 接收者
            platform: 平台
            limit: 限制数量
            
        Returns:
            List[Dict]: 对话历史列表
        """
        try:
            history_query = (
                ChatMessage
                .select()
                .where(
                    (
                        (ChatMessage.send_user == send_user) & 
                        (ChatMessage.recv_user == recv_user)
                    ) | (
                        (ChatMessage.send_user == recv_user) & 
                        (ChatMessage.recv_user == send_user)
                    )
                )
                .where(ChatMessage.platform == platform)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            
            conversations = []
            for msg in history_query:
                message_data = {
                    "id": msg.id,
                    "content": msg.content,
                    "send_user": msg.send_user,
                    "recv_user": msg.recv_user,
                    "platform": msg.platform,
                    "timestamp": msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "role": "user" if msg.send_user == send_user else "assistant"
                }
                
                # 如果有知识来源信息
                if msg.translate_content:
                    try:
                        sources = json.loads(msg.translate_content)
                        message_data["sources"] = sources
                    except:
                        pass
                
                conversations.append(message_data)
            
            # 按时间正序排列
            conversations.reverse()
            return conversations
            
        except Exception as e:
            logger.error(f"获取对话历史失败: {str(e)}")
            return []
    
    def clear_conversation_history(
        self,
        send_user: str,
        recv_user: str = "assistant",
        platform: int = 0
    ) -> bool:
        """
        清除对话历史
        
        Args:
            send_user: 发送者
            recv_user: 接收者
            platform: 平台
            
        Returns:
            bool: 是否成功
        """
        try:
            with db.atomic():
                deleted_count = (
                    ChatMessage
                    .delete()
                    .where(
                        (
                            (ChatMessage.send_user == send_user) & 
                            (ChatMessage.recv_user == recv_user)
                        ) | (
                            (ChatMessage.send_user == recv_user) & 
                            (ChatMessage.recv_user == send_user)
                        )
                    )
                    .where(ChatMessage.platform == platform)
                    .execute()
                )
                
                logger.info(f"清除了 {deleted_count} 条对话记录")
                return True
                
        except Exception as e:
            logger.error(f"清除对话历史失败: {str(e)}")
            return False


# 单例实例
_intelligent_chat_service = None

def get_intelligent_chat_service(workspace_slug: str = None) -> IntelligentChatService:
    """获取智能对话服务实例"""
    global _intelligent_chat_service
    if _intelligent_chat_service is None or workspace_slug:
        _intelligent_chat_service = IntelligentChatService(workspace_slug)
    return _intelligent_chat_service
