"""
Graph RAG 检索工具

基于 LlamaIndex KnowledgeGraphIndex 和 Neo4j 图数据库的知识图谱检索工具。
用于神经心理智能体检索心理神经免疫学知识图谱。

Requirements: 12.1-12.7
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.core.exceptions import RAGQueryError
from app.tools.rag_interface import RAGInterface, RAGResult

# 延迟导入以支持可选依赖和mock测试
if TYPE_CHECKING:
    from llama_index.core import Document, KnowledgeGraphIndex
    from llama_index.graph_stores.neo4j import Neo4jGraphStore


class EntityInfo(BaseModel):
    """实体信息

    Attributes:
        name: 实体名称
        type: 实体类型
        properties: 实体属性字典
    """

    name: str = Field(..., description="实体名称")
    type: str = Field(default="unknown", description="实体类型")
    properties: dict[str, Any] = Field(default_factory=dict, description="实体属性")


class RelationInfo(BaseModel):
    """关系信息

    Attributes:
        source_entity: 源实体名称
        target_entity: 目标实体名称
        relation_type: 关系类型
    """

    source_entity: str = Field(..., description="源实体名称")
    target_entity: str = Field(..., description="目标实体名称")
    relation_type: str = Field(..., description="关系类型")


class GraphRAGResult(BaseModel):
    """图谱 RAG 结果

    扩展的结果模型，包含结构化的实体和关系信息。

    Attributes:
        entities: 检索到的实体列表
        relations: 检索到的关系列表
        raw_response: 原始响应文本
    """

    entities: list[EntityInfo] = Field(default_factory=list, description="实体列表")
    relations: list[RelationInfo] = Field(default_factory=list, description="关系列表")
    raw_response: str = Field(default="", description="原始响应文本")


class GraphRAG(RAGInterface):
    """基于知识图谱的 RAG 检索工具

    使用 LlamaIndex KnowledgeGraphIndex 构建图谱索引，
    使用 Neo4j 作为图数据库后端。

    Attributes:
        graph_store: Neo4j 图存储实例
        index: 知识图谱索引实例
        query_timeout: 查询超时时间（秒）
        max_triplets_per_chunk: 每个块的最大三元组数量

    Example:
        >>> graph_rag = GraphRAG(
        ...     neo4j_uri="bolt://localhost:7687",
        ...     neo4j_user="neo4j",
        ...     neo4j_password="password"
        ... )
        >>> await graph_rag.build_index(documents)
        >>> results = await graph_rag.query("压力与免疫系统的关系")
    """

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        database: str = "neo4j",
        query_timeout: int = 10,
        max_triplets_per_chunk: int = 10,
    ):
        """初始化 Graph RAG 工具

        Args:
            neo4j_uri: Neo4j 数据库连接 URI（如 bolt://localhost:7687）
            neo4j_user: Neo4j 用户名
            neo4j_password: Neo4j 密码
            database: Neo4j 数据库名称，默认 "neo4j"
            query_timeout: 查询超时时间（秒），默认 10 秒
            max_triplets_per_chunk: 每个文档块提取的最大三元组数量，默认 10
        """
        self._neo4j_uri = neo4j_uri
        self._neo4j_user = neo4j_user
        self._neo4j_password = neo4j_password
        self._database = database
        self.query_timeout = query_timeout
        self.max_triplets_per_chunk = max_triplets_per_chunk

        # 延迟初始化
        self._graph_store: Neo4jGraphStore | None = None
        self._index: KnowledgeGraphIndex | None = None
        self._initialized = False

    def _lazy_init(self) -> None:
        """延迟初始化 Neo4j 连接

        仅在首次需要时初始化连接，支持测试时跳过实际连接。

        Raises:
            ImportError: 未安装 llama-index-graph-stores-neo4j
            RAGQueryError: Neo4j 连接失败
        """
        if self._initialized:
            return

        try:
            from llama_index.graph_stores.neo4j import Neo4jGraphStore
        except ImportError as e:
            raise ImportError(
                "请安装 llama-index-graph-stores-neo4j: pip install llama-index-graph-stores-neo4j"
            ) from e

        try:
            self._graph_store = Neo4jGraphStore(
                url=self._neo4j_uri,
                username=self._neo4j_user,
                password=self._neo4j_password,
                database=self._database,
            )
            self._initialized = True
        except Exception as e:
            raise RAGQueryError(
                rag_type="Graph RAG",
                original_error=f"Neo4j 连接失败: {str(e)}",
            ) from e

    @property
    def graph_store(self) -> Neo4jGraphStore | None:
        """获取图存储实例"""
        return self._graph_store

    @graph_store.setter
    def graph_store(self, value: Neo4jGraphStore) -> None:
        """设置图存储实例（用于测试注入）"""
        self._graph_store = value
        self._initialized = True

    @property
    def index(self) -> KnowledgeGraphIndex | None:
        """获取知识图谱索引"""
        return self._index

    @index.setter
    def index(self, value: KnowledgeGraphIndex) -> None:
        """设置索引（用于测试注入）"""
        self._index = value

    async def build_index(self, documents: list[Document]) -> None:
        """构建知识图谱索引

        从文档中提取实体和关系，构建知识图谱索引。

        Args:
            documents: LlamaIndex Document 对象列表

        Raises:
            ImportError: 未安装 llama-index
            RAGQueryError: 索引构建失败
        """
        self._lazy_init()

        try:
            from llama_index.core import KnowledgeGraphIndex
        except ImportError as e:
            raise ImportError("请安装 llama-index: pip install llama-index") from e

        if not documents:
            self._index = None
            return

        try:
            # 使用线程池执行同步的索引构建操作
            loop = asyncio.get_event_loop()
            self._index = await loop.run_in_executor(
                None,
                lambda: KnowledgeGraphIndex.from_documents(
                    documents,
                    graph_store=self._graph_store,
                    max_triplets_per_chunk=self.max_triplets_per_chunk,
                    include_embeddings=True,
                ),
            )
        except Exception as e:
            raise RAGQueryError(
                rag_type="Graph RAG",
                original_error=f"索引构建失败: {str(e)}",
            ) from e

    async def query(
        self,
        query_text: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        max_hops: int = 3,
    ) -> list[RAGResult]:
        """执行图谱检索查询

        支持多跳关系查询，返回相关实体和关系信息。

        Args:
            query_text: 查询文本
            top_k: 返回的最大结果数量，范围 1-20，默认 5
            similarity_threshold: 相似度阈值，范围 0.0-1.0，默认 0.7
            max_hops: 最大跳数，范围 1-3，默认 3

        Returns:
            RAGResult 列表，包含检索到的知识图谱信息

        Raises:
            RAGQueryError: 查询失败或超时
        """
        # 如果索引未构建，返回空结果
        if self._index is None:
            return [
                RAGResult(
                    content="",
                    source="knowledge_graph",
                    similarity_score=0.0,
                    metadata={
                        "error_type": "index_not_built",
                        "error_message": "知识图谱索引未构建",
                    },
                )
            ]

        # 参数范围校验
        top_k = max(1, min(20, top_k))
        similarity_threshold = max(0.0, min(1.0, similarity_threshold))
        max_hops = max(1, min(3, max_hops))  # 限制最大跳数为 3

        try:
            # 配置查询引擎
            query_engine = self._index.as_query_engine(
                include_text=True,
                response_mode="tree_summarize",
                similarity_top_k=top_k,
            )

            # 使用 asyncio.wait_for 实现超时控制
            async def execute_query():
                """执行查询的包装函数"""
                # 检查是否有真正可用的异步查询方法
                aquery_method = getattr(query_engine, "aquery", None)
                if aquery_method is not None and callable(aquery_method):
                    try:
                        return await aquery_method(query_text)
                    except TypeError:
                        # 如果 aquery 不是真正的协程，回退到同步方法
                        pass

                # 在线程池中执行同步方法
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, query_engine.query, query_text)

            response = await asyncio.wait_for(
                execute_query(),
                timeout=self.query_timeout,
            )

            # 解析图谱结果，提取实体和关系
            entities: list[EntityInfo] = []
            relations: list[RelationInfo] = []

            # 从响应的 source_nodes 中提取结构化信息
            if hasattr(response, "source_nodes"):
                for node in response.source_nodes:
                    # 检查节点相似度（如果有）
                    node_score = getattr(node, "score", 1.0)
                    if node_score is not None and node_score < similarity_threshold:
                        continue

                    node_metadata = getattr(node, "metadata", {})

                    # 提取实体信息
                    if "entity" in node_metadata:
                        entities.append(
                            EntityInfo(
                                name=node_metadata["entity"],
                                type=node_metadata.get("type", "unknown"),
                                properties=node_metadata.get("properties", {}),
                            )
                        )

                    # 提取关系信息
                    if "relation" in node_metadata:
                        relations.append(
                            RelationInfo(
                                source_entity=node_metadata.get("source", ""),
                                target_entity=node_metadata.get("target", ""),
                                relation_type=node_metadata["relation"],
                            )
                        )

                    # 尝试从三元组格式提取
                    if "triplet" in node_metadata:
                        triplet = node_metadata["triplet"]
                        if isinstance(triplet, (list, tuple)) and len(triplet) >= 3:
                            source, relation, target = triplet[0], triplet[1], triplet[2]
                            entities.append(EntityInfo(name=source, type="extracted"))
                            entities.append(EntityInfo(name=target, type="extracted"))
                            relations.append(
                                RelationInfo(
                                    source_entity=source,
                                    target_entity=target,
                                    relation_type=relation,
                                )
                            )

            # 去重实体
            seen_entities: set[str] = set()
            unique_entities: list[EntityInfo] = []
            for entity in entities:
                if entity.name not in seen_entities:
                    seen_entities.add(entity.name)
                    unique_entities.append(entity)

            # 去重关系
            seen_relations: set[tuple[str, str, str]] = set()
            unique_relations: list[RelationInfo] = []
            for rel in relations:
                key = (rel.source_entity, rel.target_entity, rel.relation_type)
                if key not in seen_relations:
                    seen_relations.add(key)
                    unique_relations.append(rel)

            # 构建结构化结果
            graph_result = GraphRAGResult(
                entities=unique_entities,
                relations=unique_relations,
                raw_response=str(response),
            )

            return [
                RAGResult(
                    content=str(response),
                    source="knowledge_graph",
                    similarity_score=1.0,
                    metadata={
                        "entities": [e.model_dump() for e in unique_entities],
                        "relations": [r.model_dump() for r in unique_relations],
                        "max_hops": max_hops,
                        "graph_result": graph_result.model_dump(),
                    },
                )
            ]

        except TimeoutError:
            # 超时错误处理 (Requirement 12.6, 12.7)
            return [
                RAGResult(
                    content="",
                    source="error",
                    similarity_score=0.0,
                    metadata={
                        "error_type": "timeout",
                        "error_message": f"查询超时 ({self.query_timeout}秒)",
                    },
                )
            ]
        except Exception as e:
            # 其他错误处理
            return [
                RAGResult(
                    content="",
                    source="error",
                    similarity_score=0.0,
                    metadata={
                        "error_type": "query_error",
                        "error_message": str(e),
                    },
                )
            ]

    async def health_check(self) -> bool:
        """检查 Neo4j 连接健康状态

        验证与 Neo4j 数据库的连接是否正常。

        Returns:
            True 表示连接正常，False 表示连接异常
        """
        try:
            self._lazy_init()

            if self._graph_store is None:
                return False

            # 尝试获取驱动并验证连接
            driver = getattr(self._graph_store, "_driver", None)
            if driver is None:
                return False

            # 执行连接验证
            driver.verify_connectivity()
            return True

        except Exception:
            return False

    async def get_graph_stats(self) -> dict[str, Any]:
        """获取图数据库统计信息

        返回图数据库中的节点数、关系数等统计信息。

        Returns:
            包含统计信息的字典
        """
        if not self._initialized or self._graph_store is None:
            return {"error": "Graph store not initialized"}

        try:
            driver = getattr(self._graph_store, "_driver", None)
            if driver is None:
                return {"error": "Driver not available"}

            # 执行统计查询
            with driver.session(database=self._database) as session:
                # 获取节点数
                node_result = session.run("MATCH (n) RETURN count(n) as count")
                node_count = node_result.single()["count"]

                # 获取关系数
                rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                rel_count = rel_result.single()["count"]

                return {
                    "node_count": node_count,
                    "relationship_count": rel_count,
                    "database": self._database,
                }
        except Exception as e:
            return {"error": str(e)}

    def close(self) -> None:
        """关闭 Neo4j 连接

        释放数据库连接资源。
        """
        if self._graph_store is not None:
            try:
                driver = getattr(self._graph_store, "_driver", None)
                if driver is not None:
                    driver.close()
            except Exception:
                pass
            finally:
                self._graph_store = None
                self._index = None
                self._initialized = False
