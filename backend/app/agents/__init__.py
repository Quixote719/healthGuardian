"""
智能体模块
包含 Controller, Nutrition, Rehabilitation, Neuropsychology, Synthesis 五个智能体
以及风险检测和健康分析辅助函数
"""

from app.agents.base import BaseAgent
from app.agents.controller import ControllerAgent
from app.agents.neuropsychology import NeuropsychologyAgent
from app.agents.nutrition import NutritionAgent
from app.agents.rehabilitation import RehabilitationAgent
from app.agents.synthesis import SynthesisAgent
from app.agents.risk_detector import (
    detect_high_risk_keywords,
    detect_prohibited_keywords,
    detect_out_of_scope,
    get_professional_help_suggestion,
    perform_safety_check,
    HIGH_RISK_KEYWORDS,
    PROHIBITED_KEYWORDS,
    OUT_OF_SCOPE_KEYWORDS,
)

__all__ = [
    # Base class
    "BaseAgent",
    # Agents
    "ControllerAgent",
    "NutritionAgent",
    "RehabilitationAgent",
    "NeuropsychologyAgent",
    "SynthesisAgent",
    # Risk detection functions
    "detect_high_risk_keywords",
    "detect_prohibited_keywords",
    "detect_out_of_scope",
    "get_professional_help_suggestion",
    "perform_safety_check",
    # Constants
    "HIGH_RISK_KEYWORDS",
    "PROHIBITED_KEYWORDS",
    "OUT_OF_SCOPE_KEYWORDS",
]
