# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Client for OpenAI's Chat Completion API.
"""

from typing import Any, Dict, List, AsyncGenerator, TYPE_CHECKING

import os
import json
import structlog

import openai
from intentional_core import TurnBasedModelClient
from intentional_core.intent_routing import IntentRouter
from intentional_core.end_conversation import EndConversationTool
from intentional_openai.tools import to_openai_tool

if TYPE_CHECKING:
    from intentional_core.bot_structure import BotStructure


log = structlog.get_logger(logger_name=__name__)


class ChatCompletionAPIClient(TurnBasedModelClient):
    """
    A client for interacting with the OpenAI Chat Completion API.
    """

    name: str = "openai"

    def __init__(self, parent: "BotStructure", intent_router: IntentRouter, config: Dict[str, Any]):
        """
        A client for interacting with the OpenAI Chat Completion API.

        Args:
            parent: The parent bot structure.
            intent_router: The intent router.
            config: The configuration dictionary.
        """
        log.debug("Loading ChatCompletionAPIClient from config", model_client_config=config)
        super().__init__(parent, intent_router)

        self.model_name = config.get("name")
        if not self.model_name:
            raise ValueError("ChatCompletionAPIClient requires a 'name' configuration key to know which model to use.")
        if "realtime" in self.model_name:
            raise ValueError(
                "ChatCompletionAPIClient doesn't support Realtime API. "
                "To use the Realtime API, use RealtimeAPIClient instead (client: openai_realtime)"
            )

        self.api_key_name = config.get("api_key_name", "OPENAI_API_KEY")
        if not os.environ.get(self.api_key_name):
            raise ValueError(
                "ChatCompletionAPIClient requires an API key to authenticate with OpenAI. "
                f"The provided environment variable name ({self.api_key_name}) is not set or is empty."
            )
        self.api_key = os.environ.get(self.api_key_name)
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
        self.system_prompt = None
        self.tools = None
        self.setup_initial_prompt()
        self.conversation = [{"role": "system", "content": self.system_prompt}]

    def setup_initial_prompt(self) -> None:
        """
        Setup initial prompt and tools. Used also after conversation end to reset the state.
        """
        self.system_prompt = self.intent_router.get_prompt()
        self.tools = self.intent_router.current_stage.tools
        self.conversation: List[Dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]
        log.debug("Initial system prompt set", system_prompt=self.system_prompt)

    async def run(self) -> None:
        """
        Handle events from the model by either processing them internally or by translating them into higher-level
        events that the BotStructure class can understand, then re-emitting them.
        """
        log.debug("ChatCompletionAPIClient.run() is no-op for now")

    async def update_system_prompt(self) -> None:
        """
        Update the system prompt in the model.
        """
        self.conversation = [{"role": "system", "content": self.system_prompt}] + self.conversation[1:]
        await self.emit("on_system_prompt_updated", {"system_prompt": self.system_prompt})

    async def handle_interruption(self, lenght_to_interruption: int) -> None:
        """
        Handle an interruption while rendering the output to the user.

        Args:
            lenght_to_interruption: The length of the data that was produced to the user before the interruption.
                This value could be number of characters, number of words, milliseconds, number of audio frames, etc.
                depending on the bot structure that implements it.
        """
        log.warning("TODO! Implement handle_interruption in ChatCompletionAPIClient")

    async def send(self, data: Dict[str, Any]) -> None:
        """
        Send a message to the model.
        """
        await self.emit("on_model_starts_generating_response", {})

        # Generate a response
        message = data["text_message"]
        response = await self._send_message(message)

        # Unwrap the response to make sure it contains no function calls to handle
        call_id = ""
        function_name = ""
        function_args = ""
        assistant_response = ""
        async for r in response:
            if not call_id:
                call_id = r.to_dict()["id"]
            delta = r.to_dict()["choices"][0]["delta"]

            if "tool_calls" not in delta:
                # If this is not a function call, just stream out
                await self.emit("on_text_message_from_model", {"delta": delta.get("content")})
                assistant_response += delta.get("content") or ""
            else:
                # TODO handle multiple parallel function calls
                if delta["tool_calls"][0]["index"] > 0 or len(delta["tool_calls"]) > 1:
                    log.error("TODO: Multiple parallel function calls not supported yet. Please open an issue.")
                    log.debug("Multiple parallel function calls", delta=delta)
                # Consume the response to understand which tool to call with which parameters
                for tool_call in delta["tool_calls"]:
                    if not function_name:
                        function_name = tool_call["function"].get("name")
                    function_args += tool_call["function"]["arguments"]

        if not function_name:
            # If there was no function call, update the conversation history and return
            self.conversation.append(message)
            self.conversation.append({"role": "assistant", "content": assistant_response})
        else:
            # Otherwise deal with the function call
            await self._handle_function_call(message, call_id, function_name, function_args)

        await self.emit("on_model_stops_generating_response", {})

    async def _send_message(self, message: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate a response to a message.

        Args:
            message: The message to respond to.
        """
        return await self.client.chat.completions.create(
            model=self.model_name,
            messages=self.conversation + [message],
            stream=True,
            tools=[{"type": "function", "function": to_openai_tool(t)} for t in self.tools.values()],
            tool_choice="auto",
            n=1,
        )

    async def _handle_function_call(
        self, message: Dict[str, Any], call_id: str, function_name: str, function_args: str
    ):
        """
        Handle a function call from the model.
        """
        log.debug("Function call detected", function_name=function_name, function_args=function_args)
        function_args = json.loads(function_args)

        # Routing function call - this is special because it should not be recorded in the conversation history
        if function_name == self.intent_router.name:
            await self._route(function_args)
            # Send the same message again with the new system prompt and no trace of the routing call.
            # We don't append the user message to the history in order to avoid message duplication.
            await self.send({"text_message": message})

        # Check if the conversation should end
        elif function_name == EndConversationTool.name:
            await self.tools[EndConversationTool.name].run()
            self.setup_initial_prompt()
            await self.emit("on_conversation_ended", {})

        else:
            # Handle a regular function call - this one shows up in the history as normal
            # so we start by appending the user message
            self.conversation.append(message)
            output = await self._call_tool(call_id, function_name, function_args)
            await self.send({"text_message": {"role": "tool", "content": json.dumps(output), "tool_call_id": call_id}})

    async def _route(self, routing_info: Dict[str, Any]) -> None:
        """
        Runs the router to determine the next system prompt and tools to use.
        """
        self.system_prompt, self.tools = await self.intent_router.run(routing_info)
        await self.update_system_prompt()
        log.debug("System prompt updated", system_prompt=self.system_prompt)
        log.debug("Tools updated", tools=self.tools)

    async def _call_tool(self, call_id, function_name, function_args):
        """
        Call a tool with the given arguments.

        Args:
            call_id: The ID of the tool call.
            function_name: The name of the tool function to call.
            function_args: The arguments to pass to the tool
        """
        await self.emit("on_tool_invoked", {"name": function_name, "args": function_args})

        # Record the tool invocation in the conversation
        self.conversation.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"arguments": json.dumps(function_args), "name": function_name},
                    }
                ],
            }
        )

        # Get the tool output
        if function_name not in self.tools:
            log.debug("The LLM called a non-existing tool.", tool=function_name)
            output = f"Tool '{function_name}' not found."
        else:
            log.debug("Calling tool", function_name=function_name, function_args=function_args)
            output = await self.tools[function_name].run(function_args)
        log.debug("Tool run", tool_output=output)
        return output
