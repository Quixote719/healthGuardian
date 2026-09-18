"""
LLM 服务模块

封装与 LLM API 的交互，支持 OpenAI 和 DeepSeek 等兼容接口。
"""

import json
import logging
import os
import re
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class LLMService:
    """LLM 服务类

    封装 LLM API 调用，支持 OpenAI 兼容接口（包括 DeepSeek）。

    Attributes:
        _llm: ChatOpenAI 实例
    """

    _instance: Optional["LLMService"] = None

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        model: str | None = None,
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
        system_prompt: str | None = None,
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

    def _extract_json_from_response(self, response: str) -> dict | None:
        """从 LLM 响应中提取 JSON

        尝试多种方式提取 JSON：
        1. 直接解析整个响应
        2. 提取 ```json ... ``` 代码块
        3. 提取 { } 之间的内容

        Args:
            response: LLM 的原始响应文本

        Returns:
            解析后的 JSON 对象，失败返回 None
        """
        # 方式1: 直接尝试解析
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # 方式2: 提取 ```json ... ``` 代码块
        json_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        matches = re.findall(json_block_pattern, response, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        # 方式3: 提取最外层的 { } 内容
        brace_pattern = r"\{[\s\S]*\}"
        matches = re.findall(brace_pattern, response)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        return None

    async def generate_structured_advice(
        self,
        agent_type: str,
        system_prompt: str,
        user_query: str,
        user_context: str,
        rag_knowledge: str = "",
    ) -> dict:
        """生成结构化的健康建议

        让 LLM 返回 JSON 格式的响应，包含 deep_insight 和 action_items。

        Args:
            agent_type: 智能体类型 ("nutrition" | "rehabilitation" | "neuropsychology")
            system_prompt: 专家 agent 的系统提示词
            user_query: 用户的原始查询
            user_context: 用户画像和健康数据的文本描述
            rag_knowledge: RAG 检索到的相关知识（可选）

        Returns:
            结构化响应:
            {
                "deep_insight": "深度分析...",
                "action_items": [
                    {
                        "title": "建议标题",
                        "description": "详细描述",
                        "frequency": "执行频率",
                        "priority": "高/中/低",
                        "risk_level": "高风险/中风险/低风险",
                        "duration": "持续时间如 4周"
                    }
                ]
            }
        """
        # 根据 agent 类型确定分类
        category_map = {
            "nutrition": "营养",
            "rehabilitation": "康复",
            "neuropsychology": "神经心理",
        }
        category = category_map.get(agent_type, "营养")

        # 检查是否有用户画像
        has_profile = "用户未提供个人健康档案" not in user_context

        # 构建用户消息
        message_parts = [
            "## 用户查询",
            user_query,
        ]

        if has_profile:
            message_parts.extend(
                [
                    "",
                    "## 用户健康档案",
                    user_context,
                ]
            )

        if rag_knowledge:
            message_parts.extend(
                [
                    "",
                    "## 参考知识库内容",
                    rag_knowledge,
                ]
            )

        # JSON 输出格式要求
        message_parts.extend(
            [
                "",
                "## 输出要求",
                "请以 JSON 格式返回你的分析和建议，格式如下：",
                "```json",
                "{",
                '  "deep_insight": "针对用户问题的深度分析，解释问题的原因、机制和重要性，200-500字",',
                '  "action_items": [',
                "    {",
                '      "title": "简短的建议标题（10-30字）",',
                '      "description": "详细的执行说明，包括具体方法、注意事项（50-200字）",',
                '      "frequency": "执行频率，如：每天、每周3次、每餐前",',
                '      "priority": "高/中/低",',
                '      "risk_level": "低风险/中风险/高风险",',
                '      "duration": "持续时间，格式为数字+单位，如：4周、3个月、长期"',
                "    }",
                "  ]",
                "}",
                "```",
                "",
                "要求：",
                "1. deep_insight 要直接回应用户的具体问题，分析要有深度",
                "2. action_items 提供 2-5 个具体可操作的建议",
                "3. 每个建议要具体、可执行，不要泛泛而谈",
                f"4. 所有建议都属于「{category}」领域",
                "5. priority 根据对用户健康的重要程度设定",
                "6. risk_level 根据执行建议的潜在风险设定：",
                "   - 低风险：日常生活调整，如饮食习惯、作息调整",
                "   - 中风险：需要一定注意的建议，如运动强度调整、补剂使用",
                "   - 高风险：涉及药物调整、高强度运动、长时间断食等",
                "7. duration 格式必须是「数字+天/周/月」，如「4周」「3个月」「30天」",
            ]
        )

        if has_profile:
            message_parts.append("8. 结合用户的个人健康状况进行个性化调整")
        else:
            message_parts.extend(
                [
                    "",
                    "注意：用户未提供个人健康档案，请给出通用但仍然具体的建议。",
                ]
            )

        message_parts.extend(
            [
                "",
                "只返回 JSON，不要有其他内容。",
            ]
        )

        user_message = "\n".join(message_parts)

        # 调用 LLM
        response = await self.chat(user_message, system_prompt)
        logger.info(f"[{agent_type}] LLM raw response length: {len(response)}")

        # 解析 JSON
        result = self._extract_json_from_response(response)

        if result is None:
            logger.warning(f"[{agent_type}] Failed to parse LLM response as JSON, using fallback")
            # 返回一个基于原始响应的 fallback
            return {
                "deep_insight": response[:1000] if len(response) > 1000 else response,
                "action_items": [],
                "parse_error": True,
            }

        # 确保必要字段存在
        if "deep_insight" not in result:
            result["deep_insight"] = ""
        if "action_items" not in result:
            result["action_items"] = []

        # 为每个 action_item 添加 category
        for item in result.get("action_items", []):
            item["category"] = category
            # 规范化 duration 格式
            duration = item.get("duration", "4周")
            if not re.match(r"^\d+[天周月]$", duration):
                # 尝试修复常见格式
                duration = duration.replace("个月", "月").replace(" ", "")
                if not re.match(r"^\d+[天周月]$", duration):
                    item["duration"] = "4周"  # 默认值

        logger.info(
            f"[{agent_type}] Parsed {len(result.get('action_items', []))} action items"
        )
        return result

    async def generate_health_advice(
        self,
        system_prompt: str,
        user_query: str,
        user_context: str,
        rag_knowledge: str = "",
    ) -> str:
        """生成健康建议（兼容旧接口）

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
            message_parts.extend(
                [
                    "",
                    "## 用户健康档案",
                    user_context,
                ]
            )

        if rag_knowledge:
            message_parts.extend(
                [
                    "",
                    "## 参考知识库内容",
                    rag_knowledge,
                ]
            )

        message_parts.extend(
            [
                "",
                "## 输出要求",
                "请根据用户的查询提供专业建议。",
                "",
                "1. 直接回应用户的具体问题",
                "2. 提供具体可操作的行动建议",
                "3. 注明注意事项和风险提示（如适用）",
            ]
        )

        if has_profile:
            message_parts.append("4. 结合用户的个人健康状况进行个性化调整")
        else:
            message_parts.extend(
                [
                    "",
                    "## 关于追问信息",
                    "用户未提供个人健康档案。请根据问题的性质自行判断：",
                    "- 如果问题是通用性的（如'什么是健康饮食'），直接给出通用建议即可",
                    "- 如果问题涉及具体症状、疾病或需要个性化方案，且你认为某些关键信息会显著影响建议的准确性，可以在回答末尾礼貌地询问",
                    "- 询问时要说明为什么需要这些信息，让用户理解提供信息的价值",
                    "- 不要每次都追问，只在真正必要时才问",
                ]
            )

        user_message = "\n".join(message_parts)

        return await self.chat(user_message, system_prompt)


def get_llm_service() -> LLMService:
    """获取 LLM 服务实例的便捷函数

    Returns:
        LLMService 实例
    """
    return LLMService.get_instance()
