#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangChain 智能对话服务测试脚本
"""

import requests
import json
import time
import sys
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

# API 基础 URL
BASE_URL = "http://localhost:5000"

# 测试用户信息
TEST_USER_ID = "langchain_test_user"
TEST_WORKSPACE = "default"
TEST_PLATFORM = 0

# 请求头
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer test_token"  # 如果需要认证的话
}


def test_langchain_health_check():
    """测试 LangChain 服务健康检查"""
    logger.info("🔍 测试 LangChain 服务健康检查...")
    
    try:
        url = f"{BASE_URL}/intelligent_chat/langchain/health"
        response = requests.get(url, headers=HEADERS)
        
        logger.info(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.success("✅ LangChain 服务健康检查通过")
            logger.info(f"服务状态: {result.get('data', {}).get('status', 'unknown')}")
            logger.info(f"LangChain 可用性: {result.get('data', {}).get('langchain_available', False)}")
            return True
        else:
            logger.error(f"❌ 健康检查失败: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 健康检查异常: {str(e)}")
        return False


def test_langchain_service_info():
    """测试获取 LangChain 服务信息"""
    logger.info("📊 测试获取 LangChain 服务信息...")
    
    try:
        url = f"{BASE_URL}/intelligent_chat/langchain/info"
        params = {"workspace_slug": TEST_WORKSPACE}
        response = requests.get(url, params=params, headers=HEADERS)
        
        logger.info(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            service_info = result.get("data", {})
            logger.success("✅ 获取 LangChain 服务信息成功")
            logger.info(f"服务类型: {service_info.get('service_type', 'unknown')}")
            logger.info(f"工作区: {service_info.get('workspace_slug', 'unknown')}")
            logger.info(f"LangChain 可用: {service_info.get('langchain_available', False)}")
            logger.info(f"模型温度: {service_info.get('llm_temperature', 'unknown')}")
            return True
        else:
            logger.error(f"❌ 获取服务信息失败: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 获取服务信息异常: {str(e)}")
        return False


def test_langchain_chat():
    """测试 LangChain RAG 对话"""
    logger.info("💬 测试 LangChain RAG 对话...")
    
    test_messages = [
        "你好，请介绍一下自己",
        "什么是人工智能？",
        "如何提高工作效率？",
        "请解释一下机器学习的基本概念"
    ]
    
    for i, message in enumerate(test_messages, 1):
        logger.info(f"📝 测试消息 {i}: {message}")
        
        try:
            url = f"{BASE_URL}/intelligent_chat/langchain/chat"
            data = {
                "message": message,
                "user_id": TEST_USER_ID,
                "workspace_slug": TEST_WORKSPACE,
                "platform": TEST_PLATFORM,
                "use_knowledge": True,
                "max_results": 3,
                "temperature": 0.7
            }
            
            response = requests.post(url, json=data, headers=HEADERS)
            logger.info(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                chat_data = result.get("data", {})
                
                if chat_data.get("success"):
                    logger.success(f"✅ LangChain 对话 {i} 成功")
                    logger.info(f"用户消息: {chat_data.get('user_message', '')}")
                    logger.info(f"助手回复: {chat_data.get('assistant_response', '')[:100]}...")
                    logger.info(f"知识库使用: {chat_data.get('knowledge_used', False)}")
                    logger.info(f"LangChain 使用: {chat_data.get('langchain_used', False)}")
                    logger.info(f"来源数量: {len(chat_data.get('sources', []))}")
                else:
                    logger.error(f"❌ LangChain 对话 {i} 失败: {chat_data.get('error', 'unknown')}")
            else:
                logger.error(f"❌ LangChain 对话 {i} 请求失败: {response.text}")
                
            # 短暂等待
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ LangChain 对话 {i} 异常: {str(e)}")
    
    return True


def test_langchain_history():
    """测试 LangChain 对话历史功能"""
    logger.info("📚 测试 LangChain 对话历史功能...")
    
    try:
        # 获取对话历史
        url = f"{BASE_URL}/intelligent_chat/langchain/history/{TEST_USER_ID}"
        params = {
            "platform": TEST_PLATFORM,
            "workspace_slug": TEST_WORKSPACE,
            "limit": 10
        }
        
        response = requests.get(url, params=params, headers=HEADERS)
        logger.info(f"获取历史状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            history_data = result.get("data", {})
            conversations = history_data.get("conversations", [])
            
            logger.success(f"✅ 获取 LangChain 对话历史成功，共 {len(conversations)} 条记录")
            
            # 显示最近几条对话
            for i, conv in enumerate(conversations[-3:], 1):
                logger.info(f"对话 {i}: [{conv.get('role', 'unknown')}] {conv.get('content', '')[:50]}...")
        else:
            logger.error(f"❌ 获取 LangChain 对话历史失败: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ 获取 LangChain 对话历史异常: {str(e)}")


def test_langchain_config_update():
    """测试 LangChain 配置更新"""
    logger.info("⚙️ 测试 LangChain 配置更新...")
    
    try:
        url = f"{BASE_URL}/intelligent_chat/langchain/config"
        data = {
            "workspace_slug": TEST_WORKSPACE,
            "temperature": 0.5,
            "max_tokens": 1000
        }
        
        response = requests.post(url, json=data, headers=HEADERS)
        logger.info(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            config_data = result.get("data", {})
            logger.success("✅ LangChain 配置更新成功")
            logger.info(f"更新的配置: {config_data.get('updated_config', {})}")
        else:
            logger.error(f"❌ LangChain 配置更新失败: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ LangChain 配置更新异常: {str(e)}")


def test_clear_langchain_history():
    """测试清除 LangChain 对话历史"""
    logger.info("🗑️ 测试清除 LangChain 对话历史...")
    
    try:
        url = f"{BASE_URL}/intelligent_chat/langchain/history/{TEST_USER_ID}"
        params = {
            "platform": TEST_PLATFORM,
            "workspace_slug": TEST_WORKSPACE
        }
        
        response = requests.delete(url, params=params, headers=HEADERS)
        logger.info(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.success("✅ 清除 LangChain 对话历史成功")
        else:
            logger.error(f"❌ 清除 LangChain 对话历史失败: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ 清除 LangChain 对话历史异常: {str(e)}")


def run_all_tests():
    """运行所有测试"""
    logger.info("🚀 开始 LangChain 智能对话服务测试")
    logger.info("=" * 60)
    
    tests = [
        ("健康检查", test_langchain_health_check),
        ("服务信息", test_langchain_service_info),
        ("RAG 对话", test_langchain_chat),
        ("对话历史", test_langchain_history),
        ("配置更新", test_langchain_config_update),
        # ("清除历史", test_clear_langchain_history),  # 注释掉，避免清除测试数据
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 开始测试: {test_name}")
        logger.info("-" * 40)
        
        try:
            if test_func():
                passed += 1
                logger.success(f"✅ {test_name} 测试通过")
            else:
                logger.error(f"❌ {test_name} 测试失败")
        except Exception as e:
            logger.error(f"❌ {test_name} 测试异常: {str(e)}")
        
        logger.info("-" * 40)
        time.sleep(2)  # 测试间隔
    
    logger.info("\n" + "=" * 60)
    logger.info(f"🏁 LangChain 智能对话服务测试完成")
    logger.info(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        logger.success("🎉 所有测试通过！LangChain 智能对话服务运行正常")
    else:
        logger.warning(f"⚠️ 有 {total - passed} 个测试失败，请检查服务配置")


if __name__ == "__main__":
    # 检查服务器是否运行
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            logger.info("✅ 服务器运行正常，开始测试...")
            run_all_tests()
        else:
            logger.error("❌ 服务器未正常响应，请检查服务器是否启动")
    except requests.exceptions.RequestException:
        logger.error("❌ 无法连接到服务器，请确保服务器在 http://localhost:5000 运行")
        logger.info("💡 可以运行 'python app.py' 启动服务器")
