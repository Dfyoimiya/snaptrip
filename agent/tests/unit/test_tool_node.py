"""Tests for tool_node.py -- tool execution and user-facing tool detection.

Covers:
  - _parse_tool_call: normalising dict-style and object-style tool calls
  - _apply_state_update: applying internal tool args to PlanState
  - tool_node routing: user-facing -> hitl, internal -> state update,
    execution -> saga path, standard -> harness
  - Edge cases: harness exceptions, saga exceptions, mixed calls

Important note on tool call format
----------------------------------
``_parse_tool_call`` expects dict-style tool calls with the key ``"arguments"``
(the format returned by the LLM adapter).  LangChain's ``AIMessage.tool_calls``
uses ``"args"`` instead.  To avoid the format mismatch, tests that exercise
``tool_node()`` use a plain ``MagicMock`` as the last message so that
``tool_calls`` is returned in the ``"arguments"`` format exactly as it arrives
from the LLM adapter in production.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.schemas.state import PlanState
from agent.tool_node import (
    USER_FACING_NAMES,
    _apply_state_update,
    _parse_tool_call,
    tool_node,
)
from agent.utils import EXECUTION_NAMES


def _make_last_msg(tool_calls: list[dict]) -> MagicMock:
    """Create a mock last message with tool_calls in the LLM-adapter format.

    The adapter format uses ``id``, ``name``, ``arguments`` (JSON string or
    dict) -- not LangChain's ``args`` format.
    """
    msg = MagicMock()
    msg.content = ""
    msg.tool_calls = tool_calls
    return msg


# ===========================================================================
# _parse_tool_call tests
# ===========================================================================


class TestParseToolCall:
    """Tests for _parse_tool_call normalization."""

    def test_dict_style_with_json_arguments(self):
        """Dict-style tool call with JSON string arguments is parsed correctly."""
        tc = {
            "id": "call_001",
            "name": "test_tool",
            "arguments": '{"key": "value", "num": 42}',
        }
        tc_id, tc_name, tc_args = _parse_tool_call(tc)
        assert tc_id == "call_001"
        assert tc_name == "test_tool"
        assert tc_args == {"key": "value", "num": 42}

    def test_dict_style_with_dict_arguments(self):
        """Dict-style tool call with dict arguments is parsed correctly."""
        tc = {
            "id": "call_002",
            "name": "update_intent",
            "arguments": {"city": "上海", "budget": 500},
        }
        tc_id, tc_name, tc_args = _parse_tool_call(tc)
        assert tc_id == "call_002"
        assert tc_name == "update_intent"
        assert tc_args == {"city": "上海", "budget": 500}

    def test_object_style(self):
        """Object-style tool call (with .id, .name, .attributes) is parsed."""

        class ObjectStyleCall:
            id = "call_003"
            name = "ask_user"
            arguments = {"message": "Hello"}

        tc = ObjectStyleCall()
        tc_id, tc_name, tc_args = _parse_tool_call(tc)
        assert tc_id == "call_003"
        assert tc_name == "ask_user"
        assert tc_args == {"message": "Hello"}

    def test_object_style_with_json_arguments(self):
        """Object-style with JSON string arguments returns raw string (no parsing for object style).

        Note: ``_parse_tool_call`` only does ``json.loads`` for dict-style tool
        calls.  Object-style tool calls return ``tc.arguments`` as-is.
        """
        class ObjectStyleCall:
            id = "call_004"
            name = "test_tool"
            arguments = '{"key": "value"}'

        tc = ObjectStyleCall()
        tc_id, tc_name, tc_args = _parse_tool_call(tc)
        assert tc_id == "call_004"
        assert tc_name == "test_tool"
        # Object-style returns raw string (no JSON parse)
        assert tc_args == '{"key": "value"}'


# ===========================================================================
# _apply_state_update tests
# ===========================================================================


class TestApplyStateUpdate:
    """Tests for _apply_state_update."""

    def test_update_intent_merges_fields(self):
        """update_intent fills in fields, preserving existing ones."""
        state: PlanState = {
            "intent": {"city": "北京", "budget": 300},
        }
        updates = _apply_state_update(state, "update_intent", {
            "budget": 500,
            "guest_count": 4,
            "preferences": ["自然", "文化"],
        })
        assert "intent" in updates
        intent = updates["intent"]
        assert intent["city"] == "北京"       # preserved from state
        assert intent["budget"] == 500        # overwritten
        assert intent["guest_count"] == 4     # new
        assert intent["preferences"] == ["自然", "文化"]  # new

    def test_update_intent_skips_empty_values(self):
        """Empty string and empty list args are not merged."""
        state: PlanState = {
            "intent": {"city": "北京"},
        }
        updates = _apply_state_update(state, "update_intent", {
            "city": "",           # should be skipped
            "preferences": [],    # should be skipped
            "guest_count": 3,     # should be added
        })
        intent = updates["intent"]
        assert intent["city"] == "北京"  # unchanged
        assert intent["guest_count"] == 3

    def test_update_intent_none_values_skipped(self):
        """None values in update_intent args are not merged."""
        state: PlanState = {
            "intent": {"city": "北京", "budget": 300},
        }
        updates = _apply_state_update(state, "update_intent", {
            "city": None,
            "budget": None,
            "guest_count": 2,
        })
        intent = updates["intent"]
        assert intent["city"] == "北京"   # preserved
        assert intent["budget"] == 300     # preserved
        assert intent["guest_count"] == 2  # new

    def test_update_profile(self):
        """update_profile fills in profile fields."""
        state: PlanState = {
            "user_profile": {"dietary_tendency": "vegetarian"},
        }
        updates = _apply_state_update(state, "update_profile", {
            "budget_tendency": "mid",
            "travel_style": "relaxed",
        })
        profile = updates["user_profile"]
        assert profile["dietary_tendency"] == "vegetarian"  # preserved
        assert profile["budget_tendency"] == "mid"
        assert profile["travel_style"] == "relaxed"

    def test_update_profile_none_values_skipped(self):
        """None values in update_profile are not merged."""
        state: PlanState = {
            "user_profile": {"dietary_tendency": "vegetarian"},
        }
        updates = _apply_state_update(state, "update_profile", {
            "budget_tendency": None,
        })
        profile = updates["user_profile"]
        assert profile["dietary_tendency"] == "vegetarian"
        assert "budget_tendency" not in profile

    def test_update_itinerary(self):
        """update_itinerary creates itinerary and selected_solution."""
        state: PlanState = {}
        updates = _apply_state_update(state, "update_itinerary", {
            "summary": "一日游",
            "slots": [{"time_start": "09:00"}],
            "total_cost": 300,
            "total_time_min": 480,
            "activity_name": "公园",
            "restaurant_name": "亲子餐厅",
        })
        assert updates["itinerary"]["summary"] == "一日游"
        assert updates["itinerary"]["total_cost"] == 300
        assert updates["selected_solution"]["activity_name"] == "公园"
        assert updates["selected_solution"]["restaurant_name"] == "亲子餐厅"

    def test_update_itinerary_defaults(self):
        """update_itinerary uses empty defaults for missing fields."""
        state: PlanState = {}
        updates = _apply_state_update(state, "update_itinerary", {})
        assert updates["itinerary"]["summary"] == ""
        assert updates["itinerary"]["slots"] == []
        assert updates["itinerary"]["total_cost"] == 0
        assert updates["itinerary"]["total_time_min"] == 0
        assert updates["selected_solution"]["activity_name"] == ""
        assert updates["selected_solution"]["restaurant_name"] == ""

    def test_unknown_tool_name(self):
        """Unknown tool name returns empty updates dict."""
        updates = _apply_state_update({}, "nonexistent_tool", {})
        assert updates == {}


# ===========================================================================
# tool_node integration tests
# ===========================================================================


class TestToolNode:
    """Tests for the full tool_node coroutine."""

    # -- User-facing tools --------------------------------------------------

    @pytest.mark.asyncio
    async def test_user_facing_tool(self):
        """ask_user tool call sets hitl_payload and produces a ToolMessage."""
        last_msg = _make_last_msg([
            {
                "name": "ask_user",
                "arguments": '{"message": "你预算多少？", "options": ["300", "500"]}',
                "id": "call_hitl_001",
            }
        ])
        state: PlanState = {"messages": [last_msg]}

        result = await tool_node(state)

        assert result["hitl_payload"] is not None
        assert result["hitl_payload"]["type"] == "ask_user"
        assert result["hitl_payload"]["message"] == "你预算多少？"
        assert result["hitl_payload"]["options"] == ["300", "500"]
        assert len(result["messages"]) == 1
        tm = result["messages"][0]
        assert tm.tool_call_id == "call_hitl_001"

    @pytest.mark.asyncio
    async def test_present_plan_tool(self):
        """present_plan tool call sets hitl_payload with plan data and predefined options."""
        last_msg = _make_last_msg([
            {
                "name": "present_plan",
                "arguments": {
                    "message": "这是方案",
                    "plan": {"summary": "一日游", "total_cost": 300},
                },
                "id": "call_plan_001",
            }
        ])
        state: PlanState = {"messages": [last_msg]}

        result = await tool_node(state)

        assert result["hitl_payload"] is not None
        assert result["hitl_payload"]["type"] == "present_plan"
        assert result["hitl_payload"]["plan"]["summary"] == "一日游"
        assert result["hitl_payload"]["options"] == ["confirmed", "modified", "rejected"]

    @pytest.mark.asyncio
    async def test_present_plan_no_plan_data(self):
        """present_plan with missing plan dict still creates hitl_payload."""
        last_msg = _make_last_msg([
            {
                "name": "present_plan",
                "arguments": {"message": "这是方案"},
                "id": "call_plan_002",
            }
        ])
        state: PlanState = {"messages": [last_msg]}

        result = await tool_node(state)

        assert result["hitl_payload"] is not None
        assert result["hitl_payload"]["type"] == "present_plan"
        assert result["hitl_payload"]["plan"] == {}  # empty default

    # -- Internal state tools -----------------------------------------------

    @pytest.mark.asyncio
    async def test_internal_state_tool(self):
        """update_intent tool call updates state and produces a ToolMessage."""
        last_msg = _make_last_msg([
            {
                "name": "update_intent",
                "arguments": {"city": "上海", "budget": 500},
                "id": "call_intent_001",
            }
        ])
        state: PlanState = {"messages": [last_msg], "intent": {"city": "北京"}}

        result = await tool_node(state)

        assert "intent" in result
        assert result["intent"]["city"] == "上海"
        assert result["intent"]["budget"] == 500

        assert len(result["messages"]) == 1
        tm = result["messages"][0]
        assert "state_updated" in tm.content

    @pytest.mark.asyncio
    async def test_internal_state_tool_update_profile(self):
        """update_profile tool call updates user_profile in state."""
        last_msg = _make_last_msg([
            {
                "name": "update_profile",
                "arguments": {"budget_tendency": "luxury", "travel_style": "relaxed"},
                "id": "call_prof_001",
            }
        ])
        state: PlanState = {
            "messages": [last_msg],
            "user_profile": {"dietary_tendency": "vegetarian"},
        }

        result = await tool_node(state)

        assert "user_profile" in result
        assert result["user_profile"]["budget_tendency"] == "luxury"
        assert result["user_profile"]["travel_style"] == "relaxed"
        assert result["user_profile"]["dietary_tendency"] == "vegetarian"

    @pytest.mark.asyncio
    async def test_internal_state_tool_update_itinerary(self):
        """update_itinerary tool call creates itinerary in state."""
        last_msg = _make_last_msg([
            {
                "name": "update_itinerary",
                "arguments": {
                    "summary": "半日游",
                    "slots": [{"time_start": "14:00"}],
                    "total_cost": 150,
                },
                "id": "call_it_001",
            }
        ])
        state: PlanState = {"messages": [last_msg]}

        result = await tool_node(state)

        assert "itinerary" in result
        assert result["itinerary"]["summary"] == "半日游"
        assert result["itinerary"]["total_cost"] == 150

    # -- Execution tools (Saga path) ---------------------------------------

    @pytest.mark.asyncio
    async def test_execution_tool_saga_no_harness(self):
        """mock_order_create with no harness available produces error ToolMessage."""
        last_msg = _make_last_msg([
            {
                "name": "mock_order_create",
                "arguments": {"order_type": "restaurant", "item_id": "rst-1"},
                "id": "call_exec_001",
            }
        ])
        state: PlanState = {"messages": [last_msg]}

        result = await tool_node(state)

        assert len(result["messages"]) == 1
        tm = result["messages"][0]
        assert "ToolHarness not available" in tm.content

    @pytest.mark.asyncio
    async def test_execution_tool_saga_with_harness(self):
        """mock_order_create with harness goes through SagaCoordinator path."""
        last_msg = _make_last_msg([
            {
                "name": "mock_order_create",
                "arguments": {"order_type": "restaurant", "item_id": "rst-1"},
                "id": "call_exec_002",
            }
        ])
        state: PlanState = {"messages": [last_msg]}

        saga_result = [
            {
                "tc_id": "call_exec_002",
                "success": True,
                "data": {"order_id": "ord-001", "status": "confirmed"},
                "saga_status": "done",
            }
        ]

        mock_harness = MagicMock()
        mock_ctx = MagicMock()

        with patch("agent.tool_node._get_harness_and_session",
                   return_value=(mock_harness, mock_ctx)):
            with patch("agent.tool_node._execute_saga", AsyncMock(return_value=saga_result)):
                result = await tool_node(state)

        assert len(result["messages"]) == 1
        tm = result["messages"][0]
        data = json.loads(tm.content)
        assert data["order_id"] == "ord-001"

    @pytest.mark.asyncio
    async def test_execution_tool_saga_failure(self):
        """When SagaCoordinator returns failure, error data is captured."""
        last_msg = _make_last_msg([
            {
                "name": "mock_payment_charge",
                "arguments": {"order_id": "ord-001", "amount": 300},
                "id": "call_exec_003",
            }
        ])
        state: PlanState = {"messages": [last_msg]}

        saga_result = [
            {
                "tc_id": "call_exec_003",
                "success": False,
                "data": {"error": "Payment declined: insufficient funds"},
                "saga_status": "failed",
            }
        ]

        mock_harness = MagicMock()
        mock_ctx = MagicMock()

        with patch("agent.tool_node._get_harness_and_session",
                   return_value=(mock_harness, mock_ctx)):
            with patch("agent.tool_node._execute_saga", AsyncMock(return_value=saga_result)):
                result = await tool_node(state)

        assert len(result["messages"]) == 1
        tm = result["messages"][0]
        data = json.loads(tm.content)
        assert "error" in data
        assert "insufficient funds" in data["error"]

    # -- Standard tool (requires harness) -----------------------------------

    @pytest.mark.asyncio
    async def test_standard_tool_no_harness(self):
        """Standard tool call with no harness returns error ToolMessage."""
        last_msg = _make_last_msg([
            {
                "name": "amap_poi_search",
                "arguments": '{"keywords": "公园", "city": "北京"}',
                "id": "call_std_001",
            }
        ])
        state: PlanState = {"messages": [last_msg]}

        result = await tool_node(state)

        assert len(result["messages"]) == 1
        tm = result["messages"][0]
        assert "ToolHarness not available" in tm.content

    @pytest.mark.asyncio
    async def test_standard_tool_with_harness(self):
        """Standard tool call with harness goes through harness.execute."""
        last_msg = _make_last_msg([
            {
                "name": "amap_poi_search",
                "arguments": {"keywords": "公园", "city": "北京"},
                "id": "call_std_002",
            }
        ])
        state: PlanState = {"messages": [last_msg]}

        mock_harness = MagicMock()
        mock_harness.execute = AsyncMock(return_value=MagicMock(
            success=True,
            data={"pois": [{"name": "朝阳公园"}]},
        ))
        mock_ctx = MagicMock()

        with patch("agent.tool_node._get_harness_and_session",
                   return_value=(mock_harness, mock_ctx)):
            result = await tool_node(state)

        assert len(result["messages"]) == 1
        tm = result["messages"][0]
        data = json.loads(tm.content)
        assert len(data["pois"]) == 1
        assert data["pois"][0]["name"] == "朝阳公园"

    @pytest.mark.asyncio
    async def test_standard_tool_harness_exception(self):
        """When harness.execute raises an exception, error ToolMessage is returned."""
        last_msg = _make_last_msg([
            {
                "name": "amap_poi_search",
                "arguments": {"keywords": "公园", "city": "北京"},
                "id": "call_std_003",
            }
        ])
        state: PlanState = {"messages": [last_msg]}

        mock_harness = MagicMock()
        mock_harness.execute = AsyncMock(side_effect=RuntimeError("API timeout"))
        mock_ctx = MagicMock()

        with patch("agent.tool_node._get_harness_and_session",
                   return_value=(mock_harness, mock_ctx)):
            result = await tool_node(state)

        assert len(result["messages"]) == 1
        tm = result["messages"][0]
        data = json.loads(tm.content)
        assert "error" in data
        assert "RuntimeError" in data["error"]
        assert "API timeout" in data["error"]

    @pytest.mark.asyncio
    async def test_standard_tool_harness_failed_result(self):
        """When harness returns failed ToolResult, error data is captured."""
        last_msg = _make_last_msg([
            {
                "name": "amap_poi_search",
                "arguments": {"keywords": "nowhere"},
                "id": "call_std_004",
            }
        ])
        state: PlanState = {"messages": [last_msg]}

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.data = {"error": "No results found"}
        mock_harness = MagicMock()
        mock_harness.execute = AsyncMock(return_value=mock_result)
        mock_ctx = MagicMock()

        with patch("agent.tool_node._get_harness_and_session",
                   return_value=(mock_harness, mock_ctx)):
            result = await tool_node(state)

        assert len(result["messages"]) == 1
        tm = result["messages"][0]
        data = json.loads(tm.content)
        assert data["error"] == "No results found"

    # -- Mixed tool calls ---------------------------------------------------

    @pytest.mark.asyncio
    async def test_mixed_tool_calls(self):
        """Multiple tool calls of different types are handled together."""
        last_msg = _make_last_msg([
            {
                "name": "ask_user",
                "arguments": {"message": "确认吗?"},
                "id": "call_mix_001",
            },
            {
                "name": "update_intent",
                "arguments": {"city": "广州"},
                "id": "call_mix_002",
            },
        ])
        state: PlanState = {"messages": [last_msg], "intent": {"city": "深圳"}}

        result = await tool_node(state)

        # hitl_payload is set for user-facing tool
        assert result["hitl_payload"] is not None
        assert result["hitl_payload"]["type"] == "ask_user"

        # State update for internal tool
        assert result["intent"]["city"] == "广州"

        # Two ToolMessages produced
        assert len(result["messages"]) == 2
        assert result["messages"][0].tool_call_id == "call_mix_001"
        assert result["messages"][1].tool_call_id == "call_mix_002"

    @pytest.mark.asyncio
    async def test_mixed_all_three_types(self):
        """Tool calls from all three categories are dispatched correctly."""
        mock_harness = MagicMock()
        mock_harness.execute = AsyncMock(return_value=MagicMock(
            success=True,
            data={"pois": [{"name": "Test"}]},
        ))
        mock_ctx = MagicMock()

        last_msg = _make_last_msg([
            {
                "name": "ask_user",
                "arguments": {"message": "确认?"},
                "id": "call_all_001",
            },
            {
                "name": "update_intent",
                "arguments": {"city": "上海"},
                "id": "call_all_002",
            },
            {
                "name": "amap_poi_search",
                "arguments": {"keywords": "公园"},
                "id": "call_all_003",
            },
            {
                "name": "mock_order_create",
                "arguments": {"order_type": "restaurant", "item_id": "rst-1"},
                "id": "call_all_004",
            },
        ])
        state: PlanState = {"messages": [last_msg]}

        saga_result = [
            {
                "tc_id": "call_all_004",
                "success": True,
                "data": {"order_id": "ord-001"},
                "saga_status": "done",
            }
        ]

        with patch("agent.tool_node._get_harness_and_session",
                   return_value=(mock_harness, mock_ctx)):
            with patch("agent.tool_node._execute_saga", AsyncMock(return_value=saga_result)):
                result = await tool_node(state)

        # hitl_payload from ask_user
        assert result["hitl_payload"] is not None

        # 4 ToolMessages
        assert len(result["messages"]) == 4

        # State update from update_intent
        assert result["intent"]["city"] == "上海"

    # -- No tool_calls on last message --------------------------------------

    @pytest.mark.asyncio
    async def test_no_tool_calls(self):
        """Last message without tool_calls returns empty results."""
        last_msg = MagicMock()
        last_msg.content = "这是最终回复"
        last_msg.tool_calls = []
        state: PlanState = {"messages": [last_msg]}

        result = await tool_node(state)

        assert result["hitl_payload"] is None
        assert result["messages"] == []


# ===========================================================================
# Tool name constants checks
# ===========================================================================


class TestToolNameConstants:
    """Sanity checks on the USER_FACING_NAMES and EXECUTION_NAMES constants."""

    def test_user_facing_names(self):
        assert USER_FACING_NAMES == {"ask_user", "present_plan", "present_booking"}

    def test_execution_names(self):
        assert EXECUTION_NAMES == {"mock_order_create", "mock_payment_charge"}
