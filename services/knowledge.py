import uuid
import requests

from typing import List, Optional, Dict
from dateutil.parser import parse as parse_datetime
from models.dantic.knowledge import (
    Document,
    Workspace,
    ChatRequest,
    ChatResponse,
    VectorSearchRequest,
    VectorSearchResult,
    DocumentUploadRequest,
    DocumentUploadResponse,
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    EmbeddingUpdateRequest,
    PinUpdateRequest,
    DocumentType,
)
from config.knowledge import kb_config


class KnowledgeBaseException(Exception):
    """知识库服务异常"""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class KnowledgeBaseService:
    """知识库服务类"""

    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = (base_url or kb_config.get_base_url()).rstrip("/")
        self.api_key = api_key or kb_config.get_api_key()
        self.headers = kb_config.get_headers()
        self.timeout = kb_config.HTTP_TIMEOUT

        # 创建requests会话
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    # 工作区管理
    def list_workspaces(self) -> List[Workspace]:
        """获取所有工作区"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/workspaces", timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            workspaces = []
            for ws_data in data.get("workspaces", []):
                workspace = Workspace(
                    id=ws_data.get("id"),
                    name=ws_data.get("name"),
                    slug=ws_data.get("slug"),
                    openai_temp=ws_data.get("openAiTemp"),
                    openai_history=ws_data.get("openAiHistory", 20),
                    openai_prompt=ws_data.get("openAiPrompt"),
                    created_at=(
                        parse_datetime(ws_data.get("createdAt"))
                        if ws_data.get("createdAt")
                        else None
                    ),
                    last_updated_at=(
                        parse_datetime(ws_data.get("lastUpdatedAt"))
                        if ws_data.get("lastUpdatedAt")
                        else None
                    ),
                    threads=ws_data.get("threads", []),
                )
                workspaces.append(workspace)

            return workspaces
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"获取工作区列表失败: {str(e)}")

    def get_workspace(self, slug: str) -> Optional[Workspace]:
        """根据slug获取工作区详情"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/workspace/{slug}", timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            ws_data = data.get("workspace")
            if not ws_data:
                return None

            return Workspace(
                id=ws_data.get("id"),
                name=ws_data.get("name"),
                slug=ws_data.get("slug"),
                openai_temp=ws_data.get("openAiTemp"),
                openai_history=ws_data.get("openAiHistory", 20),
                openai_prompt=ws_data.get("openAiPrompt"),
                documents=ws_data.get("documents", []),
                threads=ws_data.get("threads", []),
                created_at=(
                    parse_datetime(ws_data.get("createdAt"))
                    if ws_data.get("createdAt")
                    else None
                ),
                last_updated_at=(
                    parse_datetime(ws_data.get("lastUpdatedAt"))
                    if ws_data.get("lastUpdatedAt")
                    else None
                ),
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise KnowledgeBaseException(
                f"获取工作区失败: {str(e)}", e.response.status_code
            )
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"获取工作区失败: {str(e)}")

    def create_workspace(self, request: WorkspaceCreateRequest) -> Workspace:
        """创建新工作区"""
        try:
            payload = {
                "name": request.name,
            }

            if request.description:
                payload["description"] = request.description
            if request.openai_temp is not None:
                payload["openAiTemp"] = request.openai_temp
            if request.openai_history is not None:
                payload["openAiHistory"] = request.openai_history
            if request.openai_prompt:
                payload["openAiPrompt"] = request.openai_prompt

            response = self.session.post(
                f"{self.base_url}/api/v1/workspace/new",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            ws_data = data.get("workspace")
            return Workspace(
                id=ws_data.get("id"),
                name=ws_data.get("name"),
                slug=ws_data.get("slug"),
                openai_temp=ws_data.get("openAiTemp"),
                openai_history=ws_data.get("openAiHistory", 20),
                openai_prompt=ws_data.get("openAiPrompt"),
                created_at=(
                    parse_datetime(ws_data.get("createdAt"))
                    if ws_data.get("createdAt")
                    else None
                ),
                last_updated_at=(
                    parse_datetime(ws_data.get("lastUpdatedAt"))
                    if ws_data.get("lastUpdatedAt")
                    else None
                ),
            )
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"创建工作区失败: {str(e)}")

    def update_workspace(self, slug: str, request: WorkspaceUpdateRequest) -> Workspace:
        """更新工作区"""
        try:
            payload = {}
            if request.name:
                payload["name"] = request.name
            if request.description:
                payload["description"] = request.description
            if request.openai_temp is not None:
                payload["openAiTemp"] = request.openai_temp
            if request.openai_history is not None:
                payload["openAiHistory"] = request.openai_history
            if request.openai_prompt:
                payload["openAiPrompt"] = request.openai_prompt

            response = self.session.post(
                f"{self.base_url}/api/v1/workspace/{slug}/update",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            ws_data = data.get("workspace")
            return Workspace(
                id=ws_data.get("id"),
                name=ws_data.get("name"),
                slug=ws_data.get("slug"),
                openai_temp=ws_data.get("openAiTemp"),
                openai_history=ws_data.get("openAiHistory", 20),
                openai_prompt=ws_data.get("openAiPrompt"),
                documents=ws_data.get("documents", []),
                created_at=(
                    parse_datetime(ws_data.get("createdAt"))
                    if ws_data.get("createdAt")
                    else None
                ),
                last_updated_at=(
                    parse_datetime(ws_data.get("lastUpdatedAt"))
                    if ws_data.get("lastUpdatedAt")
                    else None
                ),
            )
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"更新工作区失败: {str(e)}")

    def delete_workspace(self, slug: str) -> bool:
        """删除工作区"""
        try:
            response = self.session.delete(
                f"{self.base_url}/api/v1/workspace/{slug}", timeout=self.timeout
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"删除工作区失败: {str(e)}")

    # 文档管理
    def list_documents(self) -> List[Document]:
        """获取所有文档"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/documents", timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            documents = []
            local_files = data.get("localFiles", {})
            items = local_files.get("items", [])

            for item in items:
                if item.get("type") == "file":
                    doc = Document(
                        id=item.get("id"),
                        name=item.get("name"),
                        type=self._get_document_type(item.get("name")),
                        size=0,  # API doesn't provide size
                        title=item.get("title", ""),
                        url=item.get("url"),
                        cached=item.get("cached", False),
                        location=item.get("location", ""),
                    )
                    documents.append(doc)

            return documents
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"获取文档列表失败: {str(e)}")

    def get_document(self, doc_name: str) -> Optional[Document]:
        """根据名称获取文档详情"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/document/{doc_name}", timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            local_files = data.get("localFiles", {})
            items = local_files.get("items", [])

            if items:
                item = items[0]  # 应该只有一个文档
                return Document(
                    id=item.get("id"),
                    name=item.get("name"),
                    type=self._get_document_type(item.get("name")),
                    size=0,
                    title=item.get("title", ""),
                    url=item.get("url"),
                    cached=item.get("cached", False),
                    location=item.get("location", ""),
                )
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise KnowledgeBaseException(
                f"获取文档失败: {str(e)}", e.response.status_code
            )
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"获取文档失败: {str(e)}")

    def upload_document_text(
        self, request: DocumentUploadRequest
    ) -> DocumentUploadResponse:
        """上传文本文档"""
        try:
            payload = {
                "textContent": request.content or "",
                "metadata": request.metadata,
            }

            if request.add_to_workspaces:
                payload["addToWorkspaces"] = request.add_to_workspaces

            response = self.session.post(
                f"{self.base_url}/api/v1/document/raw-text",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            documents = []
            for doc_data in data.get("documents", []):
                doc = Document(
                    id=doc_data.get("id"),
                    name=doc_data.get("title", ""),
                    type=self._get_document_type(doc_data.get("title", "")),
                    size=doc_data.get("wordCount", 0),
                    title=doc_data.get("title", ""),
                    doc_author=doc_data.get("docAuthor"),
                    description=doc_data.get("description"),
                    doc_source=doc_data.get("docSource"),
                    chunk_source=doc_data.get("chunkSource"),
                    published=doc_data.get("published"),
                    word_count=doc_data.get("wordCount"),
                    token_count_estimate=doc_data.get("token_count_estimate"),
                    location=doc_data.get("location"),
                    url=doc_data.get("url"),
                )
                documents.append(doc)

            return DocumentUploadResponse(
                success=data.get("success", True),
                error=data.get("error"),
                documents=documents,
            )
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"上传文档失败: {str(e)}")

    def upload_document_url(
        self, url: str, add_to_workspaces: str = None
    ) -> DocumentUploadResponse:
        """上传URL链接文档"""
        try:
            payload = {"link": url}

            if add_to_workspaces:
                payload["addToWorkspaces"] = add_to_workspaces

            response = self.session.post(
                f"{self.base_url}/api/v1/document/upload-link",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            documents = []
            for doc_data in data.get("documents", []):
                doc = Document(
                    id=doc_data.get("id"),
                    name=doc_data.get("title", ""),
                    type=self._get_document_type(doc_data.get("title", "")),
                    size=doc_data.get("wordCount", 0),
                    title=doc_data.get("title", ""),
                    doc_author=doc_data.get("docAuthor"),
                    description=doc_data.get("description"),
                    doc_source=doc_data.get("docSource"),
                    chunk_source=doc_data.get("chunkSource"),
                    published=doc_data.get("published"),
                    word_count=doc_data.get("wordCount"),
                    token_count_estimate=doc_data.get("token_count_estimate"),
                    location=doc_data.get("location"),
                    url=doc_data.get("url"),
                )
                documents.append(doc)

            return DocumentUploadResponse(
                success=data.get("success", True),
                error=data.get("error"),
                documents=documents,
            )
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"上传URL文档失败: {str(e)}")

    # 聊天功能
    def chat_with_workspace(self, request: ChatRequest) -> ChatResponse:
        """与工作区聊天"""
        try:
            payload = {"message": request.message, "mode": request.mode}

            if request.thread_slug:
                url = f"{self.base_url}/api/v1/workspace/{request.workspace_slug}/thread/{request.thread_slug}/chat"
            else:
                url = f"{self.base_url}/api/v1/workspace/{request.workspace_slug}/chat"

            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            return ChatResponse(
                id=data.get("id", str(uuid.uuid4())),
                type=data.get("type", "textResponse"),
                text_response=data.get("textResponse", ""),
                sources=data.get("sources", []),
                close=data.get("close", True),
                error=data.get("error"),
            )
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"聊天失败: {str(e)}")

    def vector_search(self, request: VectorSearchRequest) -> List[VectorSearchResult]:
        """向量搜索"""
        try:
            payload = {
                "query": request.query,
                "topK": request.top_k,
                "threshold": request.threshold,
            }

            response = self.session.post(
                f"{self.base_url}/api/v1/workspace/{request.workspace_slug}/vector-search",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for result_data in data.get("results", []):
                result = VectorSearchResult(
                    id=result_data.get("id", ""),
                    text=result_data.get("text", ""),
                    metadata=result_data.get("metadata", {}),
                    distance=result_data.get("distance", 0.0),
                    score=result_data.get("score", 0.0),
                )
                results.append(result)

            return results
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"向量搜索失败: {str(e)}")

    # 嵌入管理
    def update_embeddings(self, slug: str, request: EmbeddingUpdateRequest) -> bool:
        """更新工作区嵌入"""
        try:
            payload = {"adds": request.adds, "deletes": request.deletes}

            response = self.session.post(
                f"{self.base_url}/api/v1/workspace/{slug}/update-embeddings",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"更新嵌入失败: {str(e)}")

    def update_pin_status(self, slug: str, request: PinUpdateRequest) -> bool:
        """更新文档固定状态"""
        try:
            payload = {"documentPath": request.document_path, "pinned": request.pinned}

            response = self.session.post(
                f"{self.base_url}/api/v1/workspace/{slug}/update-pin",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"更新固定状态失败: {str(e)}")

    # 工具方法
    def _get_document_type(self, filename: str) -> DocumentType:
        """根据文件名获取文档类型"""
        if not filename:
            return DocumentType.TEXT

        ext = filename.lower().split(".")[-1]
        type_mapping = {
            "txt": DocumentType.TEXT,
            "md": DocumentType.MARKDOWN,
            "pdf": DocumentType.PDF,
            "docx": DocumentType.DOCX,
            "html": DocumentType.HTML,
            "htm": DocumentType.HTML,
            "json": DocumentType.JSON,
        }
        return type_mapping.get(ext, DocumentType.TEXT)

    def get_accepted_file_types(self) -> Dict[str, List[str]]:
        """获取支持的文件类型"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/document/accepted-file-types",
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("types", {})
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"获取文件类型失败: {str(e)}")

    def get_metadata_schema(self) -> Dict[str, str]:
        """获取元数据模式"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/document/metadata-schema", timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get("schema", {})
        except requests.exceptions.RequestException as e:
            raise KnowledgeBaseException(f"获取元数据模式失败: {str(e)}")


# 单例实例
_knowledge_service = None


def get_knowledge_service(
    base_url: str = None, api_key: str = None
) -> KnowledgeBaseService:
    """获取知识库服务实例"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeBaseService(base_url=base_url, api_key=api_key)
    return _knowledge_service
