# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Bot structure to support text chat for Intentional.
"""
from typing import Any, Dict, AsyncGenerator

import structlog
from intentional_core.bot_structures.bot_structure import BotStructure
from intentional_core.llm_client import LLMClient, load_llm_client_from_dict
from intentional_core.intent_routing import IntentRouter


log = structlog.get_logger(logger_name=__name__)


class DirectToLLMBotStructure(BotStructure):
    """
    Bot structure implementation for text chat.
    """

    name = "direct_to_llm"

    def __init__(self, config: Dict[str, Any], intent_router: IntentRouter):
        """
        Args:
            config:
                The configuration dictionary for the bot structure.
        """
        super().__init__()
        log.debug("Loading bot structure from config", bot_structure_config=config)

        # Init the model client
        llm_config = config.pop("llm", None)
        if not llm_config:
            raise ValueError(f"{self.__class__.__name__} requires a 'llm' configuration key.")
        self.model: LLMClient = load_llm_client_from_dict(parent=self, intent_router=intent_router, config=llm_config)

    async def connect(self) -> None:
        """
        Initializes the model and connects to it as/if necessary.
        """
        await self.model.connect()

    async def disconnect(self) -> None:
        """
        Disconnects from the model and unloads/closes it as/if necessary.
        """
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
        await self.model.handle_interruption(lenght_to_interruption)
