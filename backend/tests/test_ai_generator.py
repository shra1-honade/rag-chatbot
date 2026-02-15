"""Unit tests for AIGenerator sequential tool calling"""
import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from ai_generator import AIGenerator


def make_text_block(text):
    return SimpleNamespace(type="text", text=text)


def make_tool_use_block(tool_id, name, input_args):
    return SimpleNamespace(type="tool_use", id=tool_id, name=name, input=input_args)


def make_response(stop_reason, content_blocks):
    return SimpleNamespace(stop_reason=stop_reason, content=content_blocks)


@pytest.fixture
def generator():
    with patch("ai_generator.anthropic.Anthropic") as MockClient:
        gen = AIGenerator(api_key="test-key", model="test-model")
        gen.client = MockClient()
        yield gen


@pytest.fixture
def tool_manager():
    mgr = MagicMock()
    mgr.execute_tool = MagicMock(return_value="tool result text")
    return mgr


@pytest.fixture
def sample_tools():
    return [{"name": "search_course_content", "description": "Search", "input_schema": {}}]


class TestDirectTextResponse:
    def test_no_tools_returns_text(self, generator):
        generator.client.messages.create.return_value = make_response(
            "end_turn", [make_text_block("Hello!")]
        )
        result = generator.generate_response("hi")
        assert result == "Hello!"
        assert generator.client.messages.create.call_count == 1

    def test_tools_provided_but_claude_responds_with_text(self, generator, tool_manager, sample_tools):
        generator.client.messages.create.return_value = make_response(
            "end_turn", [make_text_block("Direct answer")]
        )
        result = generator.generate_response("hi", tools=sample_tools, tool_manager=tool_manager)
        assert result == "Direct answer"
        assert generator.client.messages.create.call_count == 1
        tool_manager.execute_tool.assert_not_called()


class TestSingleToolRound:
    def test_one_tool_call_then_text(self, generator, tool_manager, sample_tools):
        tool_response = make_response("tool_use", [
            make_tool_use_block("t1", "search_course_content", {"query": "python"})
        ])
        text_response = make_response("end_turn", [make_text_block("Here are the results")])
        generator.client.messages.create.side_effect = [tool_response, text_response]

        result = generator.generate_response("search python", tools=sample_tools, tool_manager=tool_manager)

        assert result == "Here are the results"
        assert generator.client.messages.create.call_count == 2
        tool_manager.execute_tool.assert_called_once_with("search_course_content", query="python")

        # Second API call should still include tools (round 1 < MAX_TOOL_ROUNDS)
        second_call_kwargs = generator.client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs

    def test_tool_results_included_in_messages(self, generator, tool_manager, sample_tools):
        tool_response = make_response("tool_use", [
            make_tool_use_block("t1", "search_course_content", {"query": "test"})
        ])
        text_response = make_response("end_turn", [make_text_block("Answer")])
        generator.client.messages.create.side_effect = [tool_response, text_response]

        generator.generate_response("test", tools=sample_tools, tool_manager=tool_manager)

        second_call_kwargs = generator.client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]
        # messages: [user, assistant(tool_use), user(tool_result)]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"][0]["type"] == "tool_result"
        assert messages[2]["content"][0]["content"] == "tool result text"


class TestTwoSequentialToolRounds:
    def test_two_rounds_then_text(self, generator, tool_manager, sample_tools):
        tool_response_1 = make_response("tool_use", [
            make_tool_use_block("t1", "get_course_outline", {"course_title": "MCP"})
        ])
        tool_response_2 = make_response("tool_use", [
            make_tool_use_block("t2", "search_course_content", {"query": "lesson 4 topic"})
        ])
        text_response = make_response("end_turn", [make_text_block("Final answer")])

        generator.client.messages.create.side_effect = [tool_response_1, tool_response_2, text_response]
        tool_manager.execute_tool.side_effect = ["outline result", "search result"]

        result = generator.generate_response("complex query", tools=sample_tools, tool_manager=tool_manager)

        assert result == "Final answer"
        assert generator.client.messages.create.call_count == 3
        assert tool_manager.execute_tool.call_count == 2

        # Third call (forced final) should NOT have tools
        third_call_kwargs = generator.client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs

    def test_messages_accumulate_across_rounds(self, generator, tool_manager, sample_tools):
        tool_response_1 = make_response("tool_use", [
            make_tool_use_block("t1", "get_course_outline", {"course_title": "X"})
        ])
        tool_response_2 = make_response("tool_use", [
            make_tool_use_block("t2", "search_course_content", {"query": "y"})
        ])
        text_response = make_response("end_turn", [make_text_block("Done")])

        generator.client.messages.create.side_effect = [tool_response_1, tool_response_2, text_response]
        tool_manager.execute_tool.side_effect = ["result1", "result2"]

        generator.generate_response("q", tools=sample_tools, tool_manager=tool_manager)

        # Final call messages: user, assistant, tool_result, assistant, tool_result
        final_call_kwargs = generator.client.messages.create.call_args_list[2][1]
        messages = final_call_kwargs["messages"]
        assert len(messages) == 5
        roles = [m["role"] for m in messages]
        assert roles == ["user", "assistant", "user", "assistant", "user"]


class TestErrorHandling:
    def test_tool_exception_sends_error_as_result(self, generator, tool_manager, sample_tools):
        tool_response = make_response("tool_use", [
            make_tool_use_block("t1", "search_course_content", {"query": "test"})
        ])
        text_response = make_response("end_turn", [make_text_block("Sorry, error occurred")])
        generator.client.messages.create.side_effect = [tool_response, text_response]
        tool_manager.execute_tool.side_effect = Exception("connection failed")

        result = generator.generate_response("test", tools=sample_tools, tool_manager=tool_manager)

        assert result == "Sorry, error occurred"
        # After error, tools should be removed to force text
        second_call_kwargs = generator.client.messages.create.call_args_list[1][1]
        assert "tools" not in second_call_kwargs
        # Error message should be in tool result
        messages = second_call_kwargs["messages"]
        tool_result_content = messages[2]["content"][0]["content"]
        assert "Error executing tool" in tool_result_content
        assert "connection failed" in tool_result_content

    def test_tool_not_found_string_passed_through(self, generator, tool_manager, sample_tools):
        tool_response = make_response("tool_use", [
            make_tool_use_block("t1", "bad_tool", {"query": "test"})
        ])
        text_response = make_response("end_turn", [make_text_block("No tool found")])
        generator.client.messages.create.side_effect = [tool_response, text_response]
        tool_manager.execute_tool.return_value = "Tool 'bad_tool' not found"

        result = generator.generate_response("test", tools=sample_tools, tool_manager=tool_manager)

        assert result == "No tool found"


class TestConversationHistory:
    def test_history_included_in_system_prompt(self, generator):
        generator.client.messages.create.return_value = make_response(
            "end_turn", [make_text_block("response")]
        )
        generator.generate_response("hi", conversation_history="User: hello\nAI: hi there")

        call_kwargs = generator.client.messages.create.call_args_list[0][1]
        assert "Previous conversation:" in call_kwargs["system"]
        assert "User: hello" in call_kwargs["system"]

    def test_no_history_uses_base_prompt(self, generator):
        generator.client.messages.create.return_value = make_response(
            "end_turn", [make_text_block("response")]
        )
        generator.generate_response("hi")

        call_kwargs = generator.client.messages.create.call_args_list[0][1]
        assert "Previous conversation:" not in call_kwargs["system"]


class TestMixedContentBlocks:
    def test_text_extracted_from_mixed_response(self, generator):
        response = make_response("end_turn", [
            make_text_block("The answer"),
            make_tool_use_block("t1", "search", {"q": "x"})
        ])
        generator.client.messages.create.return_value = response

        result = generator.generate_response("test")
        assert result == "The answer"

    def test_fallback_when_no_text_block(self, generator):
        result = generator._extract_text(make_response("end_turn", []))
        assert result == "I was unable to generate a response."


class TestNoToolManager:
    def test_tool_use_response_without_manager_extracts_text(self, generator, sample_tools):
        """If tool_manager is None, tool_use responses should still return any text content."""
        response = make_response("tool_use", [
            make_text_block("Partial text"),
            make_tool_use_block("t1", "search", {"q": "x"})
        ])
        generator.client.messages.create.return_value = response

        result = generator.generate_response("test", tools=sample_tools)
        assert result == "Partial text"
        assert generator.client.messages.create.call_count == 1
