"""
基于 LangChain 的智能对话服务 - 使用现有的向量检索接口
"""

import json
from typing import List, Dict, Any, Tuple
from datetime import datetime
from loguru import logger

# LangChain imports
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

# 本地服务imports
from models.chat_message import ChatMessage
from models.knowledge import VectorSearchRequest
from services.knowledge import get_knowledge_service
from utils.database import db

from services.llm import azure_llm


class LangChainChatService:
    """基于 LangChain 的智能对话服务"""

    def __init__(self, workspace_slug: str = None, default_workspace: str = "default"):
        self.knowledge_service = get_knowledge_service()
        self.workspace_slug = workspace_slug or default_workspace
        self.max_history_length = 10
        self.relevance_threshold = 0.6

        # 初始化 LangChain 组件
        self._setup_langchain_components()

    def _setup_langchain_components(self):
        """设置 LangChain 组件"""
        try:
            # 配置 ChatOpenAI 模型 (可以替换为其他模型)
            # 注意：这里使用的是通过 AnythingLLM 的 API，而不是直接调用 OpenAI
            self.llm = azure_llm

            # 创建 RAG 提示模板
            self.rag_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """你是一个智能助手，能够基于提供的知识库信息和对话历史来回答用户问题。

规则：
1. 优先使用知识库中的准确信息来回答问题
2. 结合对话历史提供连贯的回复  
3. 如果知识库中没有相关信息，基于常识礼貌回答
4. 保持回答简洁、准确、有帮助
5. 如果不确定答案，请诚实说明

知识库信息：
{context}""",
                    ),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{question}"),
                ]
            )

            # 创建输出解析器
            self.output_parser = StrOutputParser()

            logger.info("LangChain 组件初始化成功")

        except Exception as e:
            logger.error(f"LangChain 组件初始化失败: {str(e)}")
            # 使用备用的简单实现
            self.llm = None
            self.rag_prompt = None
            self.output_parser = None

    def chat_with_rag(
        self,
        user_message: str,
        send_user: str,
        recv_user: str,
        platform: int = 0,
        use_knowledge: bool = True,
        max_results: int = 3,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        使用 LangChain 进行 RAG 增强对话

        Args:
            user_message: 用户消息
            send_user: 发送者ID
            recv_user: 接收者ID
            platform: 平台类型
            use_knowledge: 是否使用知识库检索
            max_results: 最大检索结果数量
            temperature: 模型温度

        Returns:
            Dict: 对话结果
        """
        try:
            # 1. 保存用户消息
            user_chat = self._save_chat_message(
                content=user_message,
                send_user=send_user,
                recv_user=recv_user,
                platform=platform,
                message_type="user",
            )

            # 2. 获取对话历史
            chat_history = self._get_chat_history_messages(
                send_user, recv_user, platform
            )

            # 3. 知识库检索
            knowledge_context = ""
            sources = []
            if use_knowledge:
                knowledge_texts, sources = self._retrieve_knowledge(
                    user_message, max_results
                )
                knowledge_context = (
                    "\n".join(knowledge_texts)
                    if knowledge_texts
                    else "暂无相关知识库信息"
                )

            # 4. 使用 LangChain 生成回复
            if self.llm and self.rag_prompt:
                assistant_response = self._generate_langchain_response(
                    user_message, chat_history, knowledge_context, temperature
                )
            else:
                # 备用实现
                assistant_response = self._generate_fallback_response(
                    user_message, chat_history, knowledge_context
                )

            # 5. 保存助手回复
            assistant_chat = self._save_chat_message(
                content=assistant_response,
                send_user=recv_user,
                recv_user=send_user,
                platform=platform,
                message_type="assistant",
                sources=sources,
            )

            return {
                "success": True,
                "conversation_id": f"{send_user}_{recv_user}_{platform}",
                "user_message_id": user_chat.id,
                "assistant_message_id": assistant_chat.id,
                "user_message": user_message,
                "assistant_response": assistant_response,
                "sources": sources,
                "knowledge_used": len(sources) > 0,
                "langchain_used": self.llm is not None,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        except Exception as e:
            logger.error(f"LangChain 对话失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "user_message": user_message,
                "assistant_response": "抱歉，我现在无法回答您的问题，请稍后再试。",
            }

    def _generate_langchain_response(
        self,
        user_message: str,
        chat_history: List,
        knowledge_context: str,
        temperature: float = 0.7,
    ) -> str:
        """使用 LangChain 生成回复"""
        try:
            # 更新模型温度
            if hasattr(self.llm, "temperature"):
                self.llm.temperature = temperature

            # 构建 RAG 链
            rag_chain = (
                {
                    "context": RunnableLambda(lambda x: knowledge_context),
                    "chat_history": RunnableLambda(lambda x: chat_history),
                    "question": RunnablePassthrough(),
                }
                | self.rag_prompt
                | self.llm
                | self.output_parser
            )

            # 执行链并获取结果
            response = rag_chain.invoke(user_message)

            return response.strip() if response else "抱歉，我无法生成回复。"

        except Exception as e:
            logger.error(f"LangChain 生成回复失败: {str(e)}")
            # 回退到简单实现
            return self._generate_fallback_response(
                user_message, chat_history, knowledge_context
            )

    def _generate_fallback_response(
        self, user_message: str, chat_history: List, knowledge_context: str
    ) -> str:
        """备用响应生成（当 LangChain 不可用时）"""
        try:
            # 使用现有的知识库服务生成回复
            from models.knowledge import ChatRequest

            # 构建增强的提示
            enhanced_prompt = self._build_enhanced_prompt(
                user_message, chat_history, knowledge_context
            )

            chat_request = ChatRequest(
                message=enhanced_prompt, mode="chat", workspace_slug=self.workspace_slug
            )

            chat_response = self.knowledge_service.chat_with_workspace(chat_request)

            if chat_response and chat_response.text_response:
                return chat_response.text_response.strip()
            else:
                return "抱歉，我现在无法生成回复，请稍后再试。"

        except Exception as e:
            logger.error(f"备用响应生成失败: {str(e)}")
            return "抱歉，我现在无法回答您的问题，请稍后再试。"

    def _build_enhanced_prompt(
        self, user_message: str, chat_history: List, knowledge_context: str
    ) -> str:
        """构建增强提示（备用方法）"""
        prompt_parts = []

        # 系统设定
        prompt_parts.append(
            """你是一个智能助手，能够基于提供的知识库信息和对话历史来回答用户问题。请遵循以下原则：
1. 优先使用知识库中的准确信息来回答问题
2. 结合对话历史提供连贯的回复
3. 如果知识库中没有相关信息，基于常识礼貌回答
4. 保持回答简洁、准确、有帮助
5. 如果不确定答案，请诚实说明"""
        )

        # 知识库上下文
        if knowledge_context:
            prompt_parts.append(f"\n【知识库信息】:\n{knowledge_context}")

        # 对话历史
        if chat_history:
            prompt_parts.append("\n【对话历史】:")
            for msg in chat_history[-5:]:  # 最近5轮对话
                if isinstance(msg, HumanMessage):
                    prompt_parts.append(f"用户: {msg.content}")
                elif isinstance(msg, AIMessage):
                    prompt_parts.append(f"助手: {msg.content}")

        # 当前问题
        prompt_parts.append(f"\n【当前问题】:\n用户: {user_message}")
        prompt_parts.append("\n助手:")

        return "\n".join(prompt_parts)

    def _retrieve_knowledge(
        self, query: str, max_results: int = 3
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """从知识库检索相关信息"""
        try:
            search_request = VectorSearchRequest(
                query=query,
                workspace_slug=self.workspace_slug,
                top_k=max_results,
                threshold=self.relevance_threshold,
            )

            search_results = self.knowledge_service.vector_search(search_request)

            knowledge_texts = []
            sources = []

            for result in search_results:
                if result.score >= self.relevance_threshold:
                    knowledge_texts.append(result.text)
                    sources.append(
                        {
                            "title": result.metadata.get("title", "未知文档"),
                            "source": result.metadata.get("source", ""),
                            "score": result.score,
                            "chunk": (
                                result.text[:200] + "..."
                                if len(result.text) > 200
                                else result.text
                            ),
                        }
                    )

            logger.info(f"知识库检索完成，找到 {len(knowledge_texts)} 条相关信息")
            return knowledge_texts, sources

        except Exception as e:
            logger.warning(f"知识库检索失败: {str(e)}")
            return [], []

    def _get_chat_history_messages(
        self, send_user: str, recv_user: str, platform: int
    ) -> List:
        """获取对话历史并转换为 LangChain 消息格式"""
        try:
            history_query = (
                ChatMessage.select()
                .where(
                    (
                        (ChatMessage.send_user == send_user)
                        & (ChatMessage.recv_user == recv_user)
                    )
                    | (
                        (ChatMessage.send_user == recv_user)
                        & (ChatMessage.recv_user == send_user)
                    )
                )
                .where(ChatMessage.platform == platform)
                .order_by(ChatMessage.created_at.desc())
                .limit(self.max_history_length)
            )

            messages = []
            for msg in history_query:
                if msg.send_user == send_user:
                    messages.append(HumanMessage(content=msg.content or ""))
                else:
                    messages.append(AIMessage(content=msg.content or ""))

            # 按时间正序排列
            messages.reverse()
            return messages

        except Exception as e:
            logger.error(f"获取对话历史失败: {str(e)}")
            return []

    def _save_chat_message(
        self,
        content: str,
        send_user: str,
        recv_user: str,
        platform: int,
        message_type: str = "user",
        sources: List[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """保存聊天消息到数据库"""
        try:
            with db.atomic():
                chat_message = ChatMessage.create(
                    content=content,
                    send_user=send_user,
                    recv_user=recv_user,
                    platform=platform,
                )

                # 如果是助手消息且有知识来源
                if message_type == "assistant" and sources:
                    chat_message.translate_content = json.dumps(
                        sources, ensure_ascii=False
                    )
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
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取完整的对话历史"""
        try:
            history_query = (
                ChatMessage.select()
                .where(
                    (
                        (ChatMessage.send_user == send_user)
                        & (ChatMessage.recv_user == recv_user)
                    )
                    | (
                        (ChatMessage.send_user == recv_user)
                        & (ChatMessage.recv_user == send_user)
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
                    "timestamp": msg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "role": "user" if msg.send_user == send_user else "assistant",
                }

                # 添加知识来源信息
                if msg.translate_content:
                    try:
                        sources = json.loads(msg.translate_content)
                        message_data["sources"] = sources
                        message_data["langchain_enhanced"] = True
                    except:
                        pass

                conversations.append(message_data)

            conversations.reverse()
            return conversations

        except Exception as e:
            logger.error(f"获取对话历史失败: {str(e)}")
            return []

    def clear_conversation_history(
        self, send_user: str, recv_user: str = "assistant", platform: int = 0
    ) -> bool:
        """清除对话历史"""
        try:
            with db.atomic():
                deleted_count = (
                    ChatMessage.delete()
                    .where(
                        (
                            (ChatMessage.send_user == send_user)
                            & (ChatMessage.recv_user == recv_user)
                        )
                        | (
                            (ChatMessage.send_user == recv_user)
                            & (ChatMessage.recv_user == send_user)
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

    def update_llm_config(self, **kwargs):
        """更新 LLM 配置"""
        try:
            if self.llm:
                for key, value in kwargs.items():
                    if hasattr(self.llm, key):
                        setattr(self.llm, key, value)
                        logger.info(f"更新 LLM 配置: {key} = {value}")
        except Exception as e:
            logger.error(f"更新 LLM 配置失败: {str(e)}")

    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "service_type": "langchain_chat",
            "workspace_slug": self.workspace_slug,
            "langchain_available": self.llm is not None,
            "max_history_length": self.max_history_length,
            "relevance_threshold": self.relevance_threshold,
            "llm_model": (
                getattr(self.llm, "model_name", "unknown") if self.llm else None
            ),
            "llm_temperature": (
                getattr(self.llm, "temperature", None) if self.llm else None
            ),
        }


# 单例实例
_langchain_chat_service = None


def get_langchain_chat_service(workspace_slug: str = None) -> LangChainChatService:
    """获取 LangChain 智能对话服务实例"""
    global _langchain_chat_service
    if _langchain_chat_service is None or workspace_slug:
        _langchain_chat_service = LangChainChatService(workspace_slug)
    return _langchain_chat_service
