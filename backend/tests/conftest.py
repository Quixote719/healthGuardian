"""
Pytest 配置和共享 fixtures
"""

import pytest
from typing import Generator


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """指定异步测试后端"""
    return "asyncio"


@pytest.fixture
def sample_user_profile_data() -> dict:
    """示例用户画像数据"""
    return {
        "age": 45,
        "gender": "男",
        "height": 175.0,
        "weight": 78.0,
        "medical_history": [
            {
                "disease_name": "高血压",
                "diagnosis_date": "2020-01-15",
                "current_status": "慢性管理",
            }
        ],
        "physical_examination": {
            "blood_lipids": {
                "total_cholesterol": 5.8,
                "triglycerides": 2.1,
                "hdl": 1.2,
                "ldl": 3.6,
            },
            "blood_glucose": {
                "fasting_glucose": 6.5,
                "hba1c": 6.2,
            },
        },
        "medications": [
            {
                "drug_name": "氨氯地平",
                "dosage": "5mg",
                "frequency": "每日一次",
                "start_date": "2020-02-01",
            }
        ],
        "lifestyle": {
            "sleep_duration": 6.5,
            "exercise_frequency": "每周1-2次",
            "diet_habit": "荤素均衡",
            "stress_level": 7,
        },
    }


@pytest.fixture
def sample_action_item_data() -> dict:
    """示例干预措施数据"""
    return {
        "category": "营养",
        "title": "控制饱和脂肪摄入",
        "description": "每日饱和脂肪摄入量控制在总热量的7%以下，避免油炸食品和动物内脏。",
        "frequency": "每日三餐",
        "priority": "高",
        "risk_level": "低风险",
        "duration": "12周",
    }
