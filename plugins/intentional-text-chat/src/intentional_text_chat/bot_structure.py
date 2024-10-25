# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Bot structure to support text chat for Intentional.
"""
from typing import Any, Dict

import logging
from intentional_core import TurnBasedBotStructure
from intentional_core import TurnBasedModelClient, load_model_client_from_dict


logger = logging.getLogger(__name__)


class TextChatBotStructure(TurnBasedBotStructure):
    """
    Bot structure implementation for text chat.
    """

    name = "text_chat"

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config:
                The configuration dictionary for the bot structure.
        """
        super().__init__()
        logger.debug("Loading TextChatBotStructure from config: %s", config)

        # Init the model client
        llm_config = config.pop("llm", None)
        if not llm_config:
            raise ValueError("TextChatBotStructure requires a 'llm' configuration key to know which model to use.")
        self.model: TurnBasedModelClient = load_model_client_from_dict(llm_config)

        self.conversation = []

    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends a message to the model and forward the response.

        Args:
            message:
                The message to send to the model in OpenAI format, like {"role": "user", "content": "Hello!"}
        """

        async def unwrap(response):
            async for r in response:
                yield r.to_dict()["choices"][0]["delta"]

        self.conversation.append(message)
        response = await self.model.send_message(self.conversation)
        return unwrap(response)
