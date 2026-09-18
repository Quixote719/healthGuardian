"""
智能体基类测试
Tests for app/agents/base.py

Design Reference: Components and Interfaces - 智能体节点接口
"""

from abc import ABC
from typing import get_type_hints

import pytest

from app.agents.base import BaseAgent
from app.models.state import HealthState


class TestBaseAgentStructure:
    """BaseAgent 类结构测试"""

    def test_base_agent_is_abstract_class(self):
        """测试 BaseAgent 是抽象基类"""
        assert issubclass(BaseAgent, ABC)

    def test_base_agent_cannot_be_instantiated(self):
        """测试 BaseAgent 不能直接实例化"""
        with pytest.raises(TypeError) as exc_info:
            BaseAgent()

        # 检查错误消息包含抽象方法信息
        assert "abstract" in str(exc_info.value).lower()

    def test_base_agent_has_name_property(self):
        """测试 BaseAgent 定义了 name 抽象属性"""
        # 检查 name 是否在抽象方法中
        assert "name" in BaseAgent.__abstractmethods__

    def test_base_agent_has_process_method(self):
        """测试 BaseAgent 定义了 process 抽象方法"""
        assert "process" in BaseAgent.__abstractmethods__

    def test_base_agent_has_get_system_prompt_method(self):
        """测试 BaseAgent 定义了 get_system_prompt 抽象方法"""
        assert "get_system_prompt" in BaseAgent.__abstractmethods__

    def test_base_agent_has_exactly_three_abstract_members(self):
        """测试 BaseAgent 恰好有3个抽象成员"""
        assert len(BaseAgent.__abstractmethods__) == 3


class TestBaseAgentTypeHints:
    """BaseAgent 类型注解测试"""

    def test_process_method_signature(self):
        """测试 process 方法的参数和返回值类型"""
        # 获取 process 方法的类型提示
        hints = get_type_hints(BaseAgent.process)

        # 检查 state 参数类型
        assert "state" in hints
        assert hints["state"] == HealthState

        # 检查返回值类型
        assert "return" in hints
        assert hints["return"] == HealthState

    def test_get_system_prompt_return_type(self):
        """测试 get_system_prompt 方法返回 str 类型"""
        hints = get_type_hints(BaseAgent.get_system_prompt)

        assert "return" in hints
        assert hints["return"] == str

    def test_name_property_return_type(self):
        """测试 name 属性返回 str 类型"""
        # name 是一个 property，我们需要检查它的 fget 方法
        name_property = BaseAgent.name
        assert isinstance(name_property, property)

        # 获取 fget 的类型提示
        hints = get_type_hints(name_property.fget)
        assert hints.get("return") == str


class TestConcreteAgentImplementation:
    """具体智能体实现测试"""

    def test_concrete_agent_with_all_methods_can_be_instantiated(self):
        """测试实现所有抽象方法的具体智能体可以实例化"""

        class ConcreteAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "Test_Agent"

            async def process(self, state: HealthState) -> HealthState:
                return state

            def get_system_prompt(self) -> str:
                return "Test prompt"

        agent = ConcreteAgent()
        assert agent is not None
        assert isinstance(agent, BaseAgent)

    def test_concrete_agent_name_property_works(self):
        """测试具体智能体的 name 属性工作正常"""

        class ConcreteAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "Test_Agent"

            async def process(self, state: HealthState) -> HealthState:
                return state

            def get_system_prompt(self) -> str:
                return "Test prompt"

        agent = ConcreteAgent()
        assert agent.name == "Test_Agent"

    def test_concrete_agent_get_system_prompt_works(self):
        """测试具体智能体的 get_system_prompt 方法工作正常"""

        class ConcreteAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "Test_Agent"

            async def process(self, state: HealthState) -> HealthState:
                return state

            def get_system_prompt(self) -> str:
                return "你是一位测试专家智能体"

        agent = ConcreteAgent()
        assert agent.get_system_prompt() == "你是一位测试专家智能体"

    @pytest.mark.asyncio
    async def test_concrete_agent_process_works(self):
        """测试具体智能体的 process 方法工作正常"""

        class ConcreteAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "Test_Agent"

            async def process(self, state: HealthState) -> HealthState:
                # 模拟处理逻辑：添加响应到 expert_responses
                if "expert_responses" not in state:
                    state["expert_responses"] = {}
                state["expert_responses"]["test"] = "处理完成"
                return state

            def get_system_prompt(self) -> str:
                return "Test prompt"

        agent = ConcreteAgent()
        initial_state: HealthState = {
            "user_query": "测试查询",
            "expert_responses": {}
        }

        result = await agent.process(initial_state)

        assert result is not None
        assert "expert_responses" in result
        assert result["expert_responses"]["test"] == "处理完成"


class TestIncompleteAgentImplementation:
    """不完整智能体实现测试"""

    def test_agent_missing_name_cannot_be_instantiated(self):
        """测试缺少 name 属性的智能体无法实例化"""

        class IncompleteAgent(BaseAgent):
            async def process(self, state: HealthState) -> HealthState:
                return state

            def get_system_prompt(self) -> str:
                return "Test prompt"

        with pytest.raises(TypeError):
            IncompleteAgent()

    def test_agent_missing_process_cannot_be_instantiated(self):
        """测试缺少 process 方法的智能体无法实例化"""

        class IncompleteAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "Test_Agent"

            def get_system_prompt(self) -> str:
                return "Test prompt"

        with pytest.raises(TypeError):
            IncompleteAgent()

    def test_agent_missing_get_system_prompt_cannot_be_instantiated(self):
        """测试缺少 get_system_prompt 方法的智能体无法实例化"""

        class IncompleteAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "Test_Agent"

            async def process(self, state: HealthState) -> HealthState:
                return state

        with pytest.raises(TypeError):
            IncompleteAgent()


class TestBaseAgentInheritance:
    """BaseAgent 继承测试"""

    def test_isinstance_check_works(self):
        """测试 isinstance 检查正常工作"""

        class ConcreteAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "Test_Agent"

            async def process(self, state: HealthState) -> HealthState:
                return state

            def get_system_prompt(self) -> str:
                return "Test prompt"

        agent = ConcreteAgent()
        assert isinstance(agent, BaseAgent)

    def test_issubclass_check_works(self):
        """测试 issubclass 检查正常工作"""

        class ConcreteAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "Test_Agent"

            async def process(self, state: HealthState) -> HealthState:
                return state

            def get_system_prompt(self) -> str:
                return "Test prompt"

        assert issubclass(ConcreteAgent, BaseAgent)

    def test_multiple_agents_can_be_created(self):
        """测试可以创建多个不同的具体智能体"""

        class AgentA(BaseAgent):
            @property
            def name(self) -> str:
                return "Agent_A"

            async def process(self, state: HealthState) -> HealthState:
                return state

            def get_system_prompt(self) -> str:
                return "Prompt A"

        class AgentB(BaseAgent):
            @property
            def name(self) -> str:
                return "Agent_B"

            async def process(self, state: HealthState) -> HealthState:
                return state

            def get_system_prompt(self) -> str:
                return "Prompt B"

        agent_a = AgentA()
        agent_b = AgentB()

        assert agent_a.name != agent_b.name
        assert agent_a.get_system_prompt() != agent_b.get_system_prompt()
        assert isinstance(agent_a, BaseAgent)
        assert isinstance(agent_b, BaseAgent)


class TestBaseAgentDocumentation:
    """BaseAgent 文档测试"""

    def test_base_agent_has_docstring(self):
        """测试 BaseAgent 类有文档字符串"""
        assert BaseAgent.__doc__ is not None
        assert len(BaseAgent.__doc__) > 0

    def test_name_property_has_docstring(self):
        """测试 name 属性有文档字符串"""
        name_property = BaseAgent.name
        assert name_property.fget.__doc__ is not None

    def test_process_method_has_docstring(self):
        """测试 process 方法有文档字符串"""
        assert BaseAgent.process.__doc__ is not None

    def test_get_system_prompt_method_has_docstring(self):
        """测试 get_system_prompt 方法有文档字符串"""
        assert BaseAgent.get_system_prompt.__doc__ is not None


class TestModuleExports:
    """模块导出测试"""

    def test_base_agent_can_be_imported_from_agents_module(self):
        """测试 BaseAgent 可以从 agents 模块导入"""
        from app.agents import BaseAgent as ImportedBaseAgent

        assert ImportedBaseAgent is BaseAgent

    def test_base_agent_in_agents_module_all(self):
        """测试 BaseAgent 在 agents 模块的 __all__ 中"""
        from app import agents

        assert hasattr(agents, "__all__")
        assert "BaseAgent" in agents.__all__
