# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Websocket bot structure for Intentional.
"""
from typing import Any, Dict
import structlog

from intentional_core import (
    ContinuousStreamBotStructure,
    ContinuousStreamModelClient,
    load_model_client_from_dict,
    IntentRouter,
)


log = structlog.get_logger(logger_name=__name__)


class WebsocketBotStructure(ContinuousStreamBotStructure):
    """
    Bot structure implementation for OpenAI's Realtime API and similar direct, continuous streaming LLM APIs.
    """

    name = "websocket"

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
            raise ValueError("WebsocketBotStructure requires a 'llm' configuration key to know which model to use.")
        self.model: ContinuousStreamModelClient = load_model_client_from_dict(
            parent=self, intent_router=intent_router, config=llm_config
        )

    async def run(self) -> None:
        await self.model.run()

    async def send(self, data: Dict[str, Any]) -> None:
        await self.model.send(data)

    async def connect(self) -> None:
        await self.model.connect()

    async def disconnect(self) -> None:
        await self.model.disconnect()

    async def handle_interruption(self, lenght_to_interruption: int) -> None:
        await self.model.handle_interruption(lenght_to_interruption)
