"""Agent execution infrastructure."""

from src.agents.execution.mocks import (
    MockPlanningAgent,
    MockProductEngineerAgent,
    MockQualityEngineerAgent,
    MockSuiteRunnerAgent,
    MockValidationAgent,
)
from src.agents.execution.protocol import ExecutionAgent
from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult, StepContext

try:
    from src.agents.execution.claude_code import ClaudeCodeExecutor
    from src.agents.execution.planning_agent import PlanningAgent
    from src.agents.execution.product_engineer import ProductEngineerAgent
    from src.agents.execution.quality_engineer import QualityEngineerAgent
    from src.agents.execution.suite_runner import SuiteRunnerAgent
    from src.agents.execution.validation_agent import ValidationAgent

    _HAS_SDK = True
except ImportError:
    ClaudeCodeExecutor = None  # type: ignore[assignment,misc]
    PlanningAgent = None  # type: ignore[assignment,misc]
    ProductEngineerAgent = None  # type: ignore[assignment,misc]
    QualityEngineerAgent = None  # type: ignore[assignment,misc]
    SuiteRunnerAgent = None  # type: ignore[assignment,misc]
    ValidationAgent = None  # type: ignore[assignment,misc]
    _HAS_SDK = False

__all__ = [
    "AgentResult",
    "AgentRegistry",
    "ClaudeCodeExecutor",
    "ExecutionAgent",
    "MockPlanningAgent",
    "MockProductEngineerAgent",
    "MockQualityEngineerAgent",
    "MockSuiteRunnerAgent",
    "MockValidationAgent",
    "PlanningAgent",
    "ProductEngineerAgent",
    "QualityEngineerAgent",
    "StepContext",
    "SuiteRunnerAgent",
    "ValidationAgent",
]
