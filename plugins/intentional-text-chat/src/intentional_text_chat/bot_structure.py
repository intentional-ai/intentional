# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Bot structure to support text chat for Intentional.
"""
from typing import Any, Dict, AsyncGenerator

import logging
from intentional_core import TurnBasedBotStructure, TurnBasedModelClient, load_model_client_from_dict, IntentRouter


logger = logging.getLogger(__name__)


class TextChatBotStructure(TurnBasedBotStructure):
    """
    Bot structure implementation for text chat.
    """

    name = "text_chat"

    def __init__(self, config: Dict[str, Any], intent_router: IntentRouter):
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
        self.model.intent_router = intent_router

    async def send_message(self, message: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Sends a message to the model and forward the response.

        Args:
            message:
                The message to send to the model in OpenAI format, like {"role": "user", "content": "Hello!"}
        """
        async for chunk in self.model.send_message(message):
            yield chunk
