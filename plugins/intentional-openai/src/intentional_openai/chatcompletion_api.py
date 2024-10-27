# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Client for OpenAI's Chat Completion API.
"""

from typing import Any, Dict, List, AsyncGenerator

import os
import json
import logging

import openai
from intentional_core import TurnBasedModelClient
from intentional_openai.tools import to_openai_tool


logger = logging.getLogger(__name__)


class ChatCompletionAPIClient(TurnBasedModelClient):
    """
    A client for interacting with the OpenAI Chat Completion API.
    """

    name: str = "openai"

    def __init__(self, config: Dict[str, Any]):
        """
        A client for interacting with the OpenAI Chat Completion API.
        """
        logger.debug("Loading ChatCompletionAPIClient from config: %s", config)
        super().__init__()

        self.model_name = config.get("name")
        if not self.model_name:
            raise ValueError("ChatCompletionAPIClient requires a 'name' configuration key to know which model to use.")
        if "realtime" in self.model_name:
            raise ValueError(
                "ChatCompletionAPIClient doesn't support Realtime API. "
                "To use the Realtime API, use RealtimeAPIClient instead."
            )

        self.api_key_name = config.get("api_key_name", "OPENAI_API_KEY")
        if not os.environ.get(self.api_key_name):
            raise ValueError(
                "ChatCompletionAPIClient requires an API key to authenticate with OpenAI. "
                f"The provided environment variable name ({self.api_key_name}) is not set or is empty."
            )
        self.api_key = os.environ.get(self.api_key_name)

        self.system_prompt = config.get("system_prompt", "")
        self.tools = {}

        self.client = openai.AsyncOpenAI(api_key=self.api_key)
        self.conversation: List[Dict[str, Any]] = []
        self.intent_router = None
        self.conversation_ended = False

    async def send_message(self, message: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Send a message to the model.
        """
        if self.conversation_ended:
            yield None
            return

        if self.intent_router and not self.system_prompt:
            self.system_prompt, self.tools = await self.intent_router.run({})
            logger.debug("Setting initial system prompt: %s", self.system_prompt)
            logger.debug("Setting initial tools: %s", [t.name for t in self.tools])
            self.conversation.append({"role": "system", "content": self.system_prompt})

        # Generate a response
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=self.conversation + [message],
            stream=True,
            tools=[{"type": "function", "function": to_openai_tool(t)} for t in self.tools.values()]
            + [{"type": "function", "function": to_openai_tool(self.intent_router)}],
            tool_choice="auto",
            n=1,
        )

        call_id = ""
        function_name = ""
        function_args = ""
        assistant_response = ""

        async for r in response:
            if not call_id:
                call_id = r.to_dict()["id"]

            delta = r.to_dict()["choices"][0]["delta"]

            # If this is not a function call, just stream out
            if "tool_calls" not in delta:
                yield delta
                assistant_response += delta.get("content") or ""

            else:
                # TODO handle multiple parallel function calls
                if delta["tool_calls"][0]["index"] > 0 or len(delta["tool_calls"]) > 1:
                    logger.error("TODO: Multiple parallel function calls not supported yet. Please open an issue.")

                # Consume the response to understand which tool to call with which parameters
                for tool_call in delta["tool_calls"]:
                    # if not call_id:
                    #     call_id = tool_call["function"].get("id")
                    if not function_name:
                        function_name = tool_call["function"].get("name")
                    function_args += tool_call["function"]["arguments"]

        # If there was no function call, update the conversation history and return
        if not function_name:
            self.conversation.append(message)
            self.conversation.append({"role": "assistant", "content": assistant_response})
            self.print_conversation_history()
            return

        # Otherwise deal with the function call
        logger.debug("Function call detected: %s with args: %s", function_name, function_args)
        function_args = json.loads(function_args)

        # Routing function call - this is special because it should not be recorded in the conversation history
        if function_name == self.intent_router.name:
            self.system_prompt, self.tools = await self.intent_router.run(function_args)
            self.conversation = [{"role": "system", "content": self.system_prompt}] + self.conversation[1:]
            logger.debug("Setting system prompt: %s", self.system_prompt)
            logger.debug("Setting tools: %s", list(self.tools.keys()))
            self.print_conversation_history()

            # Send the same message again with the new system prompt and no trace of the routing call.
            # We don't append the message in order to avoid message duplication in the history.
            async for chunk in self.send_message(message):
                yield chunk
            return

        # TODO # End conversation function call
        # if function_name == "end_conversation":
        #     self.conversation_ended = True
        #     yield ""
        #     return

        # Handle a regular function call - this one shows up in the history as normal
        # so we start by appending the user message
        self.conversation.append(message)
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
        self.print_conversation_history()

        # Get the tools output
        logging.debug(
            "Calling tool %s with args %s. Picking from %s", function_name, function_args, list(self.tools.keys())
        )
        if function_name not in self.tools:
            output = f"Tool {function_name} not found."
        else:
            output = await self.tools[function_name].run(function_args)
        logger.debug("Tool output: %s", output)

        async for chunk in self.send_message({"role": "tool", "content": json.dumps(output), "tool_call_id": call_id}):
            yield chunk

    def print_conversation_history(self):
        """
        Print the conversation history.
        """
        logger.debug("---------------------------------")
        logger.debug("Conversation history:")
        for msg in self.conversation:
            logger.debug("%s: %s %s", msg["role"], msg.get("content", ""), msg.get("tool_calls", ""))
        if self.conversation_ended:
            logger.debug("-----Conversation has ended.-----")
        logger.debug("---------------------------------")
