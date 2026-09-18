"""
智能体基类
定义所有智能体节点的抽象接口

Design Reference: Components and Interfaces - 智能体节点接口
"""

from abc import ABC, abstractmethod

from app.models.state import HealthState


class BaseAgent(ABC):
    """智能体基类接口

    所有智能体节点（Controller, Nutrition, Rehabilitation, Neuropsychology, Synthesis）
    都应继承此抽象基类并实现所有抽象方法。

    Design Reference: Components and Interfaces - 智能体节点接口 (app/agents/base.py)

    Attributes:
        name: 智能体名称，用于标识和日志记录

    Methods:
        process: 处理状态并返回更新后的状态（异步方法）
        get_system_prompt: 获取该智能体的系统提示词

    Example:
        >>> class NutritionAgent(BaseAgent):
        ...     @property
        ...     def name(self) -> str:
        ...         return "Nutrition_Agent"
        ...
        ...     async def process(self, state: HealthState) -> HealthState:
        ...         # 实现营养分析逻辑
        ...         state["expert_responses"]["nutrition"] = "分析结果..."
        ...         return state
        ...
        ...     def get_system_prompt(self) -> str:
        ...         return "你是一位营养学专家..."
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """智能体名称

        Returns:
            str: 智能体的唯一名称标识，如 "Controller_Agent", "Nutrition_Agent" 等
        """
        pass

    @abstractmethod
    async def process(self, state: HealthState) -> HealthState:
        """处理状态并返回更新后的状态

        这是智能体的核心处理方法。每个智能体节点接收当前的 HealthState，
        执行其专业领域的分析处理，并返回更新后的状态。

        Args:
            state: 当前的 LangGraph 全局状态，包含用户查询、画像、
                  子任务分解、专家响应等信息

        Returns:
            HealthState: 更新后的状态，包含该智能体的处理结果

        Raises:
            AgentTimeoutError: 当处理超时（默认30秒）时抛出
            Exception: 处理过程中可能发生的其他异常

        Note:
            - 实现时应注意处理超时限制（单个智能体30秒）
            - 应将结果写入 state["expert_responses"] 字典
            - 发生异常时应记录到 state["error_info"] 列表
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词

        返回该智能体与 LLM 交互时使用的系统提示词。
        系统提示词定义了智能体的角色、专业领域和输出格式要求。

        Returns:
            str: 系统提示词文本

        Example:
            >>> agent = NutritionAgent()
            >>> prompt = agent.get_system_prompt()
            >>> print(prompt)
            "你是一位专业的营养学专家，负责分析用户的营养状况..."
        """
        pass
