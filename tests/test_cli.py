"""Tests for CLI module imports and exports."""

import sys
from unittest import mock

import pytest


class TestCLIModuleImports:
    def test_cli_module_imports(self):
        """CLI module imports without error."""
        from src.execution import cli  # noqa: F401

    def test_cli_main_module_imports(self):
        """CLI __main__ module imports without error.

        The __main__ module calls main() at import time, which invokes
        argparse and sys.exit(1) when no subcommand is given.  We mock
        sys.argv to avoid argparse errors and catch the expected SystemExit.
        """
        # Remove cached module so the import re-executes the module body
        sys.modules.pop("src.execution.__main__", None)

        with mock.patch("sys.argv", ["__main__.py"]):
            with pytest.raises(SystemExit):
                import importlib
                import src.execution.__main__  # noqa: F401
                importlib.reload(src.execution.__main__)

    def test_agents_package_imports(self):
        """src.agents package imports without error."""
        import src.agents  # noqa: F401

    def test_execution_init_exports(self):
        """All execution __init__.py exports are importable."""
        import src.execution

        expected = [
            "RunConfig",
            "create_registry",
            "create_test_registry",
            "create_default_registry",
            "create_hook_registry",
            "run_sprint",
            "Hook",
            "HookContext",
            "HookPoint",
            "HookRegistry",
            "HookResult",
            "MockHook",
            "cancel_sprint",
            "find_resume_point",
            "resume_sprint",
            "retry_step",
            "RunResult",
            "SprintRunner",
        ]
        for name in expected:
            assert hasattr(src.execution, name), f"src.execution missing export: {name}"

    def test_agents_execution_init_exports(self):
        """All agents/execution __init__.py exports are importable."""
        import src.agents.execution

        expected = [
            "AgentResult",
            "AgentRegistry",
            "ExecutionAgent",
            "MockProductEngineerAgent",
            "MockQualityEngineerAgent",
            "MockSuiteRunnerAgent",
            "ProductEngineerAgent",
            "QualityEngineerAgent",
            "StepContext",
            "SuiteRunnerAgent",
        ]
        for name in expected:
            assert hasattr(src.agents.execution, name), (
                f"src.agents.execution missing export: {name}"
            )
