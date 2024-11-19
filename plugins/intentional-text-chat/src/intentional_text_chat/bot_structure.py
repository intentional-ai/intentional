# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Bot structure to support text chat for Intentional.
"""
from typing import Any, Dict, AsyncGenerator

import logging
from intentional_core import TurnBasedBotStructure, TurnBasedModelClient, load_model_client_from_dict, IntentRouter


logger = logging.getLogger("intentional")


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
        self.model: TurnBasedModelClient = load_model_client_from_dict(
            parent=self, intent_router=intent_router, config=llm_config
        )

    async def connect(self) -> None:
        await self.model.connect()

    async def disconnect(self) -> None:
        await self.model.disconnect()

    async def run(self) -> None:
        """
        Main loop for the bot.
        """
        await self.model.run()

    async def send(self, data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Sends a message to the model and forward the response.

        Args:
            data: The message to send to the model in OpenAI format, like {"role": "user", "content": "Hello!"}
        """
        await self.model.send({"text_message": data})

    async def handle_interruption(self, lenght_to_interruption: int) -> None:
        """
        Handle an interruption in the streaming.

        Args:
            lenght_to_interruption: The length of the data that was produced to the user before the interruption.
                This value could be number of characters, number of words, milliseconds, number of audio frames, etc.
                depending on the bot structure that implements it.
        """
        logger.warning("TODO! Interruption not yet supported in text chat bot structure.")
