"""
测试智能对话服务
"""
import os
import sys
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.intelligent_chat import get_intelligent_chat_service
from services.knowledge import get_knowledge_service
from loguru import logger


def test_knowledge_retrieval():
    """测试知识库检索"""
    print("=" * 50)
    print("测试知识库检索功能")
    print("=" * 50)
    
    try:
        chat_service = get_intelligent_chat_service("default")
        
        # 测试查询
        test_queries = [
            "什么是人工智能",
            "如何使用API",
            "系统配置说明"
        ]
        
        for query in test_queries:
            print(f"\n查询: {query}")
            knowledge_texts, sources = chat_service._retrieve_knowledge(query, 3)
            
            print(f"找到 {len(knowledge_texts)} 条相关知识")
            for i, (text, source) in enumerate(zip(knowledge_texts, sources), 1):
                print(f"  {i}. [{source.get('title', '未知')}] {text[:100]}...")
                print(f"     相似度: {source.get('score', 0):.3f}")
            
            if not knowledge_texts:
                print("  未找到相关知识")
    
    except Exception as e:
        print(f"知识库检索测试失败: {str(e)}")


def test_basic_chat():
    """测试基础对话功能"""
    print("\n" + "=" * 50)
    print("测试基础对话功能")
    print("=" * 50)
    
    try:
        chat_service = get_intelligent_chat_service("default")
        
        # 测试用户
        test_user = "test_user_001"
        
        # 测试对话
        test_messages = [
            "你好，我是新用户",
            "请介绍一下你的功能",
            "你能帮我查找资料吗？"
        ]
        
        for message in test_messages:
            print(f"\n用户: {message}")
            
            result = chat_service.chat_with_rag(
                user_message=message,
                send_user=test_user,
                platform=0,
                use_knowledge=True,
                max_results=3
            )
            
            if result.get("success"):
                print(f"助手: {result['assistant_response']}")
                print(f"知识库使用: {'是' if result['knowledge_used'] else '否'}")
                if result.get('sources'):
                    print(f"引用来源: {len(result['sources'])} 个")
            else:
                print(f"对话失败: {result.get('error')}")
    
    except Exception as e:
        print(f"基础对话测试失败: {str(e)}")


def test_conversation_history():
    """测试对话历史功能"""
    print("\n" + "=" * 50)
    print("测试对话历史功能")
    print("=" * 50)
    
    try:
        chat_service = get_intelligent_chat_service("default")
        test_user = "test_user_002"
        
        # 先进行几轮对话
        messages = [
            "我想了解Python编程",
            "什么是机器学习？",
            "请推荐一些学习资源"
        ]
        
        print("创建对话历史...")
        for msg in messages:
            result = chat_service.chat_with_rag(
                user_message=msg,
                send_user=test_user,
                use_knowledge=False  # 不使用知识库以加快速度
            )
            print(f"  {msg} -> {result.get('success', False)}")
        
        # 获取对话历史
        print(f"\n获取用户 {test_user} 的对话历史:")
        history = chat_service.get_conversation_history(test_user, limit=10)
        
        for i, conv in enumerate(history, 1):
            role_name = "用户" if conv["role"] == "user" else "助手"
            print(f"  {i}. [{conv['timestamp']}] {role_name}: {conv['content'][:50]}...")
        
        print(f"\n总共 {len(history)} 条对话记录")
        
        # 测试清除历史
        print(f"\n清除用户 {test_user} 的对话历史...")
        success = chat_service.clear_conversation_history(test_user)
        print(f"清除结果: {'成功' if success else '失败'}")
        
        # 验证清除结果
        history_after = chat_service.get_conversation_history(test_user)
        print(f"清除后剩余记录: {len(history_after)} 条")
    
    except Exception as e:
        print(f"对话历史测试失败: {str(e)}")


def test_knowledge_enhanced_chat():
    """测试知识增强对话"""
    print("\n" + "=" * 50)
    print("测试知识增强对话")
    print("=" * 50)
    
    try:
        # 首先确保知识库中有内容
        knowledge_service = get_knowledge_service()
        workspaces = knowledge_service.list_workspaces()
        
        if not workspaces:
            print("警告: 没有找到知识库工作区，创建测试工作区...")
            # 这里可以添加创建测试工作区的代码
            return
        
        workspace_slug = workspaces[0].slug
        print(f"使用知识库工作区: {workspace_slug}")
        
        chat_service = get_intelligent_chat_service(workspace_slug)
        test_user = "test_user_003"
        
        # 测试知识增强对话
        knowledge_questions = [
            "什么是API？",
            "如何使用这个系统？",
            "有什么功能特性？"
        ]
        
        for question in knowledge_questions:
            print(f"\n用户问题: {question}")
            
            result = chat_service.chat_with_rag(
                user_message=question,
                send_user=test_user,
                use_knowledge=True,
                max_results=3
            )
            
            if result.get("success"):
                print(f"助手回复: {result['assistant_response'][:200]}...")
                print(f"使用了知识库: {'是' if result['knowledge_used'] else '否'}")
                
                if result.get('sources'):
                    print("引用来源:")
                    for i, source in enumerate(result['sources'], 1):
                        print(f"  {i}. {source.get('title', '未知文档')} (相似度: {source.get('score', 0):.3f})")
            else:
                print(f"对话失败: {result.get('error')}")
    
    except Exception as e:
        print(f"知识增强对话测试失败: {str(e)}")


def test_service_health():
    """测试服务健康状态"""
    print("\n" + "=" * 50)
    print("测试服务健康状态")
    print("=" * 50)
    
    try:
        # 测试智能对话服务
        chat_service = get_intelligent_chat_service()
        print("✓ 智能对话服务初始化成功")
        
        # 测试知识库服务
        knowledge_service = get_knowledge_service()
        workspaces = knowledge_service.list_workspaces()
        print(f"✓ 知识库服务连接成功，找到 {len(workspaces)} 个工作区")
        
        for ws in workspaces:
            print(f"  - {ws.name} ({ws.slug})")
        
        # 测试数据库连接
        from utils.database import db
        if db.is_closed():
            db.connect()
        print("✓ 数据库连接正常")
        
        print("\n所有服务健康检查通过！")
    
    except Exception as e:
        print(f"服务健康检查失败: {str(e)}")


def main():
    """主测试函数"""
    print("智能对话服务测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 运行所有测试
    test_service_health()
    test_knowledge_retrieval()
    test_basic_chat()
    test_conversation_history()
    test_knowledge_enhanced_chat()
    
    print("\n" + "=" * 50)
    print("所有测试完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
