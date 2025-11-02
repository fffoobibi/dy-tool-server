# DY Tool Server - 知识库 MCP 服务器

基于 AnythingLLM 的知识库管理系统，提供完整的 MCP（Model Context Protocol）服务器实现。

## ✨ 功能特性

### 🧠 知识库管理
- **工作区管理**: 创建、更新、删除工作区
- **文档管理**: 上传文本、URL文档到知识库
- **向量搜索**: 基于语义相似度的智能搜索
- **对话功能**: 与知识库进行智能对话
- **嵌入管理**: 动态更新文档嵌入向量

### 🔧 MCP 服务器功能
- **浏览器控制**: 网页自动化操作
- **媒体处理**: 音视频处理功能  
- **通用工具**: 文件操作、网络请求等
- **知识库集成**: 完整的知识库 MCP 工具

### 🌐 API 服务
- **RESTful API**: 完整的 Flask Web API
- **Swagger 文档**: 自动生成的 API 文档
- **异步支持**: 高性能异步处理
- **错误处理**: 完善的异常处理机制

## 🚀 快速开始

### 环境要求
- Python 3.8+
- AnythingLLM 服务器（可选）

### 安装依赖
```bash
# 安装基础依赖
pip install -r requirements.txt

# 安装 MCP 相关依赖  
pip install -r requirements_mcp.txt
```

### 配置设置
1. 复制环境配置文件：
```bash
copy .env.example .env
```

2. 编辑 `.env` 文件，配置 AnythingLLM 连接：
```bash
# AnythingLLM 服务器地址
ANYTHING_LLM_BASE_URL=http://localhost:3001
# API 密钥（如果需要）
ANYTHING_LLM_API_KEY=your_api_key_here
```

### 启动服务

#### 方法1: 一键启动（推荐）
```bash
python start_all.py
```

#### 方法2: 分别启动
```bash
# 启动 Flask API 服务器
python app.py

# 启动 MCP 服务器  
python mcp_server.py
```

### 访问服务
- **Web API**: http://localhost:5000
- **API 文档**: http://localhost:5000/docs/
- **MCP 服务器**: http://localhost:8000

## 📚 API 使用示例

### 工作区管理

#### 创建工作区
```python
import requests

response = requests.post('http://localhost:5000/knowledge_base/workspaces', json={
    "name": "我的知识库",
    "description": "测试知识库",
    "openai_temp": 0.7,
    "openai_history": 20
})
```

#### 获取工作区列表
```python
response = requests.get('http://localhost:5000/knowledge_base/workspaces')
workspaces = response.json()['data']['workspaces']
```

### 文档管理

#### 上传文本文档
```python
response = requests.post('http://localhost:5000/knowledge_base/documents/upload-text', json={
    "file_name": "test.txt",
    "content": "这是测试文档内容",
    "add_to_workspaces": "my-workspace"
})
```

#### 上传URL文档
```python
response = requests.post('http://localhost:5000/knowledge_base/documents/upload-url', json={
    "url": "https://example.com/article",
    "add_to_workspaces": "my-workspace"
})
```

### 智能对话

#### 与工作区对话
```python
response = requests.post('http://localhost:5000/knowledge_base/workspaces/my-workspace/chat', json={
    "message": "请总结一下文档内容",
    "mode": "chat"
})
```

### 向量搜索

#### 搜索相关文档
```python
response = requests.post('http://localhost:5000/knowledge_base/workspaces/my-workspace/search', json={
    "query": "机器学习算法",
    "top_k": 5,
    "threshold": 0.7
})
```

## 🛠️ MCP 工具使用

知识库 MCP 服务器提供了以下工具：

### 工作区工具
- `list_workspaces`: 获取所有工作区
- `get_workspace`: 获取工作区详情
- `create_workspace`: 创建新工作区
- `update_workspace`: 更新工作区
- `delete_workspace`: 删除工作区

### 文档工具
- `list_documents`: 获取文档列表
- `get_document`: 获取文档详情
- `upload_text_document`: 上传文本文档
- `upload_url_document`: 上传URL文档

### 对话工具
- `chat_with_workspace`: 与工作区对话
- `vector_search`: 向量搜索

### 管理工具
- `update_embeddings`: 更新嵌入
- `update_pin_status`: 更新固定状态
- `get_workspace_stats`: 获取统计信息
- `health_check`: 健康检查

## 📁 项目结构

```
dy-tool-server/
├── api/                    # Flask API 路由
│   └── knowledge_base.py  # 知识库 API
├── mcp_servers/           # MCP 服务器实现
│   ├── knowledge_base.py  # 知识库 MCP 服务器
│   ├── browser.py         # 浏览器 MCP 服务器
│   └── ...               # 其他 MCP 服务器
├── services/              # 业务逻辑层
│   └── knowledge_base.py  # 知识库服务
├── models/                # 数据模型
│   └── knowledge_base.py  # 知识库模型
├── config/                # 配置管理
│   ├── mcp.py            # MCP 配置
│   └── knowledge_base.py  # 知识库配置
├── utils/                 # 工具函数
├── tests/                 # 测试文件
├── app.py                # Flask 应用入口
├── mcp_server.py         # MCP 服务器入口
├── start_all.py          # 一键启动脚本
└── requirements*.txt     # 依赖文件
```

## 🔧 配置选项

### MCP 服务器配置
- `MCP_HOST`: 服务器主机地址（默认: localhost）
- `MCP_PORT`: 服务器端口（默认: 8000）
- `MCP_TRANSPORT`: 传输协议（sse/stdio）

### 知识库配置
- `ANYTHING_LLM_BASE_URL`: AnythingLLM 服务器地址
- `ANYTHING_LLM_API_KEY`: API 访问密钥
- `LOCAL_STORAGE_PATH`: 本地存储路径
- `MAX_DOCUMENT_SIZE`: 最大文档大小（字节）

### 功能开关
- `ENABLE_BROWSER_SERVER`: 启用浏览器服务器
- `ENABLE_KNOWLEDGE_BASE_SERVER`: 启用知识库服务器
- `ENABLE_OPENAPI_INTEGRATION`: 启用 OpenAPI 集成

## 🧪 测试

运行测试：
```bash
python tests/test_knowledge_base.py
```

## 📋 待办事项

- [ ] 添加文件上传功能（PDF、Word等）
- [ ] 支持批量文档处理
- [ ] 添加文档分类和标签
- [ ] 实现用户权限管理
- [ ] 添加监控和日志功能
- [ ] 支持多种向量数据库
- [ ] 添加文档版本控制

## 🤝 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持

如果你遇到问题或有建议，请：
- 提交 [Issue](../../issues)
- 查看 [API 文档](http://localhost:5000/docs/)
- 检查配置文件设置

---

**享受智能知识库管理的乐趣！** 🎉
