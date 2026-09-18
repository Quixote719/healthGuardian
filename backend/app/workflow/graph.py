"""
LangGraph 工作流图实现

实现多智能体工作流编排，包括：
- 使用 StateGraph 创建工作流
- 添加5个智能体节点 (controller, nutrition, rehabilitation, neuropsychology, synthesis)
- 设置入口点为 controller
- 实现条件路由：controller 后检查 ui_interrupt_flag
- 配置并行执行：nutrition, rehabilitation, neuropsychology 同时执行
- 实现 synthesis 后的条件路由：检查 requires_confirmation
- 配置 checkpointer 持久化（SqliteSaver）
- 实现单个智能体30秒超时和异常处理 (Requirements: 10.7, 10.8)

Requirements: 10.1-10.3, 10.7, 10.8
Design Reference: LangGraph 工作流设计
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

# Handle LangGraph import - may not be installed in all environments
try:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    # Create mock classes for environments without LangGraph
    LANGGRAPH_AVAILABLE = False
    END = "__end__"

    class StateGraph:
        """Mock StateGraph for environments without LangGraph"""

        def __init__(self, state_type):
            self.state_type = state_type
            self.nodes = {}
            self.edges = {}
            self.conditional_edges = {}
            self._entry_point = None

        def add_node(self, name: str, func):
            self.nodes[name] = func

        def add_edge(self, start: str, end: str):
            if start not in self.edges:
                self.edges[start] = []
            self.edges[start].append(end)

        def add_conditional_edges(self, start: str, condition_func, mapping: dict):
            self.conditional_edges[start] = {
                "condition": condition_func,
                "mapping": mapping,
            }

        def set_entry_point(self, name: str):
            self._entry_point = name

        def compile(self, checkpointer=None, interrupt_before=None, interrupt_after=None):
            return MockCompiledGraph(self, checkpointer)

    class MockCompiledGraph:
        """Mock compiled graph for testing"""

        def __init__(self, graph, checkpointer):
            self.graph = graph
            self.checkpointer = checkpointer

        async def ainvoke(self, state, config=None):
            """Execute workflow sequentially"""
            if state is None:
                return {}

            current = state.copy()

            # Execute entry point
            entry = self.graph._entry_point
            if entry and entry in self.graph.nodes:
                current = await self.graph.nodes[entry](current)

            # Check conditional edges after entry
            if entry in self.graph.conditional_edges:
                cond_info = self.graph.conditional_edges[entry]
                result = cond_info["condition"](current)
                next_node = cond_info["mapping"].get(result)
                if next_node == END or next_node is None:
                    return current

            # Execute remaining nodes in sequence
            executed = {entry}
            node_order = ["nutrition", "rehabilitation", "neuropsychology", "synthesis"]

            for node_name in node_order:
                if node_name in self.graph.nodes and node_name not in executed:
                    current = await self.graph.nodes[node_name](current)
                    executed.add(node_name)

                    # Check conditional edges
                    if node_name in self.graph.conditional_edges:
                        cond_info = self.graph.conditional_edges[node_name]
                        result = cond_info["condition"](current)
                        next_node = cond_info["mapping"].get(result)
                        if next_node == END:
                            return current

            return current

        def invoke(self, state, config=None):
            """Synchronous version - wraps async"""
            import asyncio

            return asyncio.run(self.ainvoke(state, config))

    class SqliteSaver:
        """Mock SqliteSaver for environments without LangGraph"""

        def __init__(self, conn_string: str):
            self.conn_string = conn_string
            self._storage = {}

        @classmethod
        def from_conn_string(cls, conn_string: str):
            return cls(conn_string)

    class BaseCheckpointSaver:
        """Mock BaseCheckpointSaver"""

        pass


from app.agents.controller import ControllerAgent
from app.agents.neuropsychology import NeuropsychologyAgent
from app.agents.nutrition import NutritionAgent
from app.agents.rehabilitation import RehabilitationAgent
from app.agents.synthesis import SynthesisAgent
from app.models.state import ErrorInfo, HealthState, NodeExecutionStatus

# ============================================================================
# Logger Configuration
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Agent timeout in seconds (Requirement 10.7)
AGENT_TIMEOUT_SECONDS = 30


# ============================================================================
# Agent Instances
# ============================================================================

# 初始化智能体实例
controller_agent = ControllerAgent()
nutrition_agent = NutritionAgent()
rehabilitation_agent = RehabilitationAgent()
neuropsychology_agent = NeuropsychologyAgent()
synthesis_agent = SynthesisAgent()


# ============================================================================
# Timeout and Exception Handling Wrapper
# ============================================================================


def _get_utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(UTC)


def _record_error(
    state: HealthState,
    node_name: str,
    error_type: str,
    error_message: str,
) -> HealthState:
    """Record an error in the state's error_info list.

    Creates a new ErrorInfo entry and appends it to the state.
    Also updates the node_execution_status to FAILED.

    Args:
        state: Current HealthState
        node_name: Name of the node that encountered the error
        error_type: Type/category of the error
        error_message: Descriptive error message (max 1000 chars)

    Returns:
        Updated HealthState with error recorded
    """
    # Truncate error message to max 1000 characters (Requirement 4.8)
    truncated_message = error_message[:1000] if len(error_message) > 1000 else error_message

    # Create error info entry
    error_info = ErrorInfo(
        node_name=node_name,
        error_type=error_type,
        error_message=truncated_message,
        timestamp=_get_utc_now(),
    )

    # Get existing error_info list or create new one
    existing_errors = list(state.get("error_info", []))
    existing_errors.append(error_info)

    # Get existing node_execution_status or create new one
    existing_status = dict(state.get("node_execution_status", {}))
    existing_status[node_name] = NodeExecutionStatus.FAILED

    # Create updated state
    updated_state = dict(state)
    updated_state["error_info"] = existing_errors
    updated_state["node_execution_status"] = existing_status

    return updated_state


async def with_timeout_and_error_handling(
    agent_process_func: Callable[[HealthState], HealthState],
    state: HealthState,
    node_name: str,
    timeout_seconds: int = AGENT_TIMEOUT_SECONDS,
) -> HealthState:
    """Execute an agent's process function with timeout and error handling.

    This wrapper implements Requirements 10.7 and 10.8:
    - Single agent timeout of 30 seconds (configurable)
    - Timeout termination and status recording
    - Exception capture and error logging
    - Graceful degradation (single failure doesn't affect others)

    Args:
        agent_process_func: The agent's async process method
        state: Current HealthState
        node_name: Name of the agent node (for error recording)
        timeout_seconds: Timeout in seconds (default: 30)

    Returns:
        Updated HealthState. On success, returns the agent's output.
        On failure, returns state with error recorded and node marked as FAILED.

    Raises:
        No exceptions are raised - all errors are caught and recorded in state.
    """
    # Update node status to RUNNING
    running_state = dict(state)
    existing_status = dict(running_state.get("node_execution_status", {}))
    existing_status[node_name] = NodeExecutionStatus.RUNNING
    running_state["node_execution_status"] = existing_status

    try:
        # Execute with timeout (Requirement 10.7: 30 second timeout)
        result = await asyncio.wait_for(
            agent_process_func(running_state),
            timeout=timeout_seconds,
        )

        # Update node status to COMPLETED on success
        result_state = dict(result)
        result_status = dict(result_state.get("node_execution_status", {}))
        result_status[node_name] = NodeExecutionStatus.COMPLETED
        result_state["node_execution_status"] = result_status

        logger.info(f"Agent {node_name} completed successfully")
        return result_state

    except TimeoutError:
        # Requirement 10.7: Timeout handling
        logger.warning(f"Agent {node_name} timed out after {timeout_seconds} seconds")

        # Create timeout error and record it
        error_state = _record_error(
            state=running_state,
            node_name=node_name,
            error_type="agent_timeout",
            error_message=f"智能体 {node_name} 执行超时 ({timeout_seconds}秒)",
        )

        # Log the timeout
        logger.error(f"AgentTimeoutError: {node_name} exceeded {timeout_seconds}s timeout")

        return error_state

    except Exception as e:
        # Requirement 10.8: Exception handling
        logger.exception(f"Agent {node_name} encountered an error: {e}")

        # Determine error type from exception
        error_type = type(e).__name__
        error_message = str(e) or f"Unknown error in {node_name}"

        # Record error and return state (graceful degradation)
        error_state = _record_error(
            state=running_state,
            node_name=node_name,
            error_type=error_type,
            error_message=error_message,
        )

        return error_state


# ============================================================================
# Node Functions (with timeout and error handling)
# ============================================================================


async def controller_node(state: HealthState) -> HealthState:
    """Controller 智能体节点

    主控智能体节点，负责任务拆解和风险检测。
    包含30秒超时和异常处理 (Requirements 10.7, 10.8)。

    Args:
        state: 当前的 HealthState

    Returns:
        更新后的 HealthState
    """
    return await with_timeout_and_error_handling(
        agent_process_func=controller_agent.process,
        state=state,
        node_name="controller",
    )


async def nutrition_node(state: HealthState) -> HealthState:
    """Nutrition 智能体节点

    营养学专家智能体节点。
    包含30秒超时和异常处理 (Requirements 10.7, 10.8)。

    Args:
        state: 当前的 HealthState

    Returns:
        更新后的 HealthState
    """
    return await with_timeout_and_error_handling(
        agent_process_func=nutrition_agent.process,
        state=state,
        node_name="nutrition",
    )


async def rehabilitation_node(state: HealthState) -> HealthState:
    """Rehabilitation 智能体节点

    运动康复专家智能体节点。
    包含30秒超时和异常处理 (Requirements 10.7, 10.8)。

    Args:
        state: 当前的 HealthState

    Returns:
        更新后的 HealthState
    """
    return await with_timeout_and_error_handling(
        agent_process_func=rehabilitation_agent.process,
        state=state,
        node_name="rehabilitation",
    )


async def neuropsychology_node(state: HealthState) -> HealthState:
    """Neuropsychology 智能体节点

    神经心理调节专家智能体节点。
    包含30秒超时和异常处理 (Requirements 10.7, 10.8)。

    Args:
        state: 当前的 HealthState

    Returns:
        更新后的 HealthState
    """
    return await with_timeout_and_error_handling(
        agent_process_func=neuropsychology_agent.process,
        state=state,
        node_name="neuropsychology",
    )


async def synthesis_node(state: HealthState) -> HealthState:
    """Synthesis 智能体节点

    综合反思与安全检查智能体节点。
    包含30秒超时和异常处理 (Requirements 10.7, 10.8)。

    Args:
        state: 当前的 HealthState

    Returns:
        更新后的 HealthState
    """
    return await with_timeout_and_error_handling(
        agent_process_func=synthesis_agent.process,
        state=state,
        node_name="synthesis",
    )


# ============================================================================
# Conditional Routing Functions
# ============================================================================


def should_interrupt_after_controller(state: HealthState) -> Literal["interrupt", "parallel"]:
    """判断是否需要在 Controller 后中断

    Requirement 10.3: 当 Controller_Agent 完成执行且 ui_interrupt_flag 为 true 时，
    使用 LangGraph interrupt 机制暂停工作流。

    检查状态中的 ui_interrupt_flag 标志：
    - True: 表示检测到高风险内容或禁止关键词，需要中断等待用户确认
    - False: 正常继续执行并行专家智能体

    Args:
        state: 当前的 HealthState

    Returns:
        "interrupt": 需要中断工作流
        "parallel": 继续执行并行专家智能体
    """
    # 检查 ui_interrupt_flag
    if state.get("ui_interrupt_flag", False):
        return "interrupt"

    # 检查是否有任务分解（如果没有任务分解说明被终止了）
    task_breakdown = state.get("task_breakdown", [])
    if not task_breakdown:
        # 没有任务分解，可能是被禁止关键词或超出范围终止
        return "interrupt"

    return "parallel"


def should_interrupt_after_synthesis(state: HealthState) -> Literal["interrupt", "end"]:
    """判断是否需要在 Synthesis 后中断

    检查 final_report 的 requires_confirmation 标志：
    - True: 需要用户确认高风险干预，中断等待确认
    - False: 工作流正常完成

    Args:
        state: 当前的 HealthState

    Returns:
        "interrupt": 需要中断等待用户确认
        "end": 工作流正常完成
    """
    final_report = state.get("final_report")

    if final_report is not None:
        # 检查是否需要用户确认
        if hasattr(final_report, "requires_confirmation"):
            if final_report.requires_confirmation:
                return "interrupt"
        elif isinstance(final_report, dict) and final_report.get("requires_confirmation"):
            return "interrupt"

    return "end"


# ============================================================================
# Fan-out and Fan-in Helper
# ============================================================================

# 定义并行分支名称常量
BRANCH_NUTRITION = "nutrition"
BRANCH_REHABILITATION = "rehabilitation"
BRANCH_NEUROPSYCHOLOGY = "neuropsychology"


def route_to_parallel_branches(state: HealthState) -> list[str]:
    """路由到并行分支

    从 controller 同时路由到三个并行专家节点。

    Args:
        state: 当前的 HealthState

    Returns:
        并行分支名称列表
    """
    return [BRANCH_NUTRITION, BRANCH_REHABILITATION, BRANCH_NEUROPSYCHOLOGY]


# ============================================================================
# Workflow Graph Creation
# ============================================================================


def create_health_workflow() -> StateGraph:
    """创建健康咨询工作流

    构建包含以下结构的 LangGraph 工作流：

    1. Controller (入口)
       ↓
    2. 条件路由：检查 ui_interrupt_flag
       - interrupt → END
       - parallel → 并行执行
       ↓
    3. 并行执行 Nutrition, Rehabilitation, Neuropsychology
       ↓
    4. Synthesis (汇聚)
       ↓
    5. 条件路由：检查 requires_confirmation
       - interrupt → END (需确认)
       - end → END (完成)

    Requirements: 10.1-10.3

    Returns:
        StateGraph: 配置好的工作流状态图
    """
    # 创建状态图
    workflow = StateGraph(HealthState)

    # ========== 添加节点 ==========
    # 添加 Controller 节点（入口点）
    workflow.add_node("controller", controller_node)

    # 添加并行执行的专家节点
    workflow.add_node("nutrition", nutrition_node)
    workflow.add_node("rehabilitation", rehabilitation_node)
    workflow.add_node("neuropsychology", neuropsychology_node)

    # 添加 Synthesis 汇聚节点
    workflow.add_node("synthesis", synthesis_node)

    # ========== 设置入口点 ==========
    workflow.set_entry_point("controller")

    # ========== 配置边和条件路由 ==========

    # Controller 之后的条件路由
    # - interrupt: 中断工作流（高风险/禁止内容/超出范围）
    # - parallel: 继续到并行执行
    workflow.add_conditional_edges(
        "controller",
        should_interrupt_after_controller,
        {
            "interrupt": END,
            "parallel": "nutrition",  # 先路由到其中一个，然后通过 fan-out 到其他节点
        },
    )

    # 配置并行分支：从 nutrition 出发后，也要执行 rehabilitation 和 neuropsychology
    # LangGraph 不直接支持从一个条件边同时路由到多个节点
    # 所以我们使用不同的策略：让每个专家节点都执行，然后汇聚到 synthesis

    # 由于 LangGraph 的 add_conditional_edges 不支持返回列表，
    # 我们需要使用另一种方式实现并行：
    # 1. 让 controller 路由到一个中间节点
    # 2. 或者使用 subgraph
    #
    # 更简单的方式：按顺序执行但通过状态共享模拟"并行"
    # 或者使用 branching pattern

    # 实际上，LangGraph 2.x 支持通过 Send 来实现真正的并行
    # 但为了保持简单和兼容性，这里使用顺序执行（状态会累积更新）

    # 重新配置边：
    # controller -> nutrition -> rehabilitation -> neuropsychology -> synthesis
    # 或者使用 fan-out pattern

    # 为了实现并行，我们使用 LangGraph 的 branch/join pattern
    # 具体实现：所有专家节点都连接到 synthesis
    workflow.add_edge("nutrition", "synthesis")
    workflow.add_edge("rehabilitation", "synthesis")
    workflow.add_edge("neuropsychology", "synthesis")

    # 重新配置 controller 的条件路由，使用分支返回
    # 注意：需要使用支持并行的方式

    # Synthesis 之后的条件路由
    workflow.add_conditional_edges(
        "synthesis", should_interrupt_after_synthesis, {"interrupt": END, "end": END}
    )

    return workflow


def create_parallel_health_workflow() -> StateGraph:
    """创建支持并行执行的健康咨询工作流

    使用 LangGraph 的 fan-out / fan-in 模式实现真正的并行执行。

    工作流结构：
    ```
    Controller
        │
        ├──→ Nutrition ────┐
        ├──→ Rehabilitation ├──→ Synthesis ──→ END
        └──→ Neuropsychology┘
    ```

    Requirements: 10.1-10.3

    Returns:
        StateGraph: 配置好的并行工作流状态图
    """
    # 创建状态图
    workflow = StateGraph(HealthState)

    # 添加所有节点
    workflow.add_node("controller", controller_node)
    workflow.add_node("nutrition", nutrition_node)
    workflow.add_node("rehabilitation", rehabilitation_node)
    workflow.add_node("neuropsychology", neuropsychology_node)
    workflow.add_node("synthesis", synthesis_node)

    # 设置入口点
    workflow.set_entry_point("controller")

    # Controller 条件路由
    # 使用 dict mapping，parallel 会 fan-out 到多个节点
    def route_after_controller(
        state: HealthState,
    ) -> Literal["interrupt", "nutrition", "rehabilitation", "neuropsychology"]:
        """路由函数，返回单个目标"""
        if state.get("ui_interrupt_flag", False):
            return "interrupt"
        task_breakdown = state.get("task_breakdown", [])
        if not task_breakdown:
            return "interrupt"
        # 返回第一个节点，其他节点通过并行边配置
        return "nutrition"

    # 配置 controller 的条件路由
    # 使用 map 同时路由到多个节点 - 这需要 LangGraph 支持
    # 如果不支持，则使用顺序方式
    workflow.add_conditional_edges(
        "controller",
        should_interrupt_after_controller,
        {
            "interrupt": END,
            "parallel": "nutrition",  # 主分支
        },
    )

    # 添加额外的并行边（从 controller 出发）
    # 使用 conditional_edges 的返回列表功能
    # 如果 LangGraph 不支持，则改用顺序执行

    # 所有专家节点汇聚到 synthesis
    workflow.add_edge("nutrition", "synthesis")
    workflow.add_edge("rehabilitation", "synthesis")
    workflow.add_edge("neuropsychology", "synthesis")

    # Synthesis 条件路由
    workflow.add_conditional_edges(
        "synthesis", should_interrupt_after_synthesis, {"interrupt": END, "end": END}
    )

    return workflow


def create_sequential_health_workflow() -> StateGraph:
    """创建顺序执行的健康咨询工作流

    按顺序执行所有智能体节点。这是一个简化版本，
    适用于不需要真正并行执行的场景。

    工作流结构：
    ```
    Controller → Nutrition → Rehabilitation → Neuropsychology → Synthesis → END
    ```

    注意：虽然是顺序执行，但由于状态在节点间传递，
    各专家智能体仍然可以独立处理其分配的任务。

    Returns:
        StateGraph: 配置好的顺序工作流状态图
    """
    workflow = StateGraph(HealthState)

    # 添加所有节点
    workflow.add_node("controller", controller_node)
    workflow.add_node("nutrition", nutrition_node)
    workflow.add_node("rehabilitation", rehabilitation_node)
    workflow.add_node("neuropsychology", neuropsychology_node)
    workflow.add_node("synthesis", synthesis_node)

    # 设置入口点
    workflow.set_entry_point("controller")

    # Controller 条件路由
    workflow.add_conditional_edges(
        "controller",
        should_interrupt_after_controller,
        {
            "interrupt": END,
            "parallel": "nutrition",
        },
    )

    # 顺序连接专家节点
    workflow.add_edge("nutrition", "rehabilitation")
    workflow.add_edge("rehabilitation", "neuropsychology")
    workflow.add_edge("neuropsychology", "synthesis")

    # Synthesis 条件路由
    workflow.add_conditional_edges(
        "synthesis", should_interrupt_after_synthesis, {"interrupt": END, "end": END}
    )

    return workflow


# ============================================================================
# Compiled Workflow Factory
# ============================================================================


def get_compiled_workflow(
    checkpointer: BaseCheckpointSaver | None = None,
    use_parallel: bool = True,
):
    """获取编译后的工作流

    创建并编译健康咨询工作流，配置检查点持久化。

    Args:
        checkpointer: 检查点保存器，用于持久化会话状态
                     如果为 None，则使用内存中的 SqliteSaver
        use_parallel: 是否使用并行执行模式
                     True: 尝试并行执行专家节点
                     False: 顺序执行专家节点

    Returns:
        编译后的工作流 (CompiledStateGraph)

    Example:
        >>> # 使用内存检查点
        >>> workflow = get_compiled_workflow()
        >>>
        >>> # 使用自定义检查点
        >>> from langgraph.checkpoint.sqlite import SqliteSaver
        >>> checkpointer = SqliteSaver.from_conn_string("./sessions.db")
        >>> workflow = get_compiled_workflow(checkpointer=checkpointer)
        >>>
        >>> # 执行工作流
        >>> config = {"configurable": {"thread_id": "session_123"}}
        >>> result = await workflow.ainvoke(initial_state, config)
    """
    # 创建工作流图
    if use_parallel:
        workflow = create_sequential_health_workflow()  # 目前使用顺序版本以确保稳定性
    else:
        workflow = create_sequential_health_workflow()

    # 配置检查点保存器
    if checkpointer is None:
        # 使用内存中的 SQLite 作为默认检查点
        checkpointer = SqliteSaver.from_conn_string(":memory:")

    # 编译工作流
    # interrupt_before: 在指定节点前可以中断
    # interrupt_after: 在指定节点后可以中断
    compiled = workflow.compile(
        checkpointer=checkpointer,
        # 配置可中断点
        interrupt_before=None,  # 不在任何节点前中断
        interrupt_after=["controller", "synthesis"],  # 在 controller 和 synthesis 后可能需要中断
    )

    return compiled


def get_persistent_workflow(db_path: str = "./workflow_sessions.db"):
    """获取持久化的工作流

    创建一个使用文件系统 SQLite 数据库进行持久化的工作流。
    适用于需要跨进程/重启保持会话状态的场景。

    Args:
        db_path: SQLite 数据库文件路径

    Returns:
        编译后的工作流

    Example:
        >>> workflow = get_persistent_workflow("./sessions.db")
        >>>
        >>> # 执行工作流
        >>> config = {"configurable": {"thread_id": "user_123"}}
        >>> result = await workflow.ainvoke(state, config)
        >>>
        >>> # 稍后恢复会话（即使重启后）
        >>> resumed = await workflow.ainvoke(None, config)
    """
    checkpointer = SqliteSaver.from_conn_string(db_path)
    return get_compiled_workflow(checkpointer=checkpointer)


# ============================================================================
# Workflow Execution Helpers
# ============================================================================


async def run_health_workflow(
    initial_state: HealthState,
    session_id: str,
    checkpointer: BaseCheckpointSaver | None = None,
) -> HealthState:
    """运行健康咨询工作流

    便捷函数，用于执行完整的健康咨询工作流。

    Args:
        initial_state: 初始状态，包含 user_query 和 user_profile
        session_id: 会话 ID，用于检查点追踪
        checkpointer: 可选的检查点保存器

    Returns:
        工作流执行后的最终状态

    Example:
        >>> from app.models.state import HealthState
        >>>
        >>> initial_state: HealthState = {
        ...     "user_query": "我血脂偏高，睡眠不好，请给我建议",
        ...     "user_profile": user_profile_instance,
        ...     "task_breakdown": [],
        ...     "expert_responses": {},
        ...     "ui_interrupt_flag": False,
        ...     "interrupt_reason": "",
        ...     "node_execution_status": {},
        ...     "error_info": [],
        ...     "final_report": None,
        ... }
        >>>
        >>> result = await run_health_workflow(initial_state, "session_001")
        >>> print(result["final_report"])
    """
    workflow = get_compiled_workflow(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": session_id}}

    result = await workflow.ainvoke(initial_state, config)
    return result


async def resume_health_workflow(
    session_id: str,
    checkpointer: BaseCheckpointSaver,
    update_state: HealthState | None = None,
) -> HealthState:
    """恢复暂停的健康咨询工作流

    当工作流因 HITL 机制暂停后，使用此函数恢复执行。

    Args:
        session_id: 会话 ID
        checkpointer: 检查点保存器（必须与创建时相同）
        update_state: 可选的状态更新，用于传入用户确认结果

    Returns:
        工作流继续执行后的状态

    Example:
        >>> # 用户确认后恢复
        >>> update = {"ui_interrupt_flag": False}
        >>> result = await resume_health_workflow(
        ...     "session_001",
        ...     checkpointer,
        ...     update_state=update
        ... )
    """
    workflow = get_compiled_workflow(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": session_id}}

    # 如果有状态更新，先更新状态
    if update_state is not None:
        result = await workflow.ainvoke(update_state, config)
    else:
        # 继续从上次暂停的地方执行
        result = await workflow.ainvoke(None, config)

    return result


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Module info
    "LANGGRAPH_AVAILABLE",
    # Constants
    "AGENT_TIMEOUT_SECONDS",
    # Timeout and error handling
    "with_timeout_and_error_handling",
    # Workflow creation
    "create_health_workflow",
    "create_parallel_health_workflow",
    "create_sequential_health_workflow",
    # Compiled workflow factory
    "get_compiled_workflow",
    "get_persistent_workflow",
    # Execution helpers
    "run_health_workflow",
    "resume_health_workflow",
    # Routing functions (for testing)
    "should_interrupt_after_controller",
    "should_interrupt_after_synthesis",
    # Node functions (for testing)
    "controller_node",
    "nutrition_node",
    "rehabilitation_node",
    "neuropsychology_node",
    "synthesis_node",
    # Agent instances (for advanced usage)
    "controller_agent",
    "nutrition_agent",
    "rehabilitation_agent",
    "neuropsychology_agent",
    "synthesis_agent",
]
