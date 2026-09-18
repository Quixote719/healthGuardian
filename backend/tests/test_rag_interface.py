"""
RAG 接口基类单元测试

测试 RAGResult 数据模型和 RAGInterface 抽象基类
Requirements: 11.3, 12.3
"""


import pytest
from pydantic import ValidationError

from app.tools.rag_interface import RAGInterface, RAGResult


class TestRAGResult:
    """RAGResult 数据模型测试"""

    def test_valid_rag_result_minimal(self) -> None:
        """测试最小有效 RAGResult"""
        result = RAGResult(
            content="测试内容",
            source="test_source.md",
            similarity_score=0.85,
        )
        assert result.content == "测试内容"
        assert result.source == "test_source.md"
        assert result.similarity_score == 0.85
        assert result.metadata == {}

    def test_valid_rag_result_with_metadata(self) -> None:
        """测试带元数据的 RAGResult"""
        metadata = {"category": "营养学", "page": 5, "section": "vitamins"}
        result = RAGResult(
            content="维生素D有助于钙吸收",
            source="nutrition/vitamins.md",
            similarity_score=0.92,
            metadata=metadata,
        )
        assert result.content == "维生素D有助于钙吸收"
        assert result.source == "nutrition/vitamins.md"
        assert result.similarity_score == 0.92
        assert result.metadata == metadata
        assert result.metadata["category"] == "营养学"

    def test_similarity_score_boundary_zero(self) -> None:
        """测试相似度分数边界值 0.0"""
        result = RAGResult(
            content="低相似度内容",
            source="low_score.md",
            similarity_score=0.0,
        )
        assert result.similarity_score == 0.0

    def test_similarity_score_boundary_one(self) -> None:
        """测试相似度分数边界值 1.0"""
        result = RAGResult(
            content="高相似度内容",
            source="high_score.md",
            similarity_score=1.0,
        )
        assert result.similarity_score == 1.0

    def test_similarity_score_below_zero_raises_error(self) -> None:
        """测试相似度分数低于 0 时抛出验证错误"""
        with pytest.raises(ValidationError) as exc_info:
            RAGResult(
                content="无效内容",
                source="invalid.md",
                similarity_score=-0.1,
            )
        assert "similarity_score" in str(exc_info.value)

    def test_similarity_score_above_one_raises_error(self) -> None:
        """测试相似度分数高于 1 时抛出验证错误"""
        with pytest.raises(ValidationError) as exc_info:
            RAGResult(
                content="无效内容",
                source="invalid.md",
                similarity_score=1.5,
            )
        assert "similarity_score" in str(exc_info.value)

    def test_missing_required_field_content(self) -> None:
        """测试缺少 content 字段时抛出验证错误"""
        with pytest.raises(ValidationError) as exc_info:
            RAGResult(
                source="test.md",
                similarity_score=0.8,
            )  # type: ignore
        assert "content" in str(exc_info.value)

    def test_missing_required_field_source(self) -> None:
        """测试缺少 source 字段时抛出验证错误"""
        with pytest.raises(ValidationError) as exc_info:
            RAGResult(
                content="测试内容",
                similarity_score=0.8,
            )  # type: ignore
        assert "source" in str(exc_info.value)

    def test_missing_required_field_similarity_score(self) -> None:
        """测试缺少 similarity_score 字段时抛出验证错误"""
        with pytest.raises(ValidationError) as exc_info:
            RAGResult(
                content="测试内容",
                source="test.md",
            )  # type: ignore
        assert "similarity_score" in str(exc_info.value)

    def test_json_serialization(self) -> None:
        """测试 JSON 序列化"""
        result = RAGResult(
            content="测试内容",
            source="test.md",
            similarity_score=0.88,
            metadata={"key": "value"},
        )
        json_str = result.model_dump_json()
        assert "测试内容" in json_str
        assert "test.md" in json_str
        assert "0.88" in json_str

    def test_json_deserialization(self) -> None:
        """测试 JSON 反序列化"""
        json_data = {
            "content": "反序列化测试",
            "source": "deser.md",
            "similarity_score": 0.75,
            "metadata": {"test": True},
        }
        result = RAGResult.model_validate(json_data)
        assert result.content == "反序列化测试"
        assert result.source == "deser.md"
        assert result.similarity_score == 0.75
        assert result.metadata == {"test": True}

    def test_empty_content_allowed(self) -> None:
        """测试空内容是否允许"""
        result = RAGResult(
            content="",
            source="empty.md",
            similarity_score=0.5,
        )
        assert result.content == ""

    def test_complex_metadata(self) -> None:
        """测试复杂元数据结构"""
        metadata = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "mixed": {"items": ["a", "b"], "count": 2},
        }
        result = RAGResult(
            content="复杂元数据测试",
            source="complex.md",
            similarity_score=0.9,
            metadata=metadata,
        )
        assert result.metadata["nested"]["key"] == "value"
        assert result.metadata["list"] == [1, 2, 3]


class TestRAGInterface:
    """RAGInterface 抽象基类测试"""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """测试无法直接实例化抽象基类"""
        with pytest.raises(TypeError) as exc_info:
            RAGInterface()  # type: ignore
        assert "abstract" in str(exc_info.value).lower()

    def test_concrete_implementation_query_method(self) -> None:
        """测试具体实现必须提供 query 方法"""

        class IncompleteRAG(RAGInterface):
            async def health_check(self) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteRAG()  # type: ignore

    def test_concrete_implementation_health_check_method(self) -> None:
        """测试具体实现必须提供 health_check 方法"""

        class IncompleteRAG(RAGInterface):
            async def query(
                self,
                query_text: str,
                top_k: int = 5,
                similarity_threshold: float = 0.7,
            ) -> list[RAGResult]:
                return []

        with pytest.raises(TypeError):
            IncompleteRAG()  # type: ignore

    @pytest.mark.asyncio
    async def test_valid_concrete_implementation(self) -> None:
        """测试有效的具体实现"""

        class MockRAG(RAGInterface):
            async def query(
                self,
                query_text: str,
                top_k: int = 5,
                similarity_threshold: float = 0.7,
            ) -> list[RAGResult]:
                return [
                    RAGResult(
                        content=f"Result for: {query_text}",
                        source="mock.md",
                        similarity_score=0.9,
                    )
                ]

            async def health_check(self) -> bool:
                return True

        rag = MockRAG()
        # 测试 query 方法
        results = await rag.query("测试查询")
        assert len(results) == 1
        assert results[0].content == "Result for: 测试查询"
        assert results[0].similarity_score == 0.9

        # 测试 health_check 方法
        is_healthy = await rag.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_query_with_custom_parameters(self) -> None:
        """测试带自定义参数的查询"""

        class MockRAG(RAGInterface):
            def __init__(self) -> None:
                self.last_top_k: int = 0
                self.last_threshold: float = 0.0

            async def query(
                self,
                query_text: str,
                top_k: int = 5,
                similarity_threshold: float = 0.7,
            ) -> list[RAGResult]:
                self.last_top_k = top_k
                self.last_threshold = similarity_threshold
                return []

            async def health_check(self) -> bool:
                return True

        rag = MockRAG()
        await rag.query("测试", top_k=10, similarity_threshold=0.85)
        assert rag.last_top_k == 10
        assert rag.last_threshold == 0.85

    @pytest.mark.asyncio
    async def test_query_returns_empty_list(self) -> None:
        """测试查询返回空结果"""

        class EmptyRAG(RAGInterface):
            async def query(
                self,
                query_text: str,
                top_k: int = 5,
                similarity_threshold: float = 0.7,
            ) -> list[RAGResult]:
                return []

            async def health_check(self) -> bool:
                return True

        rag = EmptyRAG()
        results = await rag.query("无匹配查询")
        assert results == []
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_health_check_returns_false(self) -> None:
        """测试健康检查返回 False"""

        class UnhealthyRAG(RAGInterface):
            async def query(
                self,
                query_text: str,
                top_k: int = 5,
                similarity_threshold: float = 0.7,
            ) -> list[RAGResult]:
                return []

            async def health_check(self) -> bool:
                return False

        rag = UnhealthyRAG()
        is_healthy = await rag.health_check()
        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_multiple_results_sorted_by_similarity(self) -> None:
        """测试多个结果按相似度排序"""

        class SortedRAG(RAGInterface):
            async def query(
                self,
                query_text: str,
                top_k: int = 5,
                similarity_threshold: float = 0.7,
            ) -> list[RAGResult]:
                # 返回按相似度降序排列的结果
                return [
                    RAGResult(content="高分", source="1.md", similarity_score=0.95),
                    RAGResult(content="中分", source="2.md", similarity_score=0.85),
                    RAGResult(content="低分", source="3.md", similarity_score=0.75),
                ]

            async def health_check(self) -> bool:
                return True

        rag = SortedRAG()
        results = await rag.query("测试")
        assert len(results) == 3
        assert results[0].similarity_score == 0.95
        assert results[1].similarity_score == 0.85
        assert results[2].similarity_score == 0.75

    def test_rag_interface_is_abstract(self) -> None:
        """验证 RAGInterface 是抽象类"""
        import inspect

        assert inspect.isabstract(RAGInterface)

    def test_query_method_is_abstract(self) -> None:
        """验证 query 方法是抽象方法"""

        assert "query" in RAGInterface.__abstractmethods__

    def test_health_check_method_is_abstract(self) -> None:
        """验证 health_check 方法是抽象方法"""

        assert "health_check" in RAGInterface.__abstractmethods__
