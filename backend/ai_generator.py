import anthropic
from typing import List, Optional

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive tools for course information.

Search Tool Usage:
- **Content Search**: Use for questions about specific course content or detailed educational materials
- **Course Outline**: Use for questions about course structure, lesson lists, or "what's in this course" queries
- You may use up to 2 tools sequentially when a query requires multiple pieces of information (e.g., get a course outline then search for related content)
- Synthesize tool results into accurate, fact-based responses
- If tool yields no results, state this clearly without offering alternatives

Outline Query Protocol:
- When a user asks about course outlines or lesson lists, use get_course_outline
- Return the course title, course link, and complete list of lessons with numbers and titles
- Format the response clearly with the course name, link, and numbered lesson list

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Initial API call
        response = self.client.messages.create(**api_params)

        # Tool calling loop: handle up to MAX_TOOL_ROUNDS sequential tool calls
        for round_num in range(self.MAX_TOOL_ROUNDS):
            if response.stop_reason != "tool_use" or not tool_manager:
                break

            # Append assistant's tool_use response
            api_params["messages"].append({"role": "assistant", "content": response.content})

            # Execute tools and collect results
            tool_results = []
            tool_failed = False
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                    except Exception as e:
                        result = f"Error executing tool: {e}"
                        tool_failed = True
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            api_params["messages"].append({"role": "user", "content": tool_results})

            # On last allowed round or tool failure, remove tools to force text
            is_last_round = (round_num == self.MAX_TOOL_ROUNDS - 1)
            if tool_failed or is_last_round:
                api_params.pop("tools", None)
                api_params.pop("tool_choice", None)

            response = self.client.messages.create(**api_params)

        return self._extract_text(response)

    def _extract_text(self, response) -> str:
        """Extract text from a response, handling mixed content blocks."""
        for block in response.content:
            if block.type == "text":
                return block.text
        return "I was unable to generate a response."
