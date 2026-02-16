"""Execution configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RunConfig:
    """Configuration for sprint execution."""

    max_retries: int = 2
    retry_delay_seconds: float = 1.0
