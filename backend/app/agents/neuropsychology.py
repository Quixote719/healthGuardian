"""
神经心理调节专家智能体节点

Neuropsychology_Agent 负责基于知识图谱检索心理神经免疫学知识，
根据用户的压力等级和睡眠时长生成个性化的神经心理干预建议。

Requirements: 8.1-8.8
"""

from typing import List, Optional

from app.agents.base import BaseAgent
from app.agents.health_analyzer import (
    StressInterventionLevel,
    get_stress_intervention_level,
    evaluate_sleep_duration,
    SleepEvaluation,
)
from app.agents.risk_detector import (
    detect_prohibited_keywords,
    get_professional_help_suggestion,
)
from app.models.action_item import ActionCategory, ActionItem, Priority, RiskLevel
from app.models.state import HealthState
from app.tools.graph_rag import GraphRAG
from app.tools.rag_interface import RAGResult
from app.services.llm import get_llm_service


# 干预类型标签
HARDWARE_INTERVENTION_LABEL = "硬件层干预"
SOFTWARE_INTERVENTION_LABEL = "软件层干预"


# 预定义的神经心理干预措施
HARDWARE_INTERVENTIONS = {
    "daily": [  # 日常调节类 (1-3级压力)
        {
            "title": "腹式呼吸训练",
            "description": f"[{HARDWARE_INTERVENTION_LABEL}] 每日进行10-15分钟腹式呼吸练习，"
            "通过深长的呼气激活副交感神经，降低皮质醇水平。"
            "建议在早起和睡前进行，有助于调节自主神经系统。",
            "frequency": "每日2次，每次10-15分钟",
            "duration": "4周",
        },
    ],
    "structured": [  # 结构化训练类 (4-6级压力)
        {
            "title": "HRV 心率变异性生物反馈训练",
            "description": f"[{HARDWARE_INTERVENTION_LABEL}] 使用 HRV 生物反馈设备进行自主神经调节训练，"
            "通过实时监测心率变异性，学习主动调节交感-副交感神经平衡。"
            "研究表明规律训练可显著改善压力应对能力和情绪调节。",
            "frequency": "每日1次，每次15-20分钟",
            "duration": "8周",
        },
        {
            "title": "渐进式肌肉放松训练",
            "description": f"[{HARDWARE_INTERVENTION_LABEL}] 通过系统性地收紧和放松全身各肌群，"
            "降低身体紧张度和肌肉张力。该技术可有效减少躯体化症状，"
            "改善睡眠质量，降低焦虑水平。",
            "frequency": "每日1次，每次20-30分钟",
            "duration": "6周",
        },
    ],
    "professional": [  # 专业支持类 (7-10级压力)
        {
            "title": "专业 HRV 生物反馈治疗",
            "description": f"[{HARDWARE_INTERVENTION_LABEL}] 在专业治疗师指导下进行系统的 HRV 生物反馈治疗，"
            "结合认知行为干预，全面改善自主神经功能和情绪调节能力。"
            "建议配合专业心理咨询同步进行。",
            "frequency": "每周2-3次，每次30-45分钟",
            "duration": "12周",
        },
        {
            "title": "光照疗法",
            "description": f"[{HARDWARE_INTERVENTION_LABEL}] 使用10000勒克斯光照治疗设备，"
            "调节昼夜节律和褪黑素分泌。光照疗法可改善情绪、"
            "增强警觉性，对于压力导致的情绪低落和睡眠问题有良好效果。"
            "建议在早晨进行，避免晚间使用。",
            "frequency": "每日早晨1次，每次20-30分钟",
            "duration": "8周",
        },
    ],
}


SOFTWARE_INTERVENTIONS = {
    "daily": [  # 日常调节类 (1-3级压力)
        {
            "title": "正念呼吸冥想",
            "description": f"[{SOFTWARE_INTERVENTION_LABEL}] 通过专注于呼吸的正念练习，"
            "培养觉察当下的能力，减少思维反刍。"
            "可使用正念冥想 App 辅助练习，逐步建立规律的冥想习惯。",
            "frequency": "每日1次，每次5-10分钟",
            "duration": "4周",
        },
        {
            "title": "情绪日记记录",
            "description": f"[{SOFTWARE_INTERVENTION_LABEL}] 每日记录情绪状态、触发事件和应对方式，"
            "通过书写增强情绪觉察和自我反思能力。"
            "有助于识别情绪模式和压力来源，为后续干预提供依据。建议长期坚持。",
            "frequency": "每日睡前记录，每次5-10分钟",
            "duration": "12周",
        },
    ],
    "structured": [  # 结构化训练类 (4-6级压力)
        {
            "title": "正念减压训练（MBSR）",
            "description": f"[{SOFTWARE_INTERVENTION_LABEL}] 系统学习正念减压技术，包括身体扫描、"
            "坐式冥想、正念行走和正念瑜伽。"
            "8周结构化课程可显著降低压力感知，改善情绪调节和生活质量。",
            "frequency": "每日练习30-45分钟，每周参加1次课程",
            "duration": "8周",
        },
        {
            "title": "认知重评训练",
            "description": f"[{SOFTWARE_INTERVENTION_LABEL}] 学习识别和挑战消极自动思维，"
            "用更平衡、理性的角度重新评估压力情境。"
            "该技术是认知行为疗法的核心技术，可有效减少焦虑和抑郁症状。",
            "frequency": "每日练习，遇到压力事件时应用",
            "duration": "6周",
        },
    ],
    "professional": [  # 专业支持类 (7-10级压力)
        {
            "title": "行为激活疗法",
            "description": f"[{SOFTWARE_INTERVENTION_LABEL}] 在治疗师指导下制定活动计划，"
            "逐步增加有意义和愉悦的活动，打破回避-抑郁的恶性循环。"
            "特别适合压力导致的动力下降和兴趣减退。"
            "【建议寻求专业心理咨询支持】",
            "frequency": "每周制定计划并执行，每周1次治疗会谈",
            "duration": "12周",
        },
        {
            "title": "专业心理咨询或治疗",
            "description": f"[{SOFTWARE_INTERVENTION_LABEL}] 建议寻求专业心理咨询师或治疗师的帮助，"
            "进行系统的心理评估和个性化治疗。"
            "重度压力状态需要专业支持，不建议仅依靠自我调节。"
            "【标记：需关注，建议尽快预约专业支持】",
            "frequency": "每周1-2次治疗会谈",
            "duration": "12周",
        },
    ],
}


# 睡眠相关干预措施
SLEEP_INTERVENTIONS = {
    "insufficient": [  # 睡眠不足 (<6小时)
        {
            "title": "睡眠卫生改善计划",
            "description": f"[{HARDWARE_INTERVENTION_LABEL}] 建立规律的睡眠-觉醒节律，"
            "固定就寝和起床时间（偏差不超过30分钟）。"
            "创造理想的睡眠环境：温度18-22°C、完全黑暗、安静。"
            "睡前1小时避免屏幕蓝光，可进行放松活动。建议长期坚持。",
            "frequency": "每日执行，逐步建立习惯",
            "duration": "8周",
        },
        {
            "title": "睡前放松仪式",
            "description": f"[{SOFTWARE_INTERVENTION_LABEL}] 建立固定的睡前放松程序，"
            "如温水泡脚、舒缓音乐、渐进式肌肉放松或轻柔瑜伽。"
            "帮助身心从活动状态过渡到休息状态，提高入睡效率。",
            "frequency": "每日睡前30分钟开始",
            "duration": "4周",
        },
    ],
    "excessive": [  # 睡眠过多 (>9小时)
        {
            "title": "规律作息调整",
            "description": f"[{HARDWARE_INTERVENTION_LABEL}] 逐步调整睡眠时间至7-8小时，"
            "设置固定的起床时间并严格执行。增加日间体力活动，"
            "避免日间过长午睡（限制在20分钟内）。"
            "过多睡眠可能提示潜在健康问题，建议关注日间精力状态。",
            "frequency": "每日执行",
            "duration": "4周",
        },
    ],
}


class NeuropsychologyAgent(BaseAgent):
    """神经心理调节专家智能体
    
    负责基于知识图谱检索心理神经免疫学知识，根据用户的压力等级
    和睡眠时长生成个性化的神经心理干预建议。
    
    Attributes:
        _graph_rag: Graph RAG 检索工具实例（可选）
    
    Requirements:
        - 8.1: 调用 Graph_RAG 检索心理神经免疫学知识图谱
        - 8.2: 根据压力等级匹配干预策略
        - 8.3: 根据睡眠时长评估并优先生成睡眠干预
        - 8.4: 区分硬件层和软件层干预输出
        - 8.5: 以 Action_Item 格式输出，category 设置为"神经心理"
        - 8.6: 将响应结果写入 Health_State 的 expert_responses 字段
        - 8.7: 检测禁止关键词，拒绝提供干预并返回建议
        - 8.8: Graph_RAG 检索失败时基于内置知识生成通用建议
    
    Example:
        >>> agent = NeuropsychologyAgent()
        >>> state = await agent.process(initial_state)
        >>> print(state["expert_responses"]["neuropsychology"])
    """
    
    def __init__(self, graph_rag: Optional[GraphRAG] = None):
        """初始化神经心理智能体
        
        Args:
            graph_rag: Graph RAG 检索工具实例，如果为 None 则使用内置知识
        """
        self._graph_rag = graph_rag
    
    @property
    def name(self) -> str:
        """智能体名称"""
        return "Neuropsychology_Agent"
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一位专业的神经心理调节专家，专注于心理神经免疫学领域。

你的职责是：
1. 评估用户的压力状态和睡眠质量
2. 基于心理神经免疫学知识提供科学的干预建议
3. 区分硬件层干预（如生物反馈、光照疗法）和软件层干预（如认知重构、正念冥想）
4. 根据压力等级匹配适当的干预强度
5. 优先关注睡眠问题，因为睡眠是身心健康的基础

注意事项：
- 对于严重精神健康问题（如自杀倾向、精神分裂症状），必须建议寻求专业帮助
- 高压力状态（7-10级）需要标记"需关注"并建议专业支持
- 所有建议应基于科学证据，并注明干预类型（硬件层/软件层）
"""
    
    async def process(self, state: HealthState) -> HealthState:
        """处理状态并生成神经心理干预建议
        
        如果没有用户画像，则只根据用户查询生成通用建议。
        
        Args:
            state: 当前的 LangGraph 全局状态
        
        Returns:
            更新后的状态，包含神经心理干预建议
        
        Requirements:
            - 8.1-8.8: 完整的神经心理干预流程
        """
        # 初始化 expert_responses 如果不存在
        if "expert_responses" not in state:
            state["expert_responses"] = {}
        
        # 获取用户查询文本
        user_query = state.get("user_query", "")
        
        # Requirement 8.7: 检测禁止关键词
        is_prohibited, prohibited_keywords = detect_prohibited_keywords(user_query)
        if is_prohibited:
            professional_help = get_professional_help_suggestion()
            state["expert_responses"]["neuropsychology"] = (
                f"检测到敏感内容（{', '.join(prohibited_keywords)}），"
                f"无法提供神经心理干预建议。\n\n{professional_help}"
            )
            return state
        
        # 获取用户画像（可能为 None）
        user_profile = state.get("user_profile")
        
        # 初始化变量
        stress_result = None
        sleep_result = None
        rag_content = ""
        rag_note = ""
        action_items: List[ActionItem] = []
        
        # 如果有用户画像，进行个性化分析
        if user_profile is not None:
            # 获取压力等级和睡眠时长
            lifestyle = user_profile.lifestyle
            stress_level = lifestyle.stress_level
            sleep_duration = lifestyle.sleep_duration
            
            # Requirement 8.2: 根据压力等级匹配干预策略
            stress_result = get_stress_intervention_level(stress_level)
            
            # Requirement 8.3: 评估睡眠时长
            sleep_result = evaluate_sleep_duration(sleep_duration)
            
            # Requirement 8.1, 8.8: 尝试调用 Graph RAG 检索
            if self._graph_rag is not None:
                try:
                    rag_results = await self._graph_rag.query(
                        f"压力等级{stress_level}级 睡眠时长{sleep_duration}小时 心理神经免疫学干预",
                        top_k=5,
                        similarity_threshold=0.7,
                    )
                    rag_content = self._extract_rag_content(rag_results)
                except Exception:
                    rag_note = "（未检索到专业知识库内容，基于内置知识生成建议）"
            else:
                rag_note = "（未检索到专业知识库内容，基于内置知识生成建议）"
            
            # 生成干预措施
            # Requirement 8.3: 睡眠异常时优先生成睡眠干预
            if sleep_result.needs_priority_intervention:
                action_items.extend(
                    self._create_sleep_interventions("insufficient", stress_result)
                )
            elif sleep_result.evaluation == SleepEvaluation.EXCESSIVE:
                action_items.extend(
                    self._create_sleep_interventions("excessive", stress_result)
                )
            
            # Requirement 8.2, 8.4: 根据压力等级生成干预措施
            intervention_key = self._get_intervention_key(stress_result.level)
            action_items.extend(
                self._create_stress_interventions(intervention_key, stress_result)
            )
        else:
            # 没有用户画像时，尝试只根据查询检索 RAG
            if self._graph_rag is not None and user_query:
                try:
                    rag_results = await self._graph_rag.query(
                        user_query,
                        top_k=5,
                        similarity_threshold=0.7,
                    )
                    rag_content = self._extract_rag_content(rag_results)
                except Exception:
                    pass
        
        # 确保不超过合理数量（去重后取前5个）
        action_items = self._deduplicate_actions(action_items)[:5]
        
        # 构建用户健康上下文
        if user_profile is not None:
            user_context = self._build_user_context(
                user_profile=user_profile,
                stress_result=stress_result,
                sleep_result=sleep_result,
            )
        else:
            user_context = "（用户未提供个人健康档案，请提供通用的神经心理调节建议）"
        
        # 调用 LLM 生成个性化建议
        llm_response = ""
        if user_query:
            try:
                llm_service = get_llm_service()
                llm_response = await llm_service.generate_health_advice(
                    system_prompt=self.get_system_prompt(),
                    user_query=user_query,
                    user_context=user_context,
                    rag_knowledge=rag_content,
                )
            except Exception as e:
                # LLM 调用失败
                llm_response = f"抱歉，服务暂时不可用，请稍后重试。（错误：{type(e).__name__}）"
        
        # 构建响应文本
        response_parts = []
        
        # LLM 生成的个性化建议（如果有）
        if llm_response:
            response_parts.append(f"## 针对您问题的建议\n")
            response_parts.append(llm_response)
            response_parts.append("")
        
        # 如果有用户画像，显示评估结果
        if user_profile is not None and stress_result and sleep_result:
            lifestyle = user_profile.lifestyle
            
            # 压力评估结果
            response_parts.append(f"## 压力状态评估\n")
            response_parts.append(f"- 压力等级：{lifestyle.stress_level}级")
            response_parts.append(f"- 干预策略：{stress_result.level.value}")
            response_parts.append(f"- {stress_result.description}")
            if stress_result.requires_attention:
                response_parts.append(f"- ⚠️ **需要关注**：建议尽快寻求专业心理支持")
            
            # 睡眠评估结果
            response_parts.append(f"\n## 睡眠状态评估\n")
            response_parts.append(f"- 睡眠时长：{lifestyle.sleep_duration}小时")
            response_parts.append(f"- 评估结果：{sleep_result.evaluation.value}")
            response_parts.append(f"- {sleep_result.description}")
            
            # RAG 检索内容（如果有）
            if rag_content:
                response_parts.append(f"\n## 知识图谱检索结果\n")
                response_parts.append(rag_content)
            
            if rag_note:
                response_parts.append(f"\n{rag_note}")
            
            # 干预措施摘要
            if action_items:
                response_parts.append(f"\n## 干预措施摘要\n")
                response_parts.append(f"共生成 {len(action_items)} 项神经心理干预措施：")
                
                hardware_count = sum(
                    1 for item in action_items 
                    if HARDWARE_INTERVENTION_LABEL in item.description
                )
                software_count = len(action_items) - hardware_count
                response_parts.append(f"- 硬件层干预：{hardware_count} 项")
                response_parts.append(f"- 软件层干预：{software_count} 项")
        else:
            response_parts.append("\n> 注：本建议基于通用神经心理知识生成。如需获得个性化建议，请提供您的健康档案信息。")
        
        # Requirement 8.6: 将响应结果写入 expert_responses
        state["expert_responses"]["neuropsychology"] = "\n".join(response_parts)
        
        # 将 action_items 也存储到状态中（供 Synthesis_Agent 使用）
        if "neuropsychology_actions" not in state:
            state["neuropsychology_actions"] = []
        state["neuropsychology_actions"] = [
            item.model_dump() for item in action_items
        ]
        
        return state
    
    def _build_user_context(
        self,
        user_profile,
        stress_result,
        sleep_result,
    ) -> str:
        """构建用户健康上下文描述
        
        Args:
            user_profile: 用户画像
            stress_result: 压力评估结果
            sleep_result: 睡眠评估结果
        
        Returns:
            用户健康上下文的文本描述
        """
        lifestyle = user_profile.lifestyle
        
        context_parts = [
            f"### 基本信息",
            f"- 年龄: {user_profile.age}岁",
            f"- 性别: {user_profile.gender}",
            "",
            f"### 生活方式",
            f"- 睡眠时长: {lifestyle.sleep_duration}小时",
            f"- 压力等级: {lifestyle.stress_level}/10",
            f"- 运动频率: {lifestyle.exercise_frequency}",
            "",
            f"### 压力状态评估",
            f"- 压力等级: {lifestyle.stress_level}级",
            f"- 干预策略: {stress_result.level.value}",
            f"- {stress_result.description}",
        ]
        
        if stress_result.requires_attention:
            context_parts.append(f"- ⚠️ 需要关注：建议寻求专业心理支持")
        
        context_parts.extend([
            "",
            f"### 睡眠状态评估",
            f"- 睡眠时长: {lifestyle.sleep_duration}小时",
            f"- 评估结果: {sleep_result.evaluation.value}",
            f"- {sleep_result.description}",
        ])
        
        if sleep_result.needs_priority_intervention:
            context_parts.append(f"- ⚠️ 需要优先干预睡眠问题")
        
        return "\n".join(context_parts)
    
    def _get_intervention_key(
        self, level: StressInterventionLevel
    ) -> str:
        """根据压力干预等级获取干预措施键名
        
        Args:
            level: 压力干预等级
        
        Returns:
            干预措施字典的键名
        """
        if level == StressInterventionLevel.DAILY_REGULATION:
            return "daily"
        elif level == StressInterventionLevel.STRUCTURED_TRAINING:
            return "structured"
        else:  # PROFESSIONAL_SUPPORT
            return "professional"
    
    def _create_stress_interventions(
        self,
        intervention_key: str,
        stress_result,
    ) -> List[ActionItem]:
        """创建压力相关的干预措施
        
        Args:
            intervention_key: 干预措施键名 ("daily", "structured", "professional")
            stress_result: 压力干预结果
        
        Returns:
            ActionItem 列表
        """
        action_items = []
        
        # 确定优先级和风险等级
        if stress_result.requires_attention:
            priority = Priority.HIGH
            risk_level = RiskLevel.MEDIUM  # 高压力但非高风险干预
        elif intervention_key == "structured":
            priority = Priority.MEDIUM
            risk_level = RiskLevel.LOW
        else:
            priority = Priority.LOW if intervention_key == "daily" else Priority.HIGH
            risk_level = RiskLevel.LOW
        
        # 添加硬件层干预
        hardware_items = HARDWARE_INTERVENTIONS.get(intervention_key, [])
        for item_data in hardware_items:
            action_items.append(
                ActionItem(
                    category=ActionCategory.NEUROPSYCHOLOGY,
                    title=item_data["title"],
                    description=item_data["description"],
                    frequency=item_data["frequency"],
                    priority=priority,
                    risk_level=risk_level,
                    duration=item_data["duration"],
                )
            )
        
        # 添加软件层干预
        software_items = SOFTWARE_INTERVENTIONS.get(intervention_key, [])
        for item_data in software_items:
            action_items.append(
                ActionItem(
                    category=ActionCategory.NEUROPSYCHOLOGY,
                    title=item_data["title"],
                    description=item_data["description"],
                    frequency=item_data["frequency"],
                    priority=priority,
                    risk_level=risk_level,
                    duration=item_data["duration"],
                )
            )
        
        return action_items
    
    def _create_sleep_interventions(
        self,
        sleep_type: str,
        stress_result,
    ) -> List[ActionItem]:
        """创建睡眠相关的干预措施
        
        Args:
            sleep_type: 睡眠类型 ("insufficient" or "excessive")
            stress_result: 压力干预结果
        
        Returns:
            ActionItem 列表
        """
        action_items = []
        
        # 睡眠干预优先级较高
        priority = Priority.HIGH if sleep_type == "insufficient" else Priority.MEDIUM
        risk_level = RiskLevel.LOW
        
        sleep_items = SLEEP_INTERVENTIONS.get(sleep_type, [])
        for item_data in sleep_items:
            action_items.append(
                ActionItem(
                    category=ActionCategory.NEUROPSYCHOLOGY,
                    title=item_data["title"],
                    description=item_data["description"],
                    frequency=item_data["frequency"],
                    priority=priority,
                    risk_level=risk_level,
                    duration=item_data["duration"],
                )
            )
        
        return action_items
    
    def _extract_rag_content(self, rag_results: List[RAGResult]) -> str:
        """从 RAG 结果中提取内容
        
        Args:
            rag_results: RAG 检索结果列表
        
        Returns:
            提取的内容文本
        """
        if not rag_results:
            return ""
        
        content_parts = []
        for result in rag_results:
            # 检查是否有错误
            if result.metadata.get("error_type"):
                continue
            
            if result.content:
                content_parts.append(result.content)
            
            # 提取实体和关系信息
            entities = result.metadata.get("entities", [])
            relations = result.metadata.get("relations", [])
            
            if entities:
                entity_names = [e.get("name", "") for e in entities if e.get("name")]
                if entity_names:
                    content_parts.append(f"相关概念：{', '.join(entity_names)}")
            
            if relations:
                rel_strs = []
                for r in relations:
                    source = r.get("source_entity", "")
                    target = r.get("target_entity", "")
                    rel_type = r.get("relation_type", "")
                    if source and target and rel_type:
                        rel_strs.append(f"{source} → {rel_type} → {target}")
                if rel_strs:
                    content_parts.append(f"知识关系：\n- " + "\n- ".join(rel_strs))
        
        return "\n\n".join(content_parts)
    
    def _deduplicate_actions(
        self, action_items: List[ActionItem]
    ) -> List[ActionItem]:
        """对干预措施进行去重
        
        基于 title 进行去重，保留第一个出现的。
        
        Args:
            action_items: 原始干预措施列表
        
        Returns:
            去重后的干预措施列表
        """
        seen_titles = set()
        unique_items = []
        
        for item in action_items:
            if item.title not in seen_titles:
                seen_titles.add(item.title)
                unique_items.append(item)
        
        return unique_items
