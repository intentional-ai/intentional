# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Client for OpenAI's Chat Completion API.
"""

from typing import Any, Dict, List

import os
import logging

import openai
from intentional_core import TurnBasedModelClient


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

        self.system_prompt = config.get("system_prompt", "You're a helpful assistant.")
        self.tools = config.get("tools", [])

        self.client = openai.AsyncOpenAI(api_key=self.api_key)

    async def send_message(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send a message to the model.
        """
        return await self.client.chat.completions.create(
            model=self.model_name,
            messages=conversation,
            stream=True,
            n=1,
        )
