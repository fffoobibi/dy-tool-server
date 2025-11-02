#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangChain 智能对话服务启动器
"""

import sys
import os
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """配置日志"""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

def test_langchain_service():
    """测试 LangChain 服务"""
    logger.info("🔍 测试 LangChain 智能对话服务...")
    
    try:
        from services.intelligent_langchain_chat import get_langchain_chat_service
        
        # 获取服务实例
        langchain_service = get_langchain_chat_service("default")
        logger.success("✅ LangChain 服务实例创建成功")
        
        # 获取服务信息
        service_info = langchain_service.get_service_info()
        logger.info(f"📊 服务信息:")
        for key, value in service_info.items():
            logger.info(f"  - {key}: {value}")
        
        # 测试简单对话
        logger.info("💬 测试 LangChain 对话功能...")
        test_result = langchain_service.chat_with_rag(
            user_message="你好，请简单介绍一下自己",
            send_user="test_user_langchain",
            platform=0,
            use_knowledge=False,  # 先不使用知识库测试
            max_results=3,
            temperature=0.7
        )
        
        if test_result.get("success"):
            logger.success("✅ LangChain 对话测试成功")
            logger.info(f"用户消息: {test_result.get('user_message', '')}")
            logger.info(f"助手回复: {test_result.get('assistant_response', '')}")
            logger.info(f"LangChain 使用: {test_result.get('langchain_used', False)}")
        else:
            logger.error(f"❌ LangChain 对话测试失败: {test_result.get('error', 'unknown')}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ LangChain 服务测试失败: {str(e)}")
        return False

def test_knowledge_service():
    """测试知识库服务"""
    logger.info("📚 测试知识库服务连接...")
    
    try:
        from services.knowledge import get_knowledge_service
        
        knowledge_service = get_knowledge_service()
        logger.success("✅ 知识库服务实例创建成功")
        
        # 测试获取工作区列表
        workspaces = knowledge_service.list_workspaces()
        logger.info(f"📁 可用工作区数量: {len(workspaces)}")
        
        for workspace in workspaces[:3]:  # 只显示前3个
            logger.info(f"  - {workspace.name} (slug: {workspace.slug})")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ 知识库服务测试失败: {str(e)}")
        return False

def test_database_connection():
    """测试数据库连接"""
    logger.info("🗄️ 测试数据库连接...")
    
    try:
        from utils.database import db
        from models.chat_message import ChatMessage
        
        # 测试数据库连接
        with db.atomic():
            # 获取最近的聊天记录数量
            count = ChatMessage.select().count()
            logger.success(f"✅ 数据库连接成功，共有 {count} 条聊天记录")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库连接测试失败: {str(e)}")
        return False

def run_interactive_chat():
    """运行交互式对话测试"""
    logger.info("🚀 启动 LangChain 智能对话交互式测试...")
    
    try:
        from services.intelligent_langchain_chat import get_langchain_chat_service
        
        langchain_service = get_langchain_chat_service("default")
        user_id = "interactive_test_user"
        
        logger.info("💡 输入 'quit' 或 'exit' 退出对话")
        logger.info("💡 输入 'clear' 清除对话历史")
        logger.info("💡 输入 'history' 查看对话历史")
        logger.info("=" * 50)
        
        while True:
            try:
                user_input = input("\n🧑 用户: ").strip()
                
                if user_input.lower() in ['quit', 'exit', '退出']:
                    logger.info("👋 退出交互式对话")
                    break
                    
                elif user_input.lower() in ['clear', '清除']:
                    success = langchain_service.clear_conversation_history(user_id, platform=0)
                    if success:
                        logger.success("✅ 对话历史已清除")
                    else:
                        logger.error("❌ 清除对话历史失败")
                    continue
                    
                elif user_input.lower() in ['history', '历史']:
                    history = langchain_service.get_conversation_history(user_id, platform=0, limit=10)
                    logger.info(f"📚 对话历史 (最近 {len(history)} 条):")
                    for i, conv in enumerate(history, 1):
                        role_emoji = "🧑" if conv["role"] == "user" else "🤖"
                        logger.info(f"  {i}. {role_emoji} {conv['content'][:100]}...")
                    continue
                    
                elif not user_input:
                    continue
                
                # 执行对话
                logger.info("🤖 助手正在思考...")
                result = langchain_service.chat_with_rag(
                    user_message=user_input,
                    send_user=user_id,
                    platform=0,
                    use_knowledge=True,
                    max_results=3,
                    temperature=0.7
                )
                
                if result.get("success"):
                    response = result.get("assistant_response", "")
                    sources = result.get("sources", [])
                    
                    print(f"\n🤖 助手: {response}\n")
                    
                    if sources:
                        logger.info(f"📚 知识来源 ({len(sources)} 条):")
                        for i, source in enumerate(sources[:2], 1):  # 只显示前2个来源
                            logger.info(f"  {i}. {source.get('title', 'Unknown')} (相关度: {source.get('score', 0):.2f})")
                else:
                    logger.error(f"❌ 对话失败: {result.get('error', 'unknown')}")
                    
            except KeyboardInterrupt:
                logger.info("\n👋 用户中断，退出对话")
                break
            except Exception as e:
                logger.error(f"❌ 对话异常: {str(e)}")
                
    except Exception as e:
        logger.error(f"❌ 交互式对话初始化失败: {str(e)}")

def main():
    """主函数"""
    setup_logging()
    
    logger.info("🎯 LangChain 智能对话服务启动器")
    logger.info("=" * 60)
    
    # 运行所有测试
    tests = [
        ("数据库连接", test_database_connection),
        ("知识库服务", test_knowledge_service),
        ("LangChain 服务", test_langchain_service),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 {test_name} 测试")
        logger.info("-" * 30)
        
        if test_func():
            passed += 1
        
        logger.info("-" * 30)
    
    logger.info(f"\n📊 预检测试结果: {passed}/{total} 通过")
    
    if passed == total:
        logger.success("🎉 所有预检测试通过！")
        
        # 询问是否运行交互式对话
        try:
            choice = input("\n是否启动交互式对话测试？(y/N): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                run_interactive_chat()
            else:
                logger.info("💡 跳过交互式对话测试")
        except KeyboardInterrupt:
            logger.info("\n👋 用户取消")
    else:
        logger.warning(f"⚠️ 有 {total - passed} 个预检测试失败")
        logger.info("💡 请检查服务配置和依赖项")

if __name__ == "__main__":
    main()
