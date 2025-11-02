#!/usr/bin/env python3
"""
验证知识库MCP服务器设置脚本
"""

import sys
import os
import traceback

def check_imports():
    """检查所有必要的模块导入"""
    print("🔍 检查模块导入...")
    
    try:
        # 检查核心依赖
        import requests
        print("✅ requests 导入成功")
        
        import fastmcp
        print("✅ fastmcp 导入成功")
        
        import flask
        print("✅ flask 导入成功")
        
        import flasgger
        print("✅ flasgger 导入成功")
        
        # 检查项目模块
        from models.knowledge import Workspace, Document
        print("✅ 知识库模型导入成功")
        
        from services.knowledge import get_knowledge_service
        print("✅ 知识库服务导入成功")
        
        from api.knowledge import bp as kb_bp
        print("✅ 知识库API导入成功")
        
        from mcp_servers.knowledge_base import create_knowledge_base_server
        print("✅ 知识库MCP服务器导入成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 意外错误: {e}")
        traceback.print_exc()
        return False


def check_config():
    """检查配置"""
    print("\n🔧 检查配置...")
    
    try:
        from config.knowledge import kb_config
        print(f"✅ 知识库配置加载成功")
        print(f"   - Base URL: {kb_config.get_base_url()}")
        print(f"   - API Key: {'已设置' if kb_config.get_api_key() else '未设置'}")
        print(f"   - 超时设置: {kb_config.HTTP_TIMEOUT}秒")
        
        from config.mcp import mcp_config
        print(f"✅ MCP配置加载成功")
        print(f"   - 服务器端口: {mcp_config.SERVER_PORT}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        return False


def check_mcp_server():
    """检查MCP服务器创建"""
    print("\n🚀 检查MCP服务器...")
    
    try:
        from mcp_servers.knowledge_base import create_knowledge_base_server
        
        # 创建服务器实例
        server = create_knowledge_base_server()
        print("✅ MCP服务器创建成功")
        print(f"   - 服务器名称: {server.name}")
        
        # 检查工具数量
        tools = server.list_tools()
        print(f"   - 可用工具数量: {len(tools)}")
        
        # 显示前几个工具
        for i, tool in enumerate(tools[:5]):
            print(f"     {i+1}. {tool.name}")
        
        if len(tools) > 5:
            print(f"     ... 和其他 {len(tools) - 5} 个工具")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP服务器检查失败: {e}")
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🎯 知识库MCP服务器设置验证")
    print("=" * 50)
    
    checks = [
        ("模块导入", check_imports),
        ("配置检查", check_config),
        ("MCP服务器", check_mcp_server),
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        try:
            if check_func():
                passed += 1
            else:
                print(f"\n❌ {name} 检查失败")
        except Exception as e:
            print(f"\n❌ {name} 检查出现异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 检查结果: {passed}/{total} 项通过")
    
    if passed == total:
        print("🎉 所有检查都通过了！知识库MCP服务器设置完成。")
        print("\n📋 下一步操作:")
        print("1. 设置 AnythingLLM 连接配置（.env文件）")
        print("2. 运行 python start_all.py 启动所有服务")
        print("3. 测试与 AnythingLLM 的连接")
        return 0
    else:
        print("⚠️  部分检查失败，请检查上述错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
