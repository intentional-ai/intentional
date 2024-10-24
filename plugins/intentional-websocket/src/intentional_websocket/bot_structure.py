# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Websocket bot structure for Intentional.
"""

import logging
from intentional_core import TurnBasedBotStructure, ContinuousStreamBotStructure
from intentional_core import ModelClient, load_model_client_from_dict


logger = logging.getLogger(__name__)


class WebsocketBotStructure(TurnBasedBotStructure, ContinuousStreamBotStructure):
    """
    Bot structure implementation for OpenAI's Realtime API and similar direct, continuous streaming LLM APIs.
    """

    name = "websocket"

    def __init__(self, config):
        """
        Args:

            config:
                The configuration dictionary for the bot structure.
        """
        logger.debug("Loading WebsocketBotStructure from config: %s", config)

        # Init the model client
        llm_config = config.pop("llm", None)
        if not llm_config:
            raise ValueError("WebsocketBotStructure requires a 'llm' configuration key to know which model to use.")
        self.model: ModelClient = load_model_client_from_dict(llm_config)

    async def run(self) -> None:
        """
        Main loop for the bot.
        """

    async def stream_data(self, data: bytes) -> None:
        self.model.stream_data(data)

    async def send_message(self, message: dict) -> None:
        self.model.send_message(message)

    async def connect(self) -> None:
        self.model.connect()

    async def disconnect(self) -> None:
        self.model.disconnect()
