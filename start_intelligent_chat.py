"""
启动智能对话服务测试
"""
import os
import sys
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入必要的模块
import settings
from utils import init_database
from test_intelligent_chat import main as test_main


def initialize_environment():
    """初始化环境"""
    print("初始化智能对话服务环境...")
    
    try:
        # 初始化数据库
        print("初始化数据库连接...")
        init_database()
        print("✓ 数据库初始化完成")
        
        # 检查环境变量
        required_env_vars = [
            "ANYTHINGLLM_BASE_URL",
            "ANYTHINGLLM_API_KEY"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  缺少环境变量: {', '.join(missing_vars)}")
            print("请在 .env 文件中配置这些变量")
            return False
        
        print("✓ 环境变量检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 环境初始化失败: {str(e)}")
        return False


def show_api_examples():
    """显示API使用示例"""
    print("\n" + "=" * 60)
    print("智能对话API使用示例")
    print("=" * 60)
    
    base_url = "http://localhost:5000"  # 根据实际情况调整
    
    examples = [
        {
            "name": "基础对话",
            "method": "POST",
            "url": f"{base_url}/intelligent_chat/chat",
            "data": {
                "message": "你好，请介绍一下你的功能",
                "user_id": "user123",
                "workspace_slug": "default",
                "use_knowledge": True
            }
        },
        {
            "name": "获取对话历史",
            "method": "GET",
            "url": f"{base_url}/intelligent_chat/history/user123?platform=0&limit=20"
        },
        {
            "name": "知识库检索测试",
            "method": "GET",
            "url": f"{base_url}/intelligent_chat/knowledge/search?query=API使用方法&max_results=3"
        },
        {
            "name": "清除对话历史",
            "method": "DELETE",
            "url": f"{base_url}/intelligent_chat/history/user123?platform=0"
        },
        {
            "name": "服务健康检查",
            "method": "GET",
            "url": f"{base_url}/intelligent_chat/health"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['name']}")
        print(f"   {example['method']} {example['url']}")
        if 'data' in example:
            print(f"   数据: {json.dumps(example['data'], ensure_ascii=False, indent=8)}")


def show_mcp_tools():
    """显示MCP工具示例"""
    print("\n" + "=" * 60)
    print("智能对话MCP工具示例")
    print("=" * 60)
    
    tools = [
        {
            "name": "rag_chat",
            "description": "RAG增强的智能对话",
            "params": {
                "message": "你好，我想了解人工智能",
                "user_id": "user123",
                "workspace_slug": "default",
                "use_knowledge": True
            }
        },
        {
            "name": "get_chat_history",
            "description": "获取用户对话历史",
            "params": {
                "user_id": "user123",
                "limit": 10
            }
        },
        {
            "name": "knowledge_search",
            "description": "知识库检索测试",
            "params": {
                "query": "机器学习算法",
                "max_results": 5
            }
        },
        {
            "name": "get_chat_stats",
            "description": "获取用户对话统计",
            "params": {
                "user_id": "user123"
            }
        },
        {
            "name": "intelligent_chat_health_check",
            "description": "智能对话服务健康检查",
            "params": {}
        }
    ]
    
    for i, tool in enumerate(tools, 1):
        print(f"\n{i}. {tool['name']}")
        print(f"   描述: {tool['description']}")
        print(f"   参数: {json.dumps(tool['params'], ensure_ascii=False, indent=8)}")


def main():
    """主函数"""
    print("智能对话服务启动器")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 初始化环境
    if not initialize_environment():
        print("❌ 环境初始化失败，退出")
        return
    
    print("\n✓ 智能对话服务准备就绪")
    
    # 运行测试
    try:
        print("\n开始运行功能测试...")
        test_main()
    except Exception as e:
        print(f"❌ 测试运行失败: {str(e)}")
    
    # 显示使用示例
    show_api_examples()
    show_mcp_tools()
    
    print("\n" + "=" * 60)
    print("智能对话服务功能说明:")
    print("1. RAG增强对话 - 结合知识库检索和LLM生成")
    print("2. 对话历史管理 - 保存和检索用户对话记录")
    print("3. 知识库检索 - 从向量数据库中搜索相关信息")
    print("4. 多平台支持 - 支持不同平台的用户隔离")
    print("5. 批量处理 - 支持批量消息处理")
    print("6. 统计分析 - 提供对话使用统计")
    print("=" * 60)
    
    print("\n要启动完整服务，请运行:")
    print("  python app.py                    # 启动Flask API服务")
    print("  python mcp_server.py            # 启动MCP服务器")
    print("  python start_all.py             # 启动所有服务")


if __name__ == "__main__":
    main()
