import unittest
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.knowledge import KnowledgeBaseService
from models.knowledge import (
    WorkspaceCreateRequest, DocumentUploadRequest, ChatRequest, VectorSearchRequest
)


class TestKnowledgeBase(unittest.TestCase):
    """知识库服务测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.service = KnowledgeBaseService()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """清理测试环境"""
        self.loop.close()
    
    def run_async(self, coro):
        """运行异步函数"""
        return self.loop.run_until_complete(coro)
    
    def test_service_initialization(self):
        """测试服务初始化"""
        self.assertIsNotNone(self.service)
        self.assertIsNotNone(self.service.base_url)
        self.assertIsNotNone(self.service.client)
    
    def test_workspace_creation_request(self):
        """测试工作区创建请求模型"""
        request = WorkspaceCreateRequest(
            name="测试工作区",
            description="这是一个测试工作区",
            openai_temp=0.7,
            openai_history=20
        )
        self.assertEqual(request.name, "测试工作区")
        self.assertEqual(request.openai_temp, 0.7)
    
    def test_document_upload_request(self):
        """测试文档上传请求模型"""
        request = DocumentUploadRequest(
            file_name="test.txt",
            content="这是测试内容",
            metadata={"author": "test"},
            add_to_workspaces="test-workspace"
        )
        self.assertEqual(request.file_name, "test.txt")
        self.assertEqual(request.content, "这是测试内容")
    
    def test_chat_request(self):
        """测试聊天请求模型"""
        request = ChatRequest(
            message="你好",
            mode="chat",
            workspace_slug="test-workspace"
        )
        self.assertEqual(request.message, "你好")
        self.assertEqual(request.workspace_slug, "test-workspace")
    
    def test_vector_search_request(self):
        """测试向量搜索请求模型"""
        request = VectorSearchRequest(
            query="搜索内容",
            workspace_slug="test-workspace",
            top_k=5,
            threshold=0.7
        )
        self.assertEqual(request.query, "搜索内容")
        self.assertEqual(request.top_k, 5)
    
    # 注释掉需要实际服务器的测试，避免在没有服务器时失败
    # def test_list_workspaces(self):
    #     """测试获取工作区列表"""
    #     try:
    #         workspaces = self.run_async(self.service.list_workspaces())
    #         self.assertIsInstance(workspaces, list)
    #     except Exception as e:
    #         # 如果服务器不可用，跳过测试
    #         self.skipTest(f"服务器不可用: {e}")


if __name__ == '__main__':
    # 创建测试目录
    os.makedirs('tests', exist_ok=True)
    
    # 运行测试
    unittest.main()
