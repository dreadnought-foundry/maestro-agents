"""Agent execution infrastructure."""

from src.agents.execution.mocks import (
    MockPlanningAgent,
    MockProductEngineerAgent,
    MockQualityEngineerAgent,
    MockTestRunnerAgent,
)
from src.agents.execution.protocol import ExecutionAgent
from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult, StepContext

try:
    from src.agents.execution.claude_code import ClaudeCodeExecutor
    from src.agents.execution.product_engineer import ProductEngineerAgent
    from src.agents.execution.quality_engineer import QualityEngineerAgent
    from src.agents.execution.test_runner import TestRunnerAgent

    _HAS_SDK = True
except ImportError:
    ClaudeCodeExecutor = None  # type: ignore[assignment,misc]
    ProductEngineerAgent = None  # type: ignore[assignment,misc]
    QualityEngineerAgent = None  # type: ignore[assignment,misc]
    TestRunnerAgent = None  # type: ignore[assignment,misc]
    _HAS_SDK = False

__all__ = [
    "AgentResult",
    "AgentRegistry",
    "ClaudeCodeExecutor",
    "ExecutionAgent",
    "MockPlanningAgent",
    "MockProductEngineerAgent",
    "MockQualityEngineerAgent",
    "MockTestRunnerAgent",
    "ProductEngineerAgent",
    "QualityEngineerAgent",
    "StepContext",
    "TestRunnerAgent",
]
