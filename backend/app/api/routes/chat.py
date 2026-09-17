"""
/chat 流式聊天 API

实现 POST /api/chat 端点，接收用户健康咨询请求并通过 SSE 流式返回结果。

Requirements: 13.1-13.9
- 13.1: 提供 /chat POST 端点接收用户健康咨询请求
- 13.2: 接收包含 user_query 和 user_profile_id 的 JSON 请求体
- 13.3: 使用 SSE 协议实现流式响应
- 13.4: 定义事件类型 (status, intermediate, report, pause, error, heartbeat)
- 13.5: 实时推送 status 和 intermediate 事件
- 13.6: 每15秒推送 heartbeat 事件
- 13.7: 推送 report 事件 (完整的 Final_Report)
- 13.8: 推送 pause 事件 (session_id 和高风险干预内容)
- 13.9: 推送 error 事件 (错误类型和描述)

Design Reference: API 设计 - 流式聊天 API
"""

import asyncio
import logging
import uuid
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.sse_manager import sse_manager, SSEEvent, SSEEventType
from app.models.api import ChatRequest, StatusEventData, PauseEventData, ErrorEventData
from app.models.state import HealthState, NodeExecutionStatus
from app.services.user_profile import get_user_profile
from app.workflow.graph import get_compiled_workflow, LANGGRAPH_AVAILABLE
from app.workflow.hitl import HITLManager


# Setup logging
logger = logging.getLogger(__name__)


# Create router
router = APIRouter()


# Global HITL Manager instance (shared across requests)
hitl_manager = HITLManager()


# ============================================================================
# SSE Event Stream Generator
# ============================================================================


async def generate_sse_stream(
    session_id: str,
    user_query: str,
    user_profile_id: str,
) -> AsyncGenerator[str, None]:
    """生成 SSE 事件流
    
    执行工作流并实时推送事件到客户端。
    
    Requirements: 13.3-13.9
    
    Args:
        session_id: 会话 ID
        user_query: 用户查询文本
        user_profile_id: 用户画像 ID
        
    Yields:
        SSE 格式的事件字符串
    """
    try:
        # ========== 初始化阶段 ==========
        # 推送初始状态事件
        yield SSEEvent(
            event_type=SSEEventType.STATUS,
            data=StatusEventData(
                agent_name="system",
                progress="正在初始化系统...",
                percentage=5,
            ),
        ).to_sse_format()
        
        # 获取用户画像（可能为 None）
        user_profile = await get_user_profile(user_profile_id)
        
        if user_profile is not None:
            yield SSEEvent(
                event_type=SSEEventType.STATUS,
                data=StatusEventData(
                    agent_name="system",
                    progress="已加载用户画像",
                    percentage=10,
                ),
            ).to_sse_format()
        else:
            # 用户画像不存在，静默处理，继续提供通用建议
            yield SSEEvent(
                event_type=SSEEventType.STATUS,
                data=StatusEventData(
                    agent_name="system",
                    progress="准备就绪",
                    percentage=10,
                ),
            ).to_sse_format()
        
        # ========== 初始化工作流状态 ==========
        initial_state: HealthState = {
            "user_query": user_query,
            "user_profile": user_profile,
            "task_breakdown": [],
            "expert_responses": {},
            "ui_interrupt_flag": False,
            "interrupt_reason": "",
            "node_execution_status": {},
            "error_info": [],
            "final_report": None,
        }
        
        # ========== 执行工作流 ==========
        yield SSEEvent(
            event_type=SSEEventType.STATUS,
            data=StatusEventData(
                agent_name="Controller_Agent",
                progress="正在分析请求...",
                percentage=15,
            ),
        ).to_sse_format()
        
        # 获取编译后的工作流
        workflow = get_compiled_workflow()
        
        # 配置工作流执行
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }
        
        # 执行工作流
        try:
            # 根据 LangGraph 可用性选择执行方式
            if LANGGRAPH_AVAILABLE:
                # 使用 LangGraph 的流式执行
                result_state = await _execute_workflow_with_events(
                    workflow=workflow,
                    initial_state=initial_state,
                    config=config,
                    session_id=session_id,
                )
                
                # 通过生成器 yield 事件
                async for event_str in _stream_workflow_events(
                    result_state=result_state,
                    session_id=session_id,
                ):
                    yield event_str
            else:
                # 回退到 Mock 工作流
                result_state = await workflow.ainvoke(initial_state, config)
                
                async for event_str in _stream_workflow_events(
                    result_state=result_state,
                    session_id=session_id,
                ):
                    yield event_str
                    
        except asyncio.TimeoutError:
            yield SSEEvent(
                event_type=SSEEventType.ERROR,
                data=ErrorEventData(
                    error_type="workflow_timeout",
                    error_message="工作流执行超时，请稍后重试",
                ),
            ).to_sse_format()
            return
            
        except Exception as e:
            logger.exception(f"Workflow execution error: {e}")
            yield SSEEvent(
                event_type=SSEEventType.ERROR,
                data=ErrorEventData(
                    error_type="workflow_error",
                    error_message=f"工作流执行错误: {str(e)}",
                ),
            ).to_sse_format()
            return
            
    except Exception as e:
        logger.exception(f"SSE stream error: {e}")
        yield SSEEvent(
            event_type=SSEEventType.ERROR,
            data=ErrorEventData(
                error_type="stream_error",
                error_message=f"流式响应错误: {str(e)}",
            ),
        ).to_sse_format()


async def _execute_workflow_with_events(
    workflow,
    initial_state: HealthState,
    config: dict,
    session_id: str,
) -> HealthState:
    """执行工作流并收集事件
    
    Args:
        workflow: 编译后的工作流
        initial_state: 初始状态
        config: 工作流配置
        session_id: 会话 ID
    
    Returns:
        工作流执行后的最终状态
    """
    # 执行工作流
    result_state = await workflow.ainvoke(initial_state, config)
    return result_state


async def _stream_workflow_events(
    result_state: HealthState,
    session_id: str,
) -> AsyncGenerator[str, None]:
    """根据工作流结果流式输出事件
    
    Args:
        result_state: 工作流执行结果状态
        session_id: 会话 ID
        
    Yields:
        SSE 格式的事件字符串
    """
    # 检查节点执行状态并推送中间事件
    node_status = result_state.get("node_execution_status", {})
    
    # Controller 状态
    if "controller" in node_status:
        status = node_status["controller"]
        yield SSEEvent(
            event_type=SSEEventType.STATUS,
            data=StatusEventData(
                agent_name="Controller_Agent",
                progress="任务拆解完成" if status == NodeExecutionStatus.COMPLETED else f"状态: {status}",
                percentage=25,
            ),
        ).to_sse_format()
    
    # 检查是否在 Controller 之后被中断（没有 final_report，但有 ui_interrupt_flag）
    # 这种情况发生在检测到禁止关键词或超出范围时
    final_report = result_state.get("final_report")
    if result_state.get("ui_interrupt_flag", False) and final_report is None:
        interrupt_reason = result_state.get("interrupt_reason", "检测到需要确认的内容")
        
        # 没有 final_report，可能是被禁止关键词或超出范围拒绝
        # 发送 Controller 的响应作为结果
        controller_response = result_state.get("expert_responses", {}).get("controller", "")
        
        yield SSEEvent(
            event_type=SSEEventType.STATUS,
            data=StatusEventData(
                agent_name="system",
                progress="请求已处理",
                percentage=100,
            ),
        ).to_sse_format()
        
        # 发送 Controller 的响应作为报告
        yield SSEEvent(
            event_type=SSEEventType.REPORT,
            data={
                "deep_insight": controller_response or interrupt_reason,
                "action_plan": [],
                "follow_up": "",
                "requires_confirmation": False,
            },
        ).to_sse_format()
        return
    
    # 专家智能体状态
    agents = [
        ("nutrition", "Nutrition_Agent", 40),
        ("rehabilitation", "Rehabilitation_Agent", 55),
        ("neuropsychology", "Neuropsychology_Agent", 70),
    ]
    
    for node_name, display_name, percentage in agents:
        if node_name in node_status:
            status = node_status[node_name]
            progress = "分析完成" if status == NodeExecutionStatus.COMPLETED else f"状态: {status}"
            
            yield SSEEvent(
                event_type=SSEEventType.STATUS,
                data=StatusEventData(
                    agent_name=display_name,
                    progress=progress,
                    percentage=percentage,
                ),
            ).to_sse_format()
            
            # 推送中间结果 (Requirement 13.5)
            expert_responses = result_state.get("expert_responses", {})
            if node_name in expert_responses:
                yield SSEEvent(
                    event_type=SSEEventType.INTERMEDIATE,
                    data={
                        "agent_name": display_name,
                        "partial_result": expert_responses[node_name][:200] + "..." 
                            if len(expert_responses.get(node_name, "")) > 200 
                            else expert_responses.get(node_name, ""),
                    },
                ).to_sse_format()
    
    # Synthesis 状态
    if "synthesis" in node_status:
        yield SSEEvent(
            event_type=SSEEventType.STATUS,
            data=StatusEventData(
                agent_name="Synthesis_Agent",
                progress="正在综合分析...",
                percentage=85,
            ),
        ).to_sse_format()
    
    # 检查最终报告
    if final_report is not None:
        # 检查是否需要确认（Synthesis 之后）
        requires_confirmation = False
        if hasattr(final_report, "requires_confirmation"):
            requires_confirmation = final_report.requires_confirmation
        elif isinstance(final_report, dict):
            requires_confirmation = final_report.get("requires_confirmation", False)
        
        if requires_confirmation:
            # 获取需要确认的项目（包括高风险和中风险）
            confirmation_items = []
            if hasattr(final_report, "action_plan"):
                for item in final_report.action_plan:
                    if hasattr(item, "risk_level"):
                        risk_str = str(item.risk_level.value) if hasattr(item.risk_level, 'value') else str(item.risk_level)
                        # 筛选高风险和中风险项目
                        if risk_str in ("高风险", "中风险"):
                            if hasattr(item, "model_dump"):
                                confirmation_items.append(item.model_dump())
                            else:
                                confirmation_items.append(item)
            elif isinstance(final_report, dict):
                for item in final_report.get("action_plan", []):
                    if isinstance(item, dict) and item.get("risk_level") in ("高风险", "中风险"):
                        confirmation_items.append(item)
            
            # 暂停工作流
            await hitl_manager.pause_workflow(
                session_id=session_id,
                state=result_state,
                reason="最终报告包含需要确认的干预措施",
                high_risk_items=confirmation_items,
            )
            
            # 推送暂停事件，包含完整报告信息供前端显示
            # 序列化 final_report
            if hasattr(final_report, "model_dump"):
                report_data = final_report.model_dump()
            elif isinstance(final_report, dict):
                report_data = final_report
            else:
                report_data = {"deep_insight": str(final_report)}
            
            yield SSEEvent(
                event_type=SSEEventType.PAUSE,
                data=PauseEventData(
                    session_id=session_id,
                    high_risk_items=confirmation_items,
                    timeout_seconds=600,
                ),
            ).to_sse_format()
            
            # 同时发送报告事件，让前端可以显示报告内容
            yield SSEEvent(
                event_type=SSEEventType.REPORT,
                data=report_data,
            ).to_sse_format()
            return
        
        # 推送最终报告事件 (Requirement 13.7)
        yield SSEEvent(
            event_type=SSEEventType.STATUS,
            data=StatusEventData(
                agent_name="system",
                progress="报告生成完成",
                percentage=100,
            ),
        ).to_sse_format()
        
        # 序列化 final_report
        if hasattr(final_report, "model_dump"):
            report_data = final_report.model_dump()
        elif isinstance(final_report, dict):
            report_data = final_report
        else:
            report_data = str(final_report)
        
        yield SSEEvent(
            event_type=SSEEventType.REPORT,
            data=report_data,
        ).to_sse_format()
    else:
        # 没有最终报告，可能是被中断或出错
        error_info = result_state.get("error_info", [])
        
        if error_info:
            # 有错误信息
            for error in error_info:
                if hasattr(error, "model_dump"):
                    error_data = error.model_dump()
                elif isinstance(error, dict):
                    error_data = error
                else:
                    error_data = {"error_type": "unknown", "error_message": str(error)}
                
                yield SSEEvent(
                    event_type=SSEEventType.ERROR,
                    data=ErrorEventData(
                        error_type=error_data.get("error_type", "unknown"),
                        error_message=error_data.get("error_message", "未知错误"),
                    ),
                ).to_sse_format()
        else:
            # 没有错误信息，推送完成状态
            yield SSEEvent(
                event_type=SSEEventType.STATUS,
                data=StatusEventData(
                    agent_name="system",
                    progress="处理完成（无报告）",
                    percentage=100,
                ),
            ).to_sse_format()


# ============================================================================
# API Endpoint
# ============================================================================


@router.post("/chat")
async def chat(request: ChatRequest):
    """流式聊天端点
    
    Requirements: 13.1-13.9
    - 13.1: 提供 /chat POST 端点接收用户健康咨询请求
    - 13.2: 接收包含 user_query 和 user_profile_id 的 JSON 请求体
    - 13.3: 使用 SSE 协议实现流式响应
    
    Args:
        request: ChatRequest 包含 user_query 和 user_profile_id
    
    Returns:
        StreamingResponse: SSE 流式响应
        
    Response Headers:
        - Content-Type: text/event-stream
        - Cache-Control: no-cache
        - Connection: keep-alive
        - X-Session-ID: 会话 ID
    
    Example:
        POST /api/chat
        {
            "user_query": "我最近血脂偏高，睡眠质量差，请给我一些建议",
            "user_profile_id": "user_123"
        }
        
        Response (SSE stream):
        event: status
        data: {"data": {"agent_name": "Controller_Agent", "progress": "正在分析...", "percentage": 15}, "timestamp": "..."}
        
        event: report
        data: {"data": {...final_report...}, "timestamp": "..."}
    """
    # 生成会话 ID
    session_id = str(uuid.uuid4())
    
    logger.info(
        f"Chat request received: session_id={session_id}, "
        f"user_profile_id={request.user_profile_id}, "
        f"query_length={len(request.user_query)}"
    )
    
    # 返回 SSE 流式响应
    return StreamingResponse(
        generate_sse_stream(
            session_id=session_id,
            user_query=request.user_query,
            user_profile_id=request.user_profile_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-ID": session_id,
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )


# ============================================================================
# Helper Functions
# ============================================================================


def get_hitl_manager() -> HITLManager:
    """获取全局 HITL 管理器实例
    
    用于在其他模块（如 confirm 路由）中访问同一个 HITL 管理器。
    
    Returns:
        HITLManager: 全局 HITL 管理器实例
    """
    return hitl_manager


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "router",
    "generate_sse_stream",
    "get_hitl_manager",
    "hitl_manager",
]
