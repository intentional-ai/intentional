# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Websocket bot structure for Intentional.
"""
from typing import Any, Dict
import logging

from intentional_core import ContinuousStreamBotStructure
from intentional_core import ContinuousStreamModelClient, load_model_client_from_dict


logger = logging.getLogger(__name__)


class WebsocketBotStructure(ContinuousStreamBotStructure):
    """
    Bot structure implementation for OpenAI's Realtime API and similar direct, continuous streaming LLM APIs.
    """

    name = "websocket"

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config:
                The configuration dictionary for the bot structure.
        """
        super().__init__()
        logger.debug("Loading WebsocketBotStructure from config: %s", config)

        # Init the model client
        llm_config = config.pop("llm", None)
        if not llm_config:
            raise ValueError("WebsocketBotStructure requires a 'llm' configuration key to know which model to use.")
        self.model: ContinuousStreamModelClient = load_model_client_from_dict(llm_config)

        self.model.parent_event_handler = self.handle_event

    async def run(self) -> None:
        """
        Main loop for the bot.
        """
        await self.model.handle_messages()

    async def stream_data(self, data: bytes) -> None:
        await self.model.stream_data(data)

    async def connect(self) -> None:
        logger.debug("Connecting to the model.")
        await self.model.connect()

    async def disconnect(self) -> None:
        await self.model.disconnect()
