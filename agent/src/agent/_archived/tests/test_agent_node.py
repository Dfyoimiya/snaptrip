# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        🔴 ARCHIVED — TRIP PLANNING AGENT                      ║
# ║  Archived: 2026-06-07                                                        ║
# ║  Reason: Agent repurposed from local trip planning to new domain             ║
# ║  This file is preserved for reference but NOT imported by the framework.     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

"""Tests for agent_node.py -- LLM ReAct inference node and routing logic.

Covers:
  - route_after_agent: routing to tools / hitl / end based on tool_calls
  - _build_all_tool_defs: merging harness, user-facing, and internal tools
  - _build_messages: constructing the message list from PlanState
  - agent_node: the full async coroutine (with mocked runtime)

These are unit tests: the full `agent_node()` coroutine requires a running
runtime with LLM adapter, so we test the pure helper functions and the
routing logic in isolation, plus the full coroutine with mocks.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agent.agent_node import (
    INTERNAL_TOOL_DEFS,
    USER_FACING_TOOL_DEFS,
    _build_all_tool_defs,
    _build_messages,
    agent_node,
    route_after_agent,
)
from agent.prompts.system import AGENT_SYSTEM_PROMPT
from agent.schemas.state import PlanState

# ===========================================================================
# route_after_agent tests
# ===========================================================================


class TestRouteAfterAgent:
    """Tests for the route_after_agent routing function."""

    def test_route_to_tools(self):
        """Last message has tool_calls for amap_poi_search -> route returns 'tools'."""
        last_msg = AIMessage(
            content="搜索中...",
            tool_calls=[
                {
                    "name": "amap_poi_search",
                    "args": {"keywords": "公园", "city": "北京"},
                    "id": "call_abc123",
                    "type": "tool_call",
                }
            ],
        )
        state: PlanState = {"messages": [last_msg]}
        assert route_after_agent(state) == "tools"

    def test_route_to_hitl(self):
        """Last message has ask_user tool call -> route returns 'hitl'."""
        last_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "ask_user",
                    "args": {"message": "你预算多少?"},
                    "id": "call_hitl_001",
                    "type": "tool_call",
                }
            ],
        )
        state: PlanState = {"messages": [last_msg]}
        assert route_after_agent(state) == "hitl"

    def test_route_to_end(self):
        """Last message is plain text (no tool_calls) -> route returns 'end'."""
        last_msg = AIMessage(content="方案已经规划好了。总费用 ¥300。")
        state: PlanState = {"messages": [last_msg]}
        assert route_after_agent(state) == "end"

    def test_route_mixed_tools(self):
        """Multiple tool calls including ask_user -> routes to 'hitl'."""
        last_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "amap_poi_search",
                    "args": {"keywords": "博物馆"},
                    "id": "call_002",
                    "type": "tool_call",
                },
                {
                    "name": "ask_user",
                    "args": {"message": "你喜欢博物馆吗?"},
                    "id": "call_003",
                    "type": "tool_call",
                },
            ],
        )
        state: PlanState = {"messages": [last_msg]}
        assert route_after_agent(state) == "hitl"

    def test_route_mixed_with_present_plan(self):
        """present_plan in tool_calls -> routes to 'hitl'."""
        last_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "present_plan",
                    "args": {"message": "这是方案", "plan": {}},
                    "id": "call_004",
                    "type": "tool_call",
                },
            ],
        )
        state: PlanState = {"messages": [last_msg]}
        assert route_after_agent(state) == "hitl"

    def test_route_empty_messages(self):
        """No messages -> route returns 'end'."""
        state: PlanState = {"messages": []}
        assert route_after_agent(state) == "end"

    def test_route_missing_messages_key(self):
        """state without messages key -> route returns 'end'."""
        state: PlanState = {}
        assert route_after_agent(state) == "end"

    def test_route_tool_calls_empty_list(self):
        """tool_calls=[] on last message -> route returns 'end'."""
        last_msg = AIMessage(content="完成", tool_calls=[])
        state: PlanState = {"messages": [last_msg]}
        assert route_after_agent(state) == "end"

    def test_route_update_intent_tool(self):
        """update_intent (internal tool) -> routes to 'tools', not 'hitl'."""
        last_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "update_intent",
                    "args": {"city": "北京"},
                    "id": "call_int_001",
                    "type": "tool_call",
                }
            ],
        )
        state: PlanState = {"messages": [last_msg]}
        assert route_after_agent(state) == "tools"

    def test_route_with_object_style_tool_calls(self):
        """route_after_agent handles object-style tool_calls with .name attribute."""
        # Use MagicMock for last_msg to avoid AIMessage validation on non-standard objects
        last_msg = MagicMock()
        last_msg.content = ""

        class ObjectStyleCall:
            name = "ask_user"
            id = "call_obj_001"
            type = "tool_call"
            args = {"message": "hello"}

        last_msg.tool_calls = [ObjectStyleCall()]
        state: PlanState = {"messages": [last_msg]}
        assert route_after_agent(state) == "hitl"

    def test_route_with_object_style_non_hitl(self):
        """Object-style tool call with non-user-facing name routes to 'tools'."""
        last_msg = MagicMock()
        last_msg.content = ""

        class ObjectStyleCall:
            name = "amap_poi_search"
            id = "call_obj_002"
            type = "tool_call"
            args = {"keywords": "test"}

        last_msg.tool_calls = [ObjectStyleCall()]
        state: PlanState = {"messages": [last_msg]}
        assert route_after_agent(state) == "tools"


# ===========================================================================
# _build_all_tool_defs tests
# ===========================================================================


class TestBuildAllToolDefs:
    """Tests for _build_all_tool_defs."""

    def test_build_all_tool_defs(self):
        """Tool definitions include harness + user-facing + internal tools."""
        harness_tools = [
            {
                "type": "function",
                "function": {
                    "name": "amap_poi_search",
                    "description": "POI search",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "pymoo_solve_itinerary",
                    "description": "NSGA-II solver",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

        all_tools = _build_all_tool_defs(harness_tools)

        # Structure: harness + user-facing + internal
        assert len(all_tools) == len(harness_tools) + len(USER_FACING_TOOL_DEFS) + len(INTERNAL_TOOL_DEFS)
        assert all_tools[0]["function"]["name"] == "amap_poi_search"
        assert all_tools[1]["function"]["name"] == "pymoo_solve_itinerary"

        # User-facing section
        user_names = {t["function"]["name"] for t in USER_FACING_TOOL_DEFS}
        for t in all_tools:
            if t["function"]["name"] in user_names:
                break
        else:
            pytest.fail("No user-facing tool found in merged list")

        # Internal section
        internal_names = {t["function"]["name"] for t in INTERNAL_TOOL_DEFS}
        for t in all_tools:
            if t["function"]["name"] in internal_names:
                break
        else:
            pytest.fail("No internal tool found in merged list")

    def test_harness_only_when_empty(self):
        """Empty harness tools list still includes user-facing and internal tools."""
        all_tools = _build_all_tool_defs([])
        assert len(all_tools) == len(USER_FACING_TOOL_DEFS) + len(INTERNAL_TOOL_DEFS)

    def test_user_facing_tool_defs_structure(self):
        """Each user-facing tool def has type=function and required fields."""
        for td in USER_FACING_TOOL_DEFS:
            assert td["type"] == "function"
            func = td["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["name"] in {"ask_user", "present_plan", "present_booking"}

    def test_internal_tool_defs_structure(self):
        """Each internal tool def has type=function and required fields."""
        for td in INTERNAL_TOOL_DEFS:
            assert td["type"] == "function"
            func = td["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["name"] in {"update_extract_result", "update_itinerary"}


# ===========================================================================
# _build_messages tests
# ===========================================================================


class TestBuildMessages:
    """Tests for _build_messages."""

    def test_build_messages_includes_system_prompt(self):
        """Message list always starts with the system prompt."""
        state: PlanState = {}
        msgs = _build_messages(state)
        assert len(msgs) >= 1
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == AGENT_SYSTEM_PROMPT

    def test_build_messages_with_intent(self):
        """Non-empty extract_result is included as a system message."""
        from agent.schemas.extract import ExtractResult, UserIntent
        er = ExtractResult()
        er.intent.city = "北京"
        er.intent.guest_count = 2
        er.hard_constraints.budget_max_cny = 500.0
        state: PlanState = {
            "extract_result": er,
        }
        msgs = _build_messages(state)
        system_msgs = [m for m in msgs if m["role"] == "system"]
        # First one is the AGENT_SYSTEM_PROMPT; second should be the extract_result
        assert len(system_msgs) >= 2
        assert "北京" in system_msgs[1]["content"]
        assert "2" in system_msgs[1]["content"]

    def test_build_messages_empty_intent(self):
        """None extract_result is excluded."""
        state: PlanState = {"extract_result": None}
        msgs = _build_messages(state)
        system_msgs = [m for m in msgs if m["role"] == "system"]
        assert len(system_msgs) == 1  # only the AGENT_SYSTEM_PROMPT

    def test_build_messages_with_profile(self):
        """Non-empty user_profile is included as a system message."""
        state: PlanState = {
            "user_profile": {"dietary_tendency": "vegetarian", "budget_tendency": "mid"},
        }
        msgs = _build_messages(state)
        system_msgs = [m for m in msgs if m["role"] == "system"]
        assert len(system_msgs) >= 2
        assert "vegetarian" in system_msgs[1]["content"]

    def test_build_messages_with_candidates(self):
        """activity_candidates and restaurant_candidates are included."""
        state: PlanState = {
            "activity_candidates": [
                {"id": "act-1", "name": "公园", "rating": 4.5},
                {"id": "act-2", "name": "博物馆", "rating": 4.7},
            ],
            "restaurant_candidates": [
                {"id": "rst-1", "name": "亲子餐厅", "rating": 4.6},
            ],
        }
        msgs = _build_messages(state)
        system_msgs = [m for m in msgs if m["role"] == "system"]
        candidate_msgs = [m for m in system_msgs if "活动候选" in m["content"] or "餐厅候选" in m["content"]]
        assert len(candidate_msgs) >= 2

    def test_build_messages_with_pareto(self):
        """pareto_solutions are included as a system message."""
        state: PlanState = {
            "pareto_solutions": [
                {"rank": 1, "activity": {"name": "公园"}, "restaurant": {"name": "亲子餐厅"}},
            ],
        }
        msgs = _build_messages(state)
        system_msgs = [m for m in msgs if m["role"] == "system"]
        pareto_msgs = [m for m in system_msgs if "Pareto 前沿解集" in m["content"]]
        assert len(pareto_msgs) == 1

    def test_build_messages_conversation_history(self):
        """HumanMessage and AIMessage are appended in order."""
        history = [
            HumanMessage(content="我想去北京玩"),
            AIMessage(content="好的，我来查一下北京的热门景点。"),
            HumanMessage(content="我喜欢博物馆"),
        ]
        state: PlanState = {"messages": history}
        msgs = _build_messages(state)

        # Find the conversation messages (role: user / assistant)
        conversation = [m for m in msgs if m["role"] in ("user", "assistant")]
        assert len(conversation) == 3
        assert conversation[0]["role"] == "user"
        assert conversation[0]["content"] == "我想去北京玩"
        assert conversation[1]["role"] == "assistant"
        assert conversation[1]["content"] == "好的，我来查一下北京的热门景点。"
        assert conversation[2]["role"] == "user"
        assert conversation[2]["content"] == "我喜欢博物馆"

    def test_build_messages_with_system_message_history(self):
        """SystemMessage in conversation history is included as system role."""
        history = [
            SystemMessage(content="System note: user prefers indoor activities"),
            HumanMessage(content="推荐一些博物馆"),
        ]
        state: PlanState = {"messages": history}
        msgs = _build_messages(state)

        system_msgs = [m for m in msgs if m["role"] == "system"]
        # First one is AGENT_SYSTEM_PROMPT, second is the SystemMessage from history
        assert len(system_msgs) >= 2
        assert "System note" in system_msgs[1]["content"]

    def test_build_messages_with_tool_calls_in_ai_message(self):
        """AIMessage with tool_calls includes them in the assistant message."""
        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "amap_poi_search",
                    "args": {"keywords": "公园"},
                    "id": "call_001",
                    "type": "tool_call",
                }
            ],
        )
        state: PlanState = {"messages": [ai_msg]}
        msgs = _build_messages(state)

        assistant_msgs = [m for m in msgs if m["role"] == "assistant"]
        assert len(assistant_msgs) == 1
        assert "tool_calls" in assistant_msgs[0]
        assert len(assistant_msgs[0]["tool_calls"]) == 1

    def test_build_messages_with_tool_message(self):
        """ToolMessage is included with tool_call_id and content."""
        tool_msg = ToolMessage(content='{"result": "ok"}', tool_call_id="call_001")
        state: PlanState = {"messages": [tool_msg]}
        msgs = _build_messages(state)

        tool_msgs = [m for m in msgs if m["role"] == "tool"]
        assert len(tool_msgs) == 1
        assert tool_msgs[0]["tool_call_id"] == "call_001"
        assert tool_msgs[0]["content"] == '{"result": "ok"}'

    def test_build_messages_empty_history(self):
        """No messages in state produces just the system messages."""
        state: PlanState = {}
        msgs = _build_messages(state)
        assert len(msgs) == 1
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == AGENT_SYSTEM_PROMPT

    def test_build_messages_ai_message_none_content_with_tool_calls(self):
        """AIMessage with None content and tool_calls is handled (content=None, tool_calls present)."""
        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "z3_verify_feasibility",
                    "args": {"activities": []},
                    "id": "call_002",
                    "type": "tool_call",
                }
            ],
        )
        state: PlanState = {"messages": [ai_msg]}
        msgs = _build_messages(state)
        assistant_msgs = [m for m in msgs if m["role"] == "assistant"]
        assert len(assistant_msgs) == 1
        # content is None because m.content is empty string (falsy)
        assert assistant_msgs[0]["content"] is None
        assert len(assistant_msgs[0]["tool_calls"]) == 1


# ===========================================================================
# agent_node integration tests (with mock runtime)
# ===========================================================================


class TestAgentNode:
    """Tests for the full agent_node coroutine with mocked runtime."""

    @pytest.mark.asyncio
    async def test_agent_node_returns_ai_message(self):
        """agent_node with mock runtime returns a dict with an AIMessage."""
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = {
            "content": "我来搜索一下公园的信息",
            "tool_calls": None,
        }
        mock_runtime = MagicMock()
        mock_runtime.llm_adapter = mock_llm
        mock_runtime.harness = MagicMock()
        mock_runtime.harness.list_tools.return_value = [
            {
                "type": "function",
                "function": {
                    "name": "amap_poi_search",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

        state: PlanState = {
            "messages": [HumanMessage(content="推荐一个公园")],
        }

        with patch("agent.graph._runtime", mock_runtime):
            result = await agent_node(state)

        assert "messages" in result
        assert len(result["messages"]) == 1
        ai_msg = result["messages"][0]
        assert isinstance(ai_msg, AIMessage)
        assert ai_msg.content == "我来搜索一下公园的信息"

        # Verify the LLM was called with proper arguments
        mock_llm.chat.assert_awaited_once()
        call_kwargs = mock_llm.chat.call_args.kwargs
        assert "messages" in call_kwargs
        assert "tools" in call_kwargs
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["max_tokens"] == 2048

    @pytest.mark.asyncio
    async def test_agent_node_with_tool_calls(self):
        """agent_node response with tool_calls is captured in AIMessage."""
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = {
            "content": "搜索中...",   # Non-empty so agent_node adds it to AIMessage kwargs
            "tool_calls": [
                {
                    "name": "amap_poi_search",
                    "args": {"keywords": "公园", "city": "北京"},
                    "id": "call_tc_001",
                    "type": "tool_call",
                }
            ],
        }
        mock_runtime = MagicMock()
        mock_runtime.llm_adapter = mock_llm
        mock_runtime.harness = MagicMock()
        mock_runtime.harness.list_tools.return_value = []

        state: PlanState = {
            "messages": [HumanMessage(content="找公园")],
        }

        with patch("agent.graph._runtime", mock_runtime):
            result = await agent_node(state)

        ai_msg = result["messages"][0]
        assert ai_msg.content == "搜索中..."
        assert len(ai_msg.tool_calls) == 1
        assert ai_msg.tool_calls[0]["name"] == "amap_poi_search"
        assert ai_msg.tool_calls[0]["args"] == {"keywords": "公园", "city": "北京"}

    @pytest.mark.asyncio
    async def test_agent_node_without_runtime(self):
        """agent_node without _runtime instantiates default LiteLLMAdapter."""
        state: PlanState = {
            "messages": [HumanMessage(content="hi")],
        }

        # _runtime is None by default; mock the LiteLLMAdapter class at the module level
        # since `from agent.adapters.litellm_adapter import LiteLLMAdapter` is called
        # inside agent_node as a fallback
        with patch("agent.graph._runtime", None):
            with patch("agent.adapters.litellm_adapter.LiteLLMAdapter") as mock_adapter_cls:
                mock_adapter = AsyncMock()
                mock_adapter.chat.return_value = {"content": "你好！"}
                mock_adapter_cls.return_value = mock_adapter

                result = await agent_node(state)

        assert result["messages"][0].content == "你好！"

    @pytest.mark.asyncio
    async def test_agent_node_without_harness(self):
        """agent_node with runtime but no harness generates empty tool list."""
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = {"content": "done"}
        mock_runtime = MagicMock()
        mock_runtime.llm_adapter = mock_llm
        mock_runtime.harness = None  # No harness

        state: PlanState = {
            "messages": [HumanMessage(content="test")],
        }

        with patch("agent.graph._runtime", mock_runtime):
            result = await agent_node(state)

        call_kwargs = mock_llm.chat.call_args.kwargs
        # Tools should still be built (user-facing + internal, no harness)
        assert len(call_kwargs["tools"]) == len(USER_FACING_TOOL_DEFS) + len(INTERNAL_TOOL_DEFS)
        assert result["messages"][0].content == "done"
