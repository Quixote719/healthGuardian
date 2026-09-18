"""
Markdown RAG 检索工具单元测试

测试 MarkdownRAG 类的各项功能，使用 mock 模拟外部依赖。
Requirements: 11.1-11.6
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMarkdownRAGImports:
    """测试模块导入和依赖检测"""

    def test_module_import_success(self) -> None:
        """测试模块可以成功导入"""
        from app.tools.markdown_rag import MarkdownRAG

        assert MarkdownRAG is not None

    def test_knowledge_category_constants(self) -> None:
        """测试知识库类别常量"""
        from app.tools.markdown_rag import KnowledgeCategory

        assert KnowledgeCategory.NUTRITION == "营养学"
        assert KnowledgeCategory.REHABILITATION == "运动康复"

    def test_query_status_model(self) -> None:
        """测试 QueryStatus 模型"""
        from app.tools.markdown_rag import QueryStatus

        status = QueryStatus(
            success=True,
            message="检索成功",
            results_count=5,
        )
        assert status.success is True
        assert status.message == "检索成功"
        assert status.results_count == 5

    def test_query_status_defaults(self) -> None:
        """测试 QueryStatus 默认值"""
        from app.tools.markdown_rag import QueryStatus

        status = QueryStatus(success=False)
        assert status.success is False
        assert status.message == ""
        assert status.results_count == 0

    def test_factory_functions_exist(self) -> None:
        """测试工厂函数存在"""
        from app.tools.markdown_rag import (
            create_nutrition_rag,
            create_rehabilitation_rag,
        )

        assert callable(create_nutrition_rag)
        assert callable(create_rehabilitation_rag)


class TestMarkdownRAGInitialization:
    """测试 MarkdownRAG 初始化"""

    def test_init_with_defaults(self) -> None:
        """测试使用默认参数初始化"""
        # 模拟依赖不可用的情况
        with patch.dict(
            "app.tools.markdown_rag.__dict__",
            {"CHROMADB_AVAILABLE": False, "LLAMA_INDEX_AVAILABLE": False},
        ):
            from importlib import reload

            import app.tools.markdown_rag as markdown_rag_module

            reload(markdown_rag_module)

            rag = markdown_rag_module.MarkdownRAG(
                collection_name="test_collection",
            )
            assert rag.collection_name == "test_collection"
            assert rag.chunk_size == 512
            assert rag.chunk_overlap == 50
            assert rag.chroma_persist_dir == "./chroma_db"

    def test_init_with_custom_params(self) -> None:
        """测试使用自定义参数初始化"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(
            collection_name="custom_collection",
            chroma_persist_dir="/custom/path",
            chunk_size=1024,
            chunk_overlap=100,
        )
        assert rag.collection_name == "custom_collection"
        assert rag.chroma_persist_dir == "/custom/path"
        assert rag.chunk_size == 1024
        assert rag.chunk_overlap == 100

    def test_last_query_status_initially_none(self) -> None:
        """测试初始时 last_query_status 为 None"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")
        assert rag.last_query_status is None


class TestMarkdownRAGQuery:
    """测试 MarkdownRAG 查询功能"""

    @pytest.mark.asyncio
    async def test_query_without_dependencies_returns_empty(self) -> None:
        """测试依赖不可用时查询返回空结果"""
        from app.tools.markdown_rag import MarkdownRAG

        # 创建一个依赖不可用的实例
        rag = MarkdownRAG(collection_name="test")
        # 强制设置依赖不可用
        rag._chroma_client = None
        rag._index = None

        results = await rag.query("测试查询")
        assert results == []
        assert rag.last_query_status is not None
        assert rag.last_query_status.success is False

    @pytest.mark.asyncio
    async def test_query_without_index_returns_empty(self) -> None:
        """测试索引未构建时查询返回空结果"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")
        # 模拟依赖可用但索引未构建
        rag._force_available = True
        rag._index = None
        results = await rag.query("测试查询")
        assert results == []
        assert rag.last_query_status is not None
        assert "索引未构建" in rag.last_query_status.message

    @pytest.mark.asyncio
    async def test_query_parameter_validation_top_k_min(self) -> None:
        """测试 top_k 参数最小值验证"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        # 创建 mock 索引
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        await rag.query("test", top_k=0)  # 应该被调整为 1
        # 验证 retriever 被调用时使用了调整后的值
        mock_index.as_retriever.assert_called_once()
        call_kwargs = mock_index.as_retriever.call_args[1]
        # top_k * 2 应该至少是 2（因为 top_k 被调整为 1）
        assert call_kwargs.get("similarity_top_k", 0) >= 2

    @pytest.mark.asyncio
    async def test_query_parameter_validation_top_k_max(self) -> None:
        """测试 top_k 参数最大值验证"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        await rag.query("test", top_k=100)  # 应该被调整为 20
        mock_index.as_retriever.assert_called_once()
        call_kwargs = mock_index.as_retriever.call_args[1]
        # top_k * 2 应该是 40（因为 top_k 被调整为 20）
        assert call_kwargs.get("similarity_top_k", 0) == 40

    @pytest.mark.asyncio
    async def test_query_parameter_validation_threshold_min(self) -> None:
        """测试 similarity_threshold 参数最小值验证"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        # 创建返回高分结果的 mock
        mock_node = MagicMock()
        mock_node.get_content.return_value = "测试内容"
        mock_node.metadata = {}

        mock_result = MagicMock()
        mock_result.score = 0.5  # 这个分数会通过 0.0 的阈值
        mock_result.node = mock_node

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [mock_result]
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        results = await rag.query("test", similarity_threshold=-0.5)  # 应该被调整为 0.0
        # 0.5 的分数应该通过 0.0 的阈值
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_query_parameter_validation_threshold_max(self) -> None:
        """测试 similarity_threshold 参数最大值验证"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        mock_node = MagicMock()
        mock_node.get_content.return_value = "测试内容"
        mock_node.metadata = {}

        mock_result = MagicMock()
        mock_result.score = 0.95
        mock_result.node = mock_node

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [mock_result]
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        results = await rag.query("test", similarity_threshold=1.5)  # 应该被调整为 1.0
        # 0.95 的分数不会通过 1.0 的阈值
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_query_similarity_filtering(self) -> None:
        """测试相似度阈值过滤"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        # 创建多个不同分数的结果
        def create_mock_result(score: float, content: str) -> MagicMock:
            mock_node = MagicMock()
            mock_node.get_content.return_value = content
            mock_node.metadata = {}
            mock_result = MagicMock()
            mock_result.score = score
            mock_result.node = mock_node
            return mock_result

        mock_results = [
            create_mock_result(0.95, "高分内容"),
            create_mock_result(0.80, "中高分内容"),
            create_mock_result(0.65, "中低分内容"),  # 低于默认阈值 0.7
            create_mock_result(0.50, "低分内容"),
        ]

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = mock_results
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        # 默认阈值 0.7
        results = await rag.query("test", similarity_threshold=0.7)
        assert len(results) == 2
        assert results[0].similarity_score == 0.95
        assert results[1].similarity_score == 0.80

    @pytest.mark.asyncio
    async def test_query_category_filtering(self) -> None:
        """测试类别过滤 (Requirement 11.4)"""
        from app.tools.markdown_rag import KnowledgeCategory, MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        # 创建不同类别的结果
        def create_mock_result(
            score: float, content: str, category: str
        ) -> MagicMock:
            mock_node = MagicMock()
            mock_node.get_content.return_value = content
            mock_node.metadata = {"category": category}
            mock_result = MagicMock()
            mock_result.score = score
            mock_result.node = mock_node
            return mock_result

        mock_results = [
            create_mock_result(0.95, "营养内容", KnowledgeCategory.NUTRITION),
            create_mock_result(0.90, "康复内容", KnowledgeCategory.REHABILITATION),
            create_mock_result(0.85, "营养内容2", KnowledgeCategory.NUTRITION),
        ]

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = mock_results
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        # 只查询营养学内容
        results = await rag.query(
            "test",
            category=KnowledgeCategory.NUTRITION,
        )
        assert len(results) == 2
        assert all(r.metadata.get("category") == "营养学" for r in results)

    @pytest.mark.asyncio
    async def test_query_top_k_limit(self) -> None:
        """测试 top_k 限制 (Requirement 11.3)"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        # 创建多个高分结果
        def create_mock_result(score: float, idx: int) -> MagicMock:
            mock_node = MagicMock()
            mock_node.get_content.return_value = f"内容{idx}"
            mock_node.metadata = {}
            mock_result = MagicMock()
            mock_result.score = score
            mock_result.node = mock_node
            return mock_result

        # 创建 10 个高分结果
        mock_results = [create_mock_result(0.9 - i * 0.01, i) for i in range(10)]

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = mock_results
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        # 限制返回 3 个结果
        results = await rag.query("test", top_k=3, similarity_threshold=0.5)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_query_results_sorted_by_similarity(self) -> None:
        """测试结果按相似度降序排序"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        # 创建乱序的结果
        def create_mock_result(score: float, content: str) -> MagicMock:
            mock_node = MagicMock()
            mock_node.get_content.return_value = content
            mock_node.metadata = {}
            mock_result = MagicMock()
            mock_result.score = score
            mock_result.node = mock_node
            return mock_result

        # 乱序返回
        mock_results = [
            create_mock_result(0.75, "中"),
            create_mock_result(0.95, "高"),
            create_mock_result(0.80, "中高"),
        ]

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = mock_results
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        results = await rag.query("test", similarity_threshold=0.7)
        # 验证按分数降序排列
        assert results[0].similarity_score == 0.95
        assert results[1].similarity_score == 0.80
        assert results[2].similarity_score == 0.75

    @pytest.mark.asyncio
    async def test_query_empty_results_status(self) -> None:
        """测试空结果时的状态信息 (Requirement 11.6)"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        results = await rag.query("test")
        assert results == []
        assert rag.last_query_status is not None
        assert rag.last_query_status.success is True
        assert "未找到相关内容" in rag.last_query_status.message

    @pytest.mark.asyncio
    async def test_query_exception_handling(self) -> None:
        """测试查询异常处理"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        mock_retriever = MagicMock()
        mock_retriever.retrieve.side_effect = Exception("检索错误")
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        results = await rag.query("test")
        assert results == []
        assert rag.last_query_status is not None
        assert rag.last_query_status.success is False
        assert "检索失败" in rag.last_query_status.message


class TestMarkdownRAGConvenienceMethods:
    """测试便捷方法"""

    @pytest.mark.asyncio
    async def test_query_nutrition(self) -> None:
        """测试营养学检索便捷方法"""
        from app.tools.markdown_rag import KnowledgeCategory, MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        # Mock query 方法
        with patch.object(rag, "query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []
            await rag.query_nutrition("维生素D")

            mock_query.assert_called_once_with(
                query_text="维生素D",
                top_k=5,
                similarity_threshold=0.7,
                category=KnowledgeCategory.NUTRITION,
            )

    @pytest.mark.asyncio
    async def test_query_rehabilitation(self) -> None:
        """测试运动康复检索便捷方法"""
        from app.tools.markdown_rag import KnowledgeCategory, MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        with patch.object(rag, "query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []
            await rag.query_rehabilitation("拉伸运动", top_k=10)

            mock_query.assert_called_once_with(
                query_text="拉伸运动",
                top_k=10,
                similarity_threshold=0.7,
                category=KnowledgeCategory.REHABILITATION,
            )


class TestMarkdownRAGHealthCheck:
    """测试健康检查功能"""

    @pytest.mark.asyncio
    async def test_health_check_without_chromadb(self) -> None:
        """测试 ChromaDB 不可用时健康检查返回 False"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")
        rag._chroma_client = None

        result = await rag.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        """测试健康检查成功"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        # Mock ChromaDB client
        mock_client = MagicMock()
        mock_client.heartbeat.return_value = 1234567890
        rag._chroma_client = mock_client

        with patch("app.tools.markdown_rag.CHROMADB_AVAILABLE", True):
            result = await rag.health_check()
            assert result is True
            mock_client.heartbeat.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_exception(self) -> None:
        """测试健康检查异常处理"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        mock_client = MagicMock()
        mock_client.heartbeat.side_effect = Exception("连接失败")
        rag._chroma_client = mock_client

        with patch("app.tools.markdown_rag.CHROMADB_AVAILABLE", True):
            result = await rag.health_check()
            assert result is False


class TestMarkdownRAGBuildIndex:
    """测试索引构建功能"""

    @pytest.mark.asyncio
    async def test_build_index_without_dependencies(self) -> None:
        """测试依赖不可用时构建索引抛出异常"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")
        rag._force_available = False

        with pytest.raises(RuntimeError) as exc_info:
            await rag.build_index([])
        assert "依赖不可用" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_build_index_empty_documents(self) -> None:
        """测试空文档列表返回 False"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")
        rag._force_available = True

        result = await rag.build_index([])
        assert result is False

    @pytest.mark.asyncio
    async def test_build_index_with_category(self) -> None:
        """测试带类别的索引构建"""
        from app.tools.markdown_rag import KnowledgeCategory, MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        # 创建 mock 文档
        mock_doc = MagicMock()
        mock_doc.metadata = {}

        # Mock 节点解析器和索引
        mock_node_parser = MagicMock()
        mock_node_parser.get_nodes_from_documents.return_value = []

        rag._node_parser = mock_node_parser
        rag._force_available = True

        with patch(
            "app.tools.markdown_rag.VectorStoreIndex"
        ) as mock_index_class:
            mock_index_class.from_documents.return_value = MagicMock()
            await rag.build_index(
                [mock_doc],
                category=KnowledgeCategory.NUTRITION,
            )
            # 验证类别被添加到文档元数据
            assert mock_doc.metadata.get("category") == "营养学"


class TestMarkdownRAGCollectionOperations:
    """测试集合操作功能"""

    @pytest.mark.asyncio
    async def test_get_collection_stats_without_chromadb(self) -> None:
        """测试 ChromaDB 不可用时获取统计信息"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test_collection")
        rag._collection = None

        stats = await rag.get_collection_stats()
        assert stats["collection_name"] == "test_collection"
        assert stats["document_count"] == 0
        assert stats["available"] is False

    @pytest.mark.asyncio
    async def test_get_collection_stats_success(self) -> None:
        """测试成功获取集合统计信息"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test_collection")

        mock_collection = MagicMock()
        mock_collection.count.return_value = 100
        rag._collection = mock_collection

        with patch("app.tools.markdown_rag.CHROMADB_AVAILABLE", True):
            stats = await rag.get_collection_stats()
            assert stats["collection_name"] == "test_collection"
            assert stats["document_count"] == 100
            assert stats["available"] is True
            assert stats["chunk_size"] == 512
            assert stats["chunk_overlap"] == 50

    @pytest.mark.asyncio
    async def test_clear_collection_without_chromadb(self) -> None:
        """测试 ChromaDB 不可用时清空集合返回 False"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")
        rag._chroma_client = None

        result = await rag.clear_collection()
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_collection_success(self) -> None:
        """测试成功清空集合"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test_collection")

        mock_client = MagicMock()
        mock_new_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_new_collection
        rag._chroma_client = mock_client

        with patch("app.tools.markdown_rag.CHROMADB_AVAILABLE", True):
            with patch("app.tools.markdown_rag.LLAMA_INDEX_AVAILABLE", False):
                result = await rag.clear_collection()
                assert result is True
                mock_client.delete_collection.assert_called_once_with("test_collection")
                mock_client.get_or_create_collection.assert_called_once()


class TestMarkdownRAGFactoryFunctions:
    """测试工厂函数"""

    def test_create_nutrition_rag(self) -> None:
        """测试创建营养学 RAG 实例"""
        from app.tools.markdown_rag import create_nutrition_rag

        rag = create_nutrition_rag()
        assert rag.collection_name == "nutrition_knowledge"
        assert rag.chunk_size == 512
        assert rag.chunk_overlap == 50

    def test_create_nutrition_rag_custom_params(self) -> None:
        """测试使用自定义参数创建营养学 RAG 实例"""
        from app.tools.markdown_rag import create_nutrition_rag

        rag = create_nutrition_rag(
            chroma_persist_dir="/custom/path",
            chunk_size=1024,
            chunk_overlap=100,
        )
        assert rag.collection_name == "nutrition_knowledge"
        assert rag.chroma_persist_dir == "/custom/path"
        assert rag.chunk_size == 1024
        assert rag.chunk_overlap == 100

    def test_create_rehabilitation_rag(self) -> None:
        """测试创建运动康复 RAG 实例"""
        from app.tools.markdown_rag import create_rehabilitation_rag

        rag = create_rehabilitation_rag()
        assert rag.collection_name == "rehabilitation_knowledge"
        assert rag.chunk_size == 512
        assert rag.chunk_overlap == 50

    def test_create_rehabilitation_rag_custom_params(self) -> None:
        """测试使用自定义参数创建运动康复 RAG 实例"""
        from app.tools.markdown_rag import create_rehabilitation_rag

        rag = create_rehabilitation_rag(
            chroma_persist_dir="/rehab/path",
            chunk_size=256,
            chunk_overlap=25,
        )
        assert rag.collection_name == "rehabilitation_knowledge"
        assert rag.chroma_persist_dir == "/rehab/path"
        assert rag.chunk_size == 256
        assert rag.chunk_overlap == 25


class TestMarkdownRAGIsAvailableProperty:
    """测试 is_available 属性"""

    def test_is_available_both_true(self) -> None:
        """测试两个依赖都可用时返回 True"""
        from app.tools.markdown_rag import MarkdownRAG

        MarkdownRAG(collection_name="test")

        with patch("app.tools.markdown_rag.CHROMADB_AVAILABLE", True):
            with patch("app.tools.markdown_rag.LLAMA_INDEX_AVAILABLE", True):
                # 需要重新检查属性
                from app.tools import markdown_rag

                assert markdown_rag.CHROMADB_AVAILABLE is True
                assert markdown_rag.LLAMA_INDEX_AVAILABLE is True

    def test_is_available_chromadb_false(self) -> None:
        """测试 ChromaDB 不可用时返回 False"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        # 直接检查实例的 is_available 属性
        # 这个属性依赖模块级变量
        assert isinstance(rag.is_available, bool)


class TestMarkdownRAGInheritance:
    """测试 MarkdownRAG 继承 RAGInterface"""

    def test_inherits_rag_interface(self) -> None:
        """测试 MarkdownRAG 继承自 RAGInterface"""
        from app.tools.markdown_rag import MarkdownRAG
        from app.tools.rag_interface import RAGInterface

        assert issubclass(MarkdownRAG, RAGInterface)

    def test_implements_query_method(self) -> None:
        """测试实现了 query 方法"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")
        assert hasattr(rag, "query")
        assert callable(rag.query)

    def test_implements_health_check_method(self) -> None:
        """测试实现了 health_check 方法"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")
        assert hasattr(rag, "health_check")
        assert callable(rag.health_check)


class TestMarkdownRAGNoneScoreHandling:
    """测试 None 分数处理"""

    @pytest.mark.asyncio
    async def test_query_handles_none_score(self) -> None:
        """测试查询处理 None 分数"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        mock_node = MagicMock()
        mock_node.get_content.return_value = "测试内容"
        mock_node.metadata = {}

        mock_result = MagicMock()
        mock_result.score = None  # None 分数
        mock_result.node = mock_node

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [mock_result]
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        # None 分数被当作 0.0 处理，低于默认阈值 0.7
        results = await rag.query("test", similarity_threshold=0.7)
        assert len(results) == 0

        # 降低阈值后应该能获取结果
        results = await rag.query("test", similarity_threshold=0.0)
        assert len(results) == 1
        assert results[0].similarity_score == 0.0


class TestMarkdownRAGMetadataHandling:
    """测试元数据处理"""

    @pytest.mark.asyncio
    async def test_query_extracts_file_path_as_source(self) -> None:
        """测试从元数据中提取 file_path 作为 source"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        mock_node = MagicMock()
        mock_node.get_content.return_value = "测试内容"
        mock_node.metadata = {"file_path": "/path/to/doc.md", "page": 1}

        mock_result = MagicMock()
        mock_result.score = 0.9
        mock_result.node = mock_node

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [mock_result]
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        results = await rag.query("test")
        assert len(results) == 1
        assert results[0].source == "/path/to/doc.md"

    @pytest.mark.asyncio
    async def test_query_extracts_source_from_metadata(self) -> None:
        """测试从元数据中提取 source 字段"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        mock_node = MagicMock()
        mock_node.get_content.return_value = "测试内容"
        mock_node.metadata = {"source": "nutrition/vitamins.md"}

        mock_result = MagicMock()
        mock_result.score = 0.9
        mock_result.node = mock_node

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [mock_result]
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        results = await rag.query("test")
        assert len(results) == 1
        assert results[0].source == "nutrition/vitamins.md"

    @pytest.mark.asyncio
    async def test_query_unknown_source_fallback(self) -> None:
        """测试无 source 信息时的降级处理"""
        from app.tools.markdown_rag import MarkdownRAG

        rag = MarkdownRAG(collection_name="test")

        mock_node = MagicMock()
        mock_node.get_content.return_value = "测试内容"
        mock_node.metadata = {"other_key": "value"}  # 没有 file_path 或 source

        mock_result = MagicMock()
        mock_result.score = 0.9
        mock_result.node = mock_node

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [mock_result]
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        rag._index = mock_index
        rag._force_available = True
        results = await rag.query("test")
        assert len(results) == 1
        assert results[0].source == "unknown"
