"""
LLM 服务模块

封装与 LLM API 的交互，支持 OpenAI 和 DeepSeek 等兼容接口。
"""

import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class LLMService:
    """LLM 服务类
    
    封装 LLM API 调用，支持 OpenAI 兼容接口（包括 DeepSeek）。
    
    Attributes:
        _llm: ChatOpenAI 实例
    """
    
    _instance: Optional["LLMService"] = None
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> None:
        """初始化 LLM 服务
        
        Args:
            api_key: API 密钥，默认从环境变量 OPENAI_API_KEY 或 DEEPSEEK_API_KEY 获取
            api_base: API 基础 URL，默认从环境变量 OPENAI_API_BASE 获取
            model: 模型名称，默认从环境变量 OPENAI_MODEL 获取
            temperature: 温度参数，控制输出随机性
            max_tokens: 最大输出 token 数
        """
        # 优先使用 DeepSeek 配置，其次使用 OpenAI 配置
        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        self._api_base = api_base or os.getenv("OPENAI_API_BASE")
        self._model = model or os.getenv("OPENAI_MODEL", "deepseek-chat")
        self._temperature = temperature
        self._max_tokens = max_tokens
        
        # 创建 ChatOpenAI 实例
        self._llm = ChatOpenAI(
            api_key=self._api_key,
            base_url=self._api_base,
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
    
    @classmethod
    def get_instance(cls) -> "LLMService":
        """获取 LLM 服务单例实例
        
        Returns:
            LLMService 单例实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """发送聊天请求
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示词（可选）
        
        Returns:
            LLM 响应文本
        """
        messages = []
        
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        messages.append(HumanMessage(content=user_message))
        
        response = await self._llm.ainvoke(messages)
        return response.content
    
    async def generate_health_advice(
        self,
        system_prompt: str,
        user_query: str,
        user_context: str,
        rag_knowledge: str = "",
    ) -> str:
        """生成健康建议
        
        将用户查询、用户上下文（画像数据）和 RAG 知识组合，
        调用 LLM 生成个性化的健康建议。
        
        Args:
            system_prompt: 专家 agent 的系统提示词
            user_query: 用户的原始查询
            user_context: 用户画像和健康数据的文本描述
            rag_knowledge: RAG 检索到的相关知识（可选）
        
        Returns:
            LLM 生成的健康建议
        """
        # 检查是否有用户画像
        has_profile = "用户未提供个人健康档案" not in user_context
        
        # 构建完整的用户消息
        message_parts = [
            "## 用户查询",
            user_query,
        ]
        
        if has_profile:
            message_parts.extend([
                "",
                "## 用户健康档案",
                user_context,
            ])
        
        if rag_knowledge:
            message_parts.extend([
                "",
                "## 参考知识库内容",
                rag_knowledge,
            ])
        
        message_parts.extend([
            "",
            "## 输出要求",
            "请根据用户的查询提供专业建议。",
            "",
            "1. 直接回应用户的具体问题",
            "2. 提供具体可操作的行动建议",
            "3. 注明注意事项和风险提示（如适用）",
        ])
        
        if has_profile:
            message_parts.append("4. 结合用户的个人健康状况进行个性化调整")
        else:
            message_parts.extend([
                "",
                "## 关于追问信息",
                "用户未提供个人健康档案。请根据问题的性质自行判断：",
                "- 如果问题是通用性的（如'什么是健康饮食'），直接给出通用建议即可",
                "- 如果问题涉及具体症状、疾病或需要个性化方案，且你认为某些关键信息（如年龄、既往病史、用药情况等）会显著影响建议的准确性，可以在回答末尾礼貌地询问",
                "- 询问时要说明为什么需要这些信息，让用户理解提供信息的价值",
                "- 不要每次都追问，只在真正必要时才问",
            ])
        
        user_message = "\n".join(message_parts)
        
        return await self.chat(user_message, system_prompt)


def get_llm_service() -> LLMService:
    """获取 LLM 服务实例的便捷函数
    
    Returns:
        LLMService 实例
    """
    return LLMService.get_instance()
