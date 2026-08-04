"""
Agent contract for all EdgeDash sub-agents.

Every agent must satisfy the Agent protocol: expose a `name` attribute and
implement `run(config, storage_module) -> AgentResult`.
Using Protocol (structural subtyping) keeps agents decoupled from a shared
base class while still being statically checkable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

import types

from edgedash.config import Config

Status = Literal["ok", "failed"]


@dataclass
class AgentResult:
    agent: str
    status: Status
    records_touched: int
    notes: str


@runtime_checkable
class Agent(Protocol):
    name: str

    def run(self, config: Config, storage: types.ModuleType) -> AgentResult:
        ...
