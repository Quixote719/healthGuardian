"""
FastAPI 应用入口测试
Tests for app/main.py

Requirements: 13.1, 14.11
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app import __version__


@pytest.fixture
async def async_client():
    """创建异步测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHealthEndpoint:
    """健康检查端点测试"""
    
    @pytest.mark.asyncio
    async def test_health_check_returns_200(self, async_client: AsyncClient):
        """测试健康检查端点返回 200 状态码"""
        response = await async_client.get("/health")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_health_check_response_structure(self, async_client: AsyncClient):
        """测试健康检查端点响应结构"""
        response = await async_client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "service" in data
    
    @pytest.mark.asyncio
    async def test_health_check_status_is_healthy(self, async_client: AsyncClient):
        """测试健康检查状态为 healthy"""
        response = await async_client.get("/health")
        data = response.json()
        
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_version_matches(self, async_client: AsyncClient):
        """测试健康检查版本与应用版本一致"""
        response = await async_client.get("/health")
        data = response.json()
        
        assert data["version"] == __version__
    
    @pytest.mark.asyncio
    async def test_health_check_service_name(self, async_client: AsyncClient):
        """测试健康检查服务名称正确"""
        response = await async_client.get("/health")
        data = response.json()
        
        assert data["service"] == "health-longevity-multi-agent-system"


class TestRootEndpoint:
    """根路径端点测试"""
    
    @pytest.mark.asyncio
    async def test_root_returns_200(self, async_client: AsyncClient):
        """测试根路径端点返回 200 状态码"""
        response = await async_client.get("/")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_root_response_structure(self, async_client: AsyncClient):
        """测试根路径端点响应结构"""
        response = await async_client.get("/")
        data = response.json()
        
        assert "message" in data
        assert "version" in data
        assert "docs" in data
    
    @pytest.mark.asyncio
    async def test_root_welcome_message(self, async_client: AsyncClient):
        """测试根路径欢迎消息"""
        response = await async_client.get("/")
        data = response.json()
        
        assert "Health Longevity Multi-Agent System" in data["message"]
    
    @pytest.mark.asyncio
    async def test_root_docs_link(self, async_client: AsyncClient):
        """测试根路径文档链接"""
        response = await async_client.get("/")
        data = response.json()
        
        assert data["docs"] == "/docs"


class TestCORSConfiguration:
    """CORS 中间件配置测试"""
    
    @pytest.mark.asyncio
    async def test_cors_allows_all_origins(self, async_client: AsyncClient):
        """测试 CORS 允许所有来源"""
        response = await async_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        # OPTIONS 预检请求应该返回 200
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_cors_headers_present(self, async_client: AsyncClient):
        """测试 CORS 响应头存在"""
        response = await async_client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # 检查 CORS 相关响应头
        assert "access-control-allow-origin" in response.headers


class TestErrorHandling:
    """全局异常处理测试"""
    
    @pytest.mark.asyncio
    async def test_404_for_unknown_route(self, async_client: AsyncClient):
        """测试未知路由返回 404"""
        response = await async_client.get("/unknown-route")
        assert response.status_code == 404


class TestOpenAPIDocumentation:
    """OpenAPI 文档端点测试"""
    
    @pytest.mark.asyncio
    async def test_docs_endpoint_available(self, async_client: AsyncClient):
        """测试 Swagger 文档端点可用"""
        response = await async_client.get("/docs")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_openapi_json_available(self, async_client: AsyncClient):
        """测试 OpenAPI JSON 端点可用"""
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Health Longevity Multi-Agent System"
