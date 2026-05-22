#!/usr/bin/env python3
"""Migrate all imports from old app.* paths to new marketplace/agent_worker/shared."""

import re
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Mapping table: (pattern, replacement) ──
# Order matters: more specific patterns first
REPLACEMENTS = [
    # ── shared layer ──
    (r'from app\.core\.config import', 'from shared.core.config import'),
    (r'from app\.core\.constants import', 'from shared.core.constants import'),
    (r'from app\.core\.exceptions import', 'from shared.core.exceptions import'),
    (r'from app\.core\.exception_handlers import', 'from shared.core.exception_handlers import'),
    (r'from app\.core\.logging import', 'from shared.core.logging import'),
    (r'from app\.core\.rate_limit import', 'from shared.core.rate_limit import'),
    (r'from app\.core\.response import', 'from shared.core.response import'),
    (r'from app\.core\.security import', 'from shared.core.security import'),
    (r'from app\.db\.session import', 'from shared.db.session import'),
    (r'from app\.db\.redis import', 'from shared.db.redis import'),
    (r'from app\.schemas\.plan import', 'from shared.schemas.plan import'),

    # ── marketplace main ──
    (r'from app\.main import', 'from marketplace.app.main import'),
    (r'from app\.celery_app import', 'from marketplace.app.celery_app import'),

    # ── marketplace api ──
    (r'from app\.api\.v1\.plan import', 'from marketplace.app.api.v1.plan import'),
    (r'from app\.api\.v1\.auth import', 'from marketplace.app.api.v1.auth import'),
    (r'from app\.api\.v1\.user import', 'from marketplace.app.api.v1.user import'),
    (r'from app\.api\.v1\.session import', 'from marketplace.app.api.v1.session import'),

    # ── marketplace models ──
    (r'from app\.models\.base import', 'from marketplace.app.models.base import'),
    (r'from app\.models\.users import', 'from marketplace.app.models.users import'),
    (r'from app\.models\.user_profile import', 'from marketplace.app.models.user_profile import'),
    (r'from app\.models\.plan import', 'from marketplace.app.models.plan import'),
    (r'from app\.models\.plan_slot import', 'from marketplace.app.models.plan_slot import'),
    (r'from app\.models\.plan_adjustment import', 'from marketplace.app.models.plan_adjustment import'),
    (r'from app\.models\.poi import', 'from marketplace.app.models.poi import'),
    (r'from app\.models\.refresh_token import', 'from marketplace.app.models.refresh_token import'),

    # ── marketplace schemas ──
    (r'from app\.schemas\.auth import', 'from marketplace.app.schemas.auth import'),
    (r'from app\.schemas\.user import', 'from marketplace.app.schemas.user import'),

    # ── marketplace services ──
    (r'from app\.services\.user_service import', 'from marketplace.app.services.user_service import'),

    # ── marketplace amap adapters ──
    (r'from app\.adapters\.amap_client import', 'from marketplace.app.adapters.amap.client import'),
    (r'from app\.adapters\.base import', 'from marketplace.app.adapters.amap.base import'),
    (r'from app\.adapters\.registry import', 'from marketplace.app.adapters.amap.registry import'),
    (r'from app\.adapters\.adapters\.poi_adapter import', 'from marketplace.app.adapters.amap.poi_adapter import'),
    (r'from app\.adapters\.adapters\.route_adapter import', 'from marketplace.app.adapters.amap.route_adapter import'),
    (r'from app\.adapters\.adapters\.geocode_adapter import', 'from marketplace.app.adapters.amap.geocode_adapter import'),
    (r'from app\.adapters\.adapters\.district_adapter import', 'from marketplace.app.adapters.amap.district_adapter import'),
    (r'from app\.adapters\.mappers\.poi_mapper import', 'from marketplace.app.adapters.amap.poi_mapper import'),
    (r'from app\.adapters\.mappers\.route_mapper import', 'from marketplace.app.adapters.amap.route_mapper import'),
    (r'from app\.adapters\.mappers\.geo_mapper import', 'from marketplace.app.adapters.amap.geo_mapper import'),
    (r'from app\.adapters\.schemas\.poi import', 'from marketplace.app.adapters.amap.schemas.poi import'),
    (r'from app\.adapters\.schemas\.route import', 'from marketplace.app.adapters.amap.schemas.route import'),
    (r'from app\.adapters\.schemas\.geocode import', 'from marketplace.app.adapters.amap.schemas.geocode import'),
    (r'from app\.adapters\.schemas\.district import', 'from marketplace.app.adapters.amap.schemas.district import'),
    (r'from app\.adapters\.schemas\.weather import', 'from marketplace.app.adapters.amap.schemas.weather import'),
    (r'from app\.adapters\.schemas\.types import', 'from marketplace.app.adapters.amap.schemas.types import'),

    # ── marketplace data ──
    (r'from app\.data\.seed_pois import', 'from marketplace.app.data.seed_pois import'),

    # ── agent_worker core ──
    (r'from app\.agent\.runtime import', 'from agent_worker.app.agent.runtime import'),
    (r'from app\.agents\.graph import', 'from agent_worker.app.agent.graph import'),
    (r'from app\.agents\.protocol import', 'from agent_worker.app.agent.protocol import'),

    # ── agent engines ──
    (r'from app\.agents\.intent_parser import', 'from agent_worker.app.agent.engines.intent_parser import'),
    (r'from app\.agents\.context_loader import', 'from agent_worker.app.agent.engines.context_loader import'),
    (r'from app\.agents\.memory_manager import', 'from agent_worker.app.agent.engines.memory_manager import'),
    (r'from app\.agents\.retrieval_engine import', 'from agent_worker.app.agent.engines.retrieval_engine import'),
    (r'from app\.agents\.planning_engine import', 'from agent_worker.app.agent.engines.planning_engine import'),
    (r'from app\.agents\.consensus_resolver import', 'from agent_worker.app.agent.engines.consensus_resolver import'),
    (r'from app\.agents\.execution_engine import', 'from agent_worker.app.agent.engines.execution_engine import'),
    (r'from app\.agents\.fallback_engine import', 'from agent_worker.app.agent.engines.fallback_engine import'),
    (r'from app\.agents\.notify_engine import', 'from agent_worker.app.agent.engines.notify_engine import'),

    # ── agent state ──
    (r'from app\.agent_runtime\.state import', 'from agent_worker.app.agent.state.builder import'),
    (r'from app\.agent_runtime\.events import', 'from agent_worker.app.agent.state.events import'),
    (r'from app\.agent_runtime\.preconfirm_state import', 'from agent_worker.app.agent.state.preconfirm import'),
    (r'from app\.agent_runtime\.postconfirm_state import', 'from agent_worker.app.agent.state.postconfirm import'),
    (r'from app\.agent_runtime\.response_state import', 'from agent_worker.app.agent.state.response import'),

    # ── agent events ──
    (r'from app\.agent_runtime\.event_store import', 'from agent_worker.app.agent.events.store import'),
    (r'from app\.adapters\.events\.redis_event_bus import', 'from agent_worker.app.agent.events.redis_bus import'),

    # ── agent checkpointer ──
    (r'from app\.agent_runtime\.checkpointer import', 'from agent_worker.app.agent.checkpointer.builder import'),

    # ── agent providers ──
    (r'from app\.providers\.base import', 'from agent_worker.app.agent.providers.base import'),
    (r'from app\.providers\.deepseek import', 'from agent_worker.app.agent.providers.deepseek import'),
    (r'from app\.providers\.kimi import', 'from agent_worker.app.agent.providers.kimi import'),
    (r'from app\.providers\.openrouter import', 'from agent_worker.app.agent.providers.openrouter import'),
    (r'from app\.providers\.registry import', 'from agent_worker.app.agent.providers.registry import'),

    # ── agent memory ──
    (r'from app\.services\.memory_service import', 'from agent_worker.app.agent.memory.service import'),

    # ── agent services ──
    (r'from app\.services\.agent_service import', 'from agent_worker.app.agent.services.agent import'),
    (r'from app\.services\.llm_gateway import', 'from agent_worker.app.agent.services.llm_gateway import'),

    # ── agent adapters ──
    (r'from app\.adapters\.llm\.llm_adapter import', 'from agent_worker.app.agent.adapters.llm import'),
    (r'from app\.adapters\.tools\.marketplace_client import', 'from agent_worker.app.agent.adapters.marketplace import'),
    (r'from app\.adapters\.tools\.mock_gateway import', 'from agent_worker.app.agent.adapters.mock_tool_gateway import'),
    (r'from app\.services\.mock_gateway import', 'from agent_worker.app.agent.adapters.mock_gateway import'),
    (r'from app\.adapters\.prompt\.jinja import', 'from agent_worker.app.agent.adapters.prompt import'),

    # ── agent persistence ──
    (r'from app\.adapters\.persistence\.plan_run_repository import', 'from agent_worker.app.agent.adapters.persistence.plan_run import'),
    (r'from app\.adapters\.persistence\.runtime_event_repository import', 'from agent_worker.app.agent.adapters.persistence.runtime_event import'),
    (r'from app\.adapters\.persistence\.checkpoint_repository import', 'from agent_worker.app.agent.adapters.persistence.checkpoint import'),
    (r'from app\.adapters\.persistence\.plan_repository import', 'from agent_worker.app.agent.adapters.persistence.plan import'),
    (r'from app\.adapters\.persistence\.user_profile_repository import', 'from agent_worker.app.agent.adapters.persistence.user_profile import'),

    # ── agent models ──
    (r'from app\.models\.plan_run import', 'from agent_worker.app.agent.models.plan_run import'),
    (r'from app\.models\.plan_run_event import', 'from agent_worker.app.agent.models.plan_run_event import'),
    (r'from app\.models\.checkpoint import', 'from agent_worker.app.agent.models.checkpoint import'),
    (r'from app\.models\.runtime_checkpoint import', 'from agent_worker.app.agent.models.runtime_checkpoint import'),
    (r'from app\.models\.llm_usage_log import', 'from agent_worker.app.agent.models.llm_usage_log import'),

    # ── agent schemas ──
    (r'from app\.schemas\.agent\.events import', 'from agent_worker.app.agent.schemas.events import'),
    (r'from app\.schemas\.agent\.runtime import', 'from agent_worker.app.agent.schemas.runtime import'),
    (r'from app\.schemas\.agent\.state import', 'from agent_worker.app.agent.schemas.state import'),
    (r'from app\.schemas\.tool import', 'from agent_worker.app.agent.schemas.tool import'),
    (r'from app\.schemas\.tool_provider import', 'from agent_worker.app.agent.schemas.tool_provider import'),
    (r'from app\.schemas\.checkpoint import', 'from agent_worker.app.agent.schemas.checkpoint import'),
    (r'from app\.schemas\.llm import', 'from agent_worker.app.agent.schemas.llm import'),

    # ── agent ports ──
    (r'from app\.ports\.events import', 'from agent_worker.app.agent.ports.events import'),
    (r'from app\.ports\.llm import', 'from agent_worker.app.agent.ports.llm import'),
    (r'from app\.ports\.prompt import', 'from agent_worker.app.agent.ports.prompt import'),
    (r'from app\.ports\.repositories import', 'from agent_worker.app.agent.ports.repositories import'),
    (r'from app\.ports\.tools import', 'from agent_worker.app.agent.ports.tools import'),

    # ── agent tasks ──
    (r'from app\.tasks\.plan_tasks import', 'from agent_worker.app.tasks.plan_tasks import'),

    # ── agent_runtime lazy imports from __init__ ──
    (r'from app\.agent_runtime import (GRAPH_VERSION|RuntimeEventStore|build_plan_graph|build_initial_runtime_state|build_request_envelope)',
     lambda m: _handle_agent_runtime_import(m)),

    # ── broad agent_runtime (catch remaining) ──
    (r'from app\.agent_runtime import', 'from agent_worker.app.agent.state.builder import'),

    # ── app.agents.skills ──
    (r'from app\.agents\.skills', 'from agent_worker.app.agent.skills'),
    (r'from app\.agents\.prompts', 'from agent_worker.app.agent.prompts'),
]

def _handle_agent_runtime_import(m):
    """Handle the lazy imports from agent_runtime/__init__.py."""
    names_str = m.group(1)
    names = [n.strip() for n in names_str.split(',')]
    lines = []
    for name in names:
        if name == 'GRAPH_VERSION':
            # GRAPH_VERSION is defined in graph.py
            pass  # handled by specific patterns
        elif name == 'RuntimeEventStore':
            lines.append(f'from agent_worker.app.agent.events.store import RuntimeEventStore')
        elif name == 'build_plan_graph':
            lines.append(f'from agent_worker.app.agent.graph import build_plan_graph')
        elif name == 'build_initial_runtime_state':
            lines.append(f'from agent_worker.app.agent.state.builder import build_initial_runtime_state')
        elif name == 'build_request_envelope':
            lines.append(f'from agent_worker.app.agent.state.builder import build_request_envelope')
    return '\n'.join(lines) if lines else m.group(0)

def migrate_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    original = content
    for pattern, replacement in REPLACEMENTS:
        if callable(replacement):
            content = re.sub(pattern, replacement, content)
        else:
            content = re.sub(pattern, replacement, content)

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    changed = 0
    total = 0
    for root, dirs, files in os.walk(BACKEND):
        # Skip __pycache__, .venv, .git
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.venv', '.git', 'node_modules')]
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                total += 1
                if migrate_file(path):
                    changed += 1
                    print(f'  UPDATED: {os.path.relpath(path, BACKEND)}')

    print(f'\nDone: {changed}/{total} files updated')

if __name__ == '__main__':
    main()
