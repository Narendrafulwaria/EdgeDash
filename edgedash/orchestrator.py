"""
Orchestrator — reads state, decides what to run, delegates to agents,
logs every result, and prints a readable cycle summary.

The Orchestrator never fetches data or scores listings directly.
It only reads state and delegates.

Agent registry: swap one import line to replace MockFetcher with the real
Fetcher. Scorer and GapAnalyzer are registered as stubs until implemented.
"""
from __future__ import annotations

import types
from datetime import datetime, timezone
from typing import Callable

from edgedash import storage as _storage
from edgedash.agents.base import Agent, AgentResult
from edgedash.agents.mock_fetcher import MockFetcher
from edgedash.config import Config

# ---------------------------------------------------------------------------
# Stub agents (placeholders — not yet implemented)
# ---------------------------------------------------------------------------

class _NotImplementedAgent:
    def __init__(self, agent_name: str) -> None:
        self.name = agent_name

    def run(self, config: Config, storage: types.ModuleType) -> AgentResult:
        return AgentResult(
            agent=self.name,
            status="ok",
            records_touched=0,
            notes="not implemented yet — skipping",
        )


# ---------------------------------------------------------------------------
# Registry
# One line to swap: replace MockFetcher() with Fetcher() when it's ready.
# ---------------------------------------------------------------------------

def _build_registry() -> list[Agent]:
    return [
        MockFetcher(),                        # swap → Fetcher() in week 2
        _NotImplementedAgent("scorer"),       # swap → Scorer() in week 2
        _NotImplementedAgent("gap_analyzer"), # swap → GapAnalyzer() in week 3
    ]


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _read_state(storage: types.ModuleType) -> dict:
    return {
        "last_fetch": storage.last_fetch_time(),
        "unscored":   storage.count_unscored(),
    }


def _decide(state: dict) -> list[str]:
    """Return the list of agent names that should run this cycle, with reasons."""
    plan: list[tuple[str, str]] = []
    plan.append(("mock_fetcher", "always fetch on every cycle"))
    if state["unscored"] > 0:
        plan.append(("scorer", f"{state['unscored']} unscored listings in db"))
    else:
        plan.append(("scorer", "no unscored listings — will run anyway to check"))
    plan.append(("gap_analyzer", "always analyse gaps after scoring"))
    return plan


# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------

_SEP  = "─" * 60
_SEP2 = "═" * 60


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "never"
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _print_state(state: dict) -> None:
    print(_SEP)
    print("  STATE")
    print(_SEP)
    print(f"  Last fetch       : {_fmt_dt(state['last_fetch'])}")
    print(f"  Unscored listings: {state['unscored']}")
    print()


def _print_plan(plan: list[tuple[str, str]]) -> None:
    print(_SEP)
    print("  PLAN")
    print(_SEP)
    for agent_name, reason in plan:
        print(f"  ▶  {agent_name:<20} — {reason}")
    print()


def _print_result(result: AgentResult, duration_ms: int) -> None:
    icon = "✓" if result.status == "ok" else "✗"
    print(f"  {icon}  {result.agent:<20}  "
          f"touched={result.records_touched:<4}  "
          f"{duration_ms}ms")
    if result.notes:
        print(f"       {result.notes}")


def _print_summary(results: list[AgentResult], cycle_ms: int) -> None:
    print()
    print(_SEP2)
    print("  CYCLE SUMMARY")
    print(_SEP2)
    total_touched = sum(r.records_touched for r in results)
    failed = [r for r in results if r.status == "failed"]
    print(f"  Agents run       : {len(results)}")
    print(f"  Records touched  : {total_touched}")
    print(f"  Failed agents    : {len(failed)}")
    print(f"  Cycle duration   : {cycle_ms}ms")
    if failed:
        print()
        print("  FAILURES:")
        for r in failed:
            print(f"    • {r.agent}: {r.notes}")
    print(_SEP2)
    print()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_cycle(config: Config) -> list[AgentResult]:
    cycle_start = datetime.now(timezone.utc)

    print()
    print(_SEP2)
    print(f"  EDGEDASH CYCLE  —  {_fmt_dt(cycle_start)}")
    print(_SEP2)
    print(f"  Role: {config.target_role}  |  City: {config.target_city}")
    print()

    _storage.init_db(config.db_path)

    state = _read_state(_storage)
    _print_state(state)

    plan = _decide(state)
    _print_plan(plan)

    registry: dict[str, Agent] = {a.name: a for a in _build_registry()}
    plan_names = [name for name, _ in plan]

    print(_SEP)
    print("  RUNNING AGENTS")
    print(_SEP)

    results: list[AgentResult] = []
    for agent_name in plan_names:
        agent = registry.get(agent_name)
        if agent is None:
            print(f"  ⚠  {agent_name} not found in registry — skipping")
            continue

        agent_start = datetime.now(timezone.utc)
        result = agent.run(config, _storage)
        agent_end = datetime.now(timezone.utc)
        duration_ms = int((agent_end - agent_start).total_seconds() * 1000)

        _print_result(result, duration_ms)
        results.append(result)

        _storage.log_cycle(
            agent=result.agent,
            started_at=agent_start,
            finished_at=agent_end,
            records_touched=result.records_touched,
            status=result.status,
            notes=result.notes or None,
        )

    cycle_end = datetime.now(timezone.utc)
    cycle_ms = int((cycle_end - cycle_start).total_seconds() * 1000)
    _print_summary(results, cycle_ms)

    return results
