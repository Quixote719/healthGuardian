"""
Controller_Agent 主控智能体

负责任务拆解、风险检测和安全检查。
将用户请求分解为营养、康复、神经心理三个维度的子任务。

Requirements: 5.1-5.5
Design Reference: LangGraph 工作流设计 - Controller_Agent
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import List

from app.agents.base import BaseAgent
from app.agents.risk_detector import (
    perform_safety_check,
    get_professional_help_suggestion,
)
from app.models.state import (
    ErrorInfo,
    HealthState,
    NodeExecutionStatus,
    SubTask,
    TargetAgent,
)


# 超时时间（秒）
CONTROLLER_TIMEOUT_SECONDS = 30


def _utc_now() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ControllerAgent(BaseAgent):
    """主控智能体
    
    Controller_Agent 是 LangGraph 工作流的入口节点，负责：
    1. 读取用户画像信息
    2. 执行安全检查（禁止关键词、高风险关键词、超出范围检测）
    3. 将用户请求拆解为营养、康复、神经心理三个维度的子任务
    4. 设置相应的状态标志（ui_interrupt_flag、error_info等）
    
    Requirements: 5.1-5.5
    
    Attributes:
        name: 智能体名称 "Controller_Agent"
    
    Example:
        >>> controller = ControllerAgent()
        >>> state = {"user_query": "我血脂偏高，睡眠不好", "user_profile": profile}
        >>> result = await controller.process(state)
        >>> print(result["task_breakdown"])
        [SubTask(...), SubTask(...), SubTask(...)]
    """
    
    @property
    def name(self) -> str:
        """智能体名称
        
        Returns:
            str: "Controller_Agent"
        """
        return "Controller_Agent"
    
    def get_system_prompt(self) -> str:
        """获取系统提示词
        
        返回 Controller_Agent 的系统提示词，用于定义其角色和行为。
        
        Returns:
            str: 系统提示词文本
        """
        return """你是健康多智能体系统的主控智能体（Controller_Agent）。

你的职责是：
1. 分析用户的健康咨询请求
2. 将请求拆解为三个维度的子任务：
   - 营养（nutrition）：饮食、补剂、营养素相关
   - 康复（rehabilitation）：运动、体态、身体机能相关
   - 神经心理（neuropsychology）：压力、睡眠、情绪、认知相关
3. 确保每个子任务描述清晰、具体、可执行

请根据用户的查询内容和健康画像，生成针对性的子任务描述。"""
    
    async def process(self, state: HealthState) -> HealthState:
        """处理用户请求并进行任务拆解
        
        这是 Controller_Agent 的核心处理方法。接收 HealthState，执行安全检查，
        将用户请求拆解为三个维度的子任务，并返回更新后的状态。
        
        Args:
            state: 当前的 LangGraph 全局状态，包含 user_query 和 user_profile
        
        Returns:
            HealthState: 更新后的状态，包含：
                - task_breakdown: 子任务列表
                - ui_interrupt_flag: 是否需要 HITL 确认
                - interrupt_reason: 中断原因
                - node_execution_status: 节点执行状态
                - error_info: 错误信息（如有）
                - expert_responses: Controller 的响应（如终止或警告）
        
        Raises:
            无直接抛出异常，所有异常都会被捕获并记录到 error_info
        
        Note:
            - 实现30秒超时限制（Requirement 5.5）
            - 检测禁止关键词时直接终止并返回专业帮助建议（Requirement 5.4）
            - 检测高风险关键词时设置 ui_interrupt_flag=True（Requirement 5.3）
            - 超出范围的请求直接终止并返回原因（Requirement 5.4）
        """
        # 更新节点执行状态为运行中
        state = self._update_node_status(state, NodeExecutionStatus.RUNNING)
        
        try:
            # 使用 asyncio.timeout 实现30秒超时（Requirement 5.5）
            async with asyncio.timeout(CONTROLLER_TIMEOUT_SECONDS):
                return await self._process_internal(state)
        except asyncio.TimeoutError:
            # 超时处理（Requirement 5.5）
            return self._handle_timeout(state)
        except Exception as e:
            # 异常处理
            return self._handle_exception(state, e)
    
    async def _process_internal(self, state: HealthState) -> HealthState:
        """内部处理逻辑
        
        Args:
            state: 当前状态
        
        Returns:
            HealthState: 更新后的状态
        """
        # Requirement 5.1: 从 Health_State 读取 user_profile 信息
        user_query = state.get("user_query", "")
        user_profile = state.get("user_profile")
        
        # 初始化响应字典（如果不存在）
        if "expert_responses" not in state:
            state["expert_responses"] = {}
        
        # 初始化错误信息列表（如果不存在）
        if "error_info" not in state:
            state["error_info"] = []
        
        # 默认不需要中断
        state["ui_interrupt_flag"] = False
        state["interrupt_reason"] = ""
        
        # 执行安全检查
        safety_result = perform_safety_check(user_query)
        
        # Requirement 5.4: 检测禁止关键词 - 需要终止并返回专业帮助建议
        if safety_result.get("terminate") and safety_result.get("prohibited_keywords"):
            return self._handle_prohibited_content(state, safety_result)
        
        # Requirement 5.4: 检测超出服务范围 - 需要终止
        if safety_result.get("terminate") and safety_result.get("out_of_scope_reason"):
            return self._handle_out_of_scope(state, safety_result)
        
        # Requirement 5.3: 检测高风险关键词 - 设置 ui_interrupt_flag
        if safety_result.get("ui_interrupt_flag"):
            state = self._handle_high_risk_content(state, safety_result)
        
        # Requirement 5.2: 将请求拆解为三个维度的子任务
        task_breakdown = self._create_task_breakdown(user_query, user_profile)
        state["task_breakdown"] = task_breakdown
        
        # 更新 Controller 响应
        state["expert_responses"]["controller"] = self._generate_controller_response(
            task_breakdown, safety_result
        )
        
        # 更新节点状态为完成
        state = self._update_node_status(state, NodeExecutionStatus.COMPLETED)
        
        return state
    
    def _handle_prohibited_content(
        self, state: HealthState, safety_result: dict
    ) -> HealthState:
        """处理检测到禁止关键词的情况
        
        Requirement 5.4: 精神科范畴问题需终止并返回专业帮助建议
        
        Args:
            state: 当前状态
            safety_result: 安全检查结果
        
        Returns:
            HealthState: 更新后的状态（已终止）
        """
        message = safety_result.get("message", get_professional_help_suggestion())
        prohibited_keywords = safety_result.get("prohibited_keywords", [])
        
        # 设置 Controller 响应为专业帮助建议
        state["expert_responses"]["controller"] = message
        
        # 设置中断原因（虽然会终止，但记录原因）
        state["interrupt_reason"] = f"检测到禁止关键词：{', '.join(prohibited_keywords)}"
        
        # 清空任务分解（不继续处理）
        state["task_breakdown"] = []
        
        # 更新节点状态为完成（终止也是一种完成）
        state = self._update_node_status(state, NodeExecutionStatus.COMPLETED)
        
        # 设置一个特殊标志表示需要终止（由工作流读取）
        state["ui_interrupt_flag"] = False  # 不需要用户确认，直接终止
        
        return state
    
    def _handle_out_of_scope(
        self, state: HealthState, safety_result: dict
    ) -> HealthState:
        """处理超出服务范围的请求
        
        Requirement 5.4: 超出系统能力范围的请求需终止并返回原因
        
        Args:
            state: 当前状态
            safety_result: 安全检查结果
        
        Returns:
            HealthState: 更新后的状态（已终止）
        """
        reason = safety_result.get("out_of_scope_reason", "")
        message = safety_result.get("message", reason)
        
        # 设置 Controller 响应为超出范围说明
        state["expert_responses"]["controller"] = message
        
        # 设置中断原因
        state["interrupt_reason"] = f"超出服务范围：{reason}"
        
        # 清空任务分解（不继续处理）
        state["task_breakdown"] = []
        
        # 更新节点状态为完成
        state = self._update_node_status(state, NodeExecutionStatus.COMPLETED)
        
        return state
    
    def _handle_high_risk_content(
        self, state: HealthState, safety_result: dict
    ) -> HealthState:
        """处理检测到高风险关键词的情况
        
        Requirement 5.3: 高风险关键词需设置 ui_interrupt_flag=True
        
        Args:
            state: 当前状态
            safety_result: 安全检查结果
        
        Returns:
            HealthState: 更新后的状态（设置了中断标志）
        """
        high_risk_keywords = safety_result.get("high_risk_keywords", [])
        
        # 设置中断标志
        state["ui_interrupt_flag"] = True
        state["interrupt_reason"] = (
            f"检测到高风险内容（{', '.join(high_risk_keywords)}），需要您确认后继续"
        )
        
        return state
    
    def _create_task_breakdown(
        self, user_query: str, user_profile
    ) -> List[SubTask]:
        """创建任务拆解
        
        Requirement 5.2: 将请求拆解为营养、康复、神经心理三个维度的子任务
        
        Args:
            user_query: 用户查询文本
            user_profile: 用户画像对象
        
        Returns:
            List[SubTask]: 三个子任务列表
        """
        # 生成唯一的任务ID前缀
        task_prefix = str(uuid.uuid4())[:8]
        
        # 提取用户画像的关键信息用于任务描述
        profile_context = self._extract_profile_context(user_profile)
        
        # 创建三个维度的子任务
        subtasks = [
            SubTask(
                task_id=f"{task_prefix}-nutrition",
                target_agent=TargetAgent.NUTRITION,
                task_description=self._generate_nutrition_task_description(
                    user_query, profile_context
                ),
            ),
            SubTask(
                task_id=f"{task_prefix}-rehabilitation",
                target_agent=TargetAgent.REHABILITATION,
                task_description=self._generate_rehabilitation_task_description(
                    user_query, profile_context
                ),
            ),
            SubTask(
                task_id=f"{task_prefix}-neuropsychology",
                target_agent=TargetAgent.NEUROPSYCHOLOGY,
                task_description=self._generate_neuropsychology_task_description(
                    user_query, profile_context
                ),
            ),
        ]
        
        return subtasks
    
    def _extract_profile_context(self, user_profile) -> dict:
        """从用户画像中提取关键上下文信息
        
        Args:
            user_profile: 用户画像对象
        
        Returns:
            dict: 关键上下文信息
        """
        if user_profile is None:
            return {}
        
        context = {}
        
        # 基础信息
        if hasattr(user_profile, "age"):
            context["age"] = user_profile.age
        if hasattr(user_profile, "gender"):
            context["gender"] = str(user_profile.gender.value) if hasattr(user_profile.gender, 'value') else str(user_profile.gender)
        
        # BMI
        if hasattr(user_profile, "bmi"):
            context["bmi"] = user_profile.bmi
        elif hasattr(user_profile, "height") and hasattr(user_profile, "weight"):
            height_m = user_profile.height / 100
            if height_m > 0:
                context["bmi"] = round(user_profile.weight / (height_m ** 2), 2)
        
        # 病史
        if hasattr(user_profile, "medical_history") and user_profile.medical_history:
            context["medical_history"] = [
                h.disease_name if hasattr(h, 'disease_name') else str(h)
                for h in user_profile.medical_history
            ]
        
        # 用药史
        if hasattr(user_profile, "medications") and user_profile.medications:
            context["medications"] = [
                m.drug_name if hasattr(m, 'drug_name') else str(m)
                for m in user_profile.medications
            ]
        
        # 体检指标
        if hasattr(user_profile, "physical_examination"):
            pe = user_profile.physical_examination
            if hasattr(pe, "blood_lipids"):
                bl = pe.blood_lipids
                context["blood_lipids"] = {
                    "total_cholesterol": getattr(bl, "total_cholesterol", None),
                    "triglycerides": getattr(bl, "triglycerides", None),
                    "hdl": getattr(bl, "hdl", None),
                    "ldl": getattr(bl, "ldl", None),
                }
            if hasattr(pe, "blood_glucose"):
                bg = pe.blood_glucose
                context["blood_glucose"] = {
                    "fasting_glucose": getattr(bg, "fasting_glucose", None),
                    "hba1c": getattr(bg, "hba1c", None),
                }
        
        # 生活方式
        if hasattr(user_profile, "lifestyle"):
            ls = user_profile.lifestyle
            context["lifestyle"] = {
                "sleep_duration": getattr(ls, "sleep_duration", None),
                "exercise_frequency": str(getattr(ls, "exercise_frequency", "")),
                "diet_habit": str(getattr(ls, "diet_habit", "")),
                "stress_level": getattr(ls, "stress_level", None),
            }
        
        return context
    
    def _generate_nutrition_task_description(
        self, user_query: str, profile_context: dict
    ) -> str:
        """生成营养子任务描述
        
        Args:
            user_query: 用户查询
            profile_context: 用户画像上下文
        
        Returns:
            str: 营养子任务描述
        """
        description_parts = [f"基于用户查询「{user_query}」，分析并提供营养和饮食相关建议。"]
        
        # 添加血脂血糖信息
        if "blood_lipids" in profile_context:
            bl = profile_context["blood_lipids"]
            description_parts.append(
                f"血脂指标：总胆固醇{bl.get('total_cholesterol')}mmol/L，"
                f"甘油三酯{bl.get('triglycerides')}mmol/L，"
                f"HDL{bl.get('hdl')}mmol/L，LDL{bl.get('ldl')}mmol/L。"
            )
        
        if "blood_glucose" in profile_context:
            bg = profile_context["blood_glucose"]
            description_parts.append(
                f"血糖指标：空腹血糖{bg.get('fasting_glucose')}mmol/L，"
                f"糖化血红蛋白{bg.get('hba1c')}%。"
            )
        
        # 添加用药信息
        if "medications" in profile_context:
            meds = profile_context["medications"]
            description_parts.append(f"当前用药：{', '.join(meds)}，请注意药物-食物交互。")
        
        return " ".join(description_parts)
    
    def _generate_rehabilitation_task_description(
        self, user_query: str, profile_context: dict
    ) -> str:
        """生成康复子任务描述
        
        Args:
            user_query: 用户查询
            profile_context: 用户画像上下文
        
        Returns:
            str: 康复子任务描述
        """
        description_parts = [f"基于用户查询「{user_query}」，分析并提供运动和康复相关建议。"]
        
        # 添加年龄和BMI信息
        if "age" in profile_context:
            description_parts.append(f"用户年龄：{profile_context['age']}岁。")
        
        if "bmi" in profile_context:
            description_parts.append(f"BMI：{profile_context['bmi']}。")
        
        # 添加病史禁忌
        if "medical_history" in profile_context:
            diseases = profile_context["medical_history"]
            description_parts.append(f"既往病史：{', '.join(diseases)}，请注意运动禁忌。")
        
        # 添加运动习惯
        if "lifestyle" in profile_context:
            ls = profile_context["lifestyle"]
            if ls.get("exercise_frequency"):
                description_parts.append(f"当前运动频率：{ls['exercise_frequency']}。")
        
        return " ".join(description_parts)
    
    def _generate_neuropsychology_task_description(
        self, user_query: str, profile_context: dict
    ) -> str:
        """生成神经心理子任务描述
        
        Args:
            user_query: 用户查询
            profile_context: 用户画像上下文
        
        Returns:
            str: 神经心理子任务描述
        """
        description_parts = [f"基于用户查询「{user_query}」，分析并提供心理调节和睡眠相关建议。"]
        
        # 添加压力和睡眠信息
        if "lifestyle" in profile_context:
            ls = profile_context["lifestyle"]
            if ls.get("stress_level"):
                description_parts.append(f"压力水平：{ls['stress_level']}/10。")
            if ls.get("sleep_duration"):
                description_parts.append(f"睡眠时长：{ls['sleep_duration']}小时。")
        
        return " ".join(description_parts)
    
    def _generate_controller_response(
        self, task_breakdown: List[SubTask], safety_result: dict
    ) -> str:
        """生成 Controller 响应内容
        
        Args:
            task_breakdown: 任务拆解结果
            safety_result: 安全检查结果
        
        Returns:
            str: Controller 响应文本
        """
        response_parts = ["任务拆解完成。"]
        
        if task_breakdown:
            response_parts.append(f"已创建 {len(task_breakdown)} 个子任务：")
            for task in task_breakdown:
                agent_name = {
                    TargetAgent.NUTRITION: "营养专家",
                    TargetAgent.REHABILITATION: "康复专家",
                    TargetAgent.NEUROPSYCHOLOGY: "神经心理专家",
                }.get(task.target_agent, str(task.target_agent))
                response_parts.append(f"- {agent_name}：{task.task_description[:50]}...")
        
        if safety_result.get("ui_interrupt_flag"):
            response_parts.append(
                f"注意：检测到高风险内容，需要用户确认后继续。"
            )
        
        return "\n".join(response_parts)
    
    def _handle_timeout(self, state: HealthState) -> HealthState:
        """处理超时情况
        
        Requirement 5.5: 超过30秒未完成则终止并记录错误状态
        
        Args:
            state: 当前状态
        
        Returns:
            HealthState: 更新后的状态（包含超时错误）
        """
        error_info = ErrorInfo(
            node_name=self.name,
            error_type="timeout",
            error_message=f"Controller_Agent 处理超时（超过{CONTROLLER_TIMEOUT_SECONDS}秒）",
            timestamp=_utc_now(),
        )
        
        if "error_info" not in state:
            state["error_info"] = []
        state["error_info"].append(error_info)
        
        # 设置响应
        if "expert_responses" not in state:
            state["expert_responses"] = {}
        state["expert_responses"]["controller"] = "处理超时，请稍后重试"
        
        # 清空任务分解
        state["task_breakdown"] = []
        
        # 更新节点状态为失败
        state = self._update_node_status(state, NodeExecutionStatus.FAILED)
        
        return state
    
    def _handle_exception(self, state: HealthState, exception: Exception) -> HealthState:
        """处理异常情况
        
        Args:
            state: 当前状态
            exception: 捕获的异常
        
        Returns:
            HealthState: 更新后的状态（包含异常错误）
        """
        error_info = ErrorInfo(
            node_name=self.name,
            error_type=type(exception).__name__,
            error_message=str(exception)[:1000],  # 限制错误消息长度
            timestamp=_utc_now(),
        )
        
        if "error_info" not in state:
            state["error_info"] = []
        state["error_info"].append(error_info)
        
        # 设置响应
        if "expert_responses" not in state:
            state["expert_responses"] = {}
        state["expert_responses"]["controller"] = f"处理过程中发生错误：{str(exception)[:100]}"
        
        # 清空任务分解
        state["task_breakdown"] = []
        
        # 更新节点状态为失败
        state = self._update_node_status(state, NodeExecutionStatus.FAILED)
        
        return state
    
    def _update_node_status(
        self, state: HealthState, status: NodeExecutionStatus
    ) -> HealthState:
        """更新节点执行状态
        
        Args:
            state: 当前状态
            status: 新的执行状态
        
        Returns:
            HealthState: 更新后的状态
        """
        if "node_execution_status" not in state:
            state["node_execution_status"] = {}
        
        state["node_execution_status"][self.name] = status
        
        return state
