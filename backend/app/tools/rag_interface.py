"""
RAG 工具基类接口

定义 RAG（检索增强生成）工具的抽象基类和结果数据模型。
Markdown RAG 和 Graph RAG 工具都继承此接口。

Requirements: 11.3, 12.3
"""

from abc import ABC, abstractmethod
from typing import Any, List

from pydantic import BaseModel, Field


class RAGResult(BaseModel):
    """RAG 检索结果数据模型

    Attributes:
        content: 检索到的文本内容
        source: 内容来源标识（文件路径、文档ID等）
        similarity_score: 相似度分数，范围 0.0-1.0
        metadata: 附加元数据字典
    """

    content: str = Field(..., description="检索到的文本内容")
    source: str = Field(..., description="内容来源标识")
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="相似度分数，范围 0.0-1.0"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元数据")


class RAGInterface(ABC):
    """RAG 工具基类接口

    定义所有 RAG 检索工具必须实现的方法。
    包括检索查询和健康检查功能。
    """

    @abstractmethod
    async def query(
        self,
        query_text: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> List[RAGResult]:
        """执行检索查询

        Args:
            query_text: 查询文本
            top_k: 返回的最大结果数量，范围 1-20，默认 5
            similarity_threshold: 相似度阈值，范围 0.0-1.0，默认 0.7
                                  只返回相似度不低于此阈值的结果

        Returns:
            RAGResult 列表，按相似度降序排列

        Raises:
            RAGQueryError: 检索过程中发生错误
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """检查服务健康状态

        检查 RAG 工具所依赖的服务（如向量数据库、图数据库）是否可用。

        Returns:
            True 表示服务正常，False 表示服务异常
        """
        pass
