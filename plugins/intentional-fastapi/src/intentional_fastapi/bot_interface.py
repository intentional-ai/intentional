# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
FastAPI REST API interface for Intentional.
"""
from typing import Any, Dict

import structlog

from intentional_core import (
    BotInterface,
    BotStructure,
    TurnBasedBotStructure,
    ContinuousStreamBotStructure,
    load_bot_structure_from_dict,
    IntentRouter,
)
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import StreamingResponse


log = structlog.get_logger(logger_name=__name__)


class ResponseChunksIterator:
    """
    Async iterator that collects the response chunks from the bot and streams them out.
    """

    def __init__(self):
        self.buffer = []

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.buffer:
            raise StopAsyncIteration

        next_chunk = self.buffer[0]
        self.buffer = self.buffer[1:]
        return next_chunk

    async def asend(self, value):  # pylint: disable=missing-function-docstring
        self.buffer.append(value)
        return


class FastAPIBotInterface(BotInterface):
    """
    Bot that lets you use a FastAPI REST API to interact with the user.
    """

    name = "fastapi"

    def __init__(self, config: Dict[str, Any], intent_router: IntentRouter):
        # Init the structure
        bot_structure_config = config.pop("bot", None)
        if not bot_structure_config:
            raise ValueError(
                f"{self.__class__.__name__} requires a 'bot' configuration key to know how to structure the bot."
            )
        log.debug("Creating bot structure", bot_structure_config=bot_structure_config)
        self.bot: BotStructure = load_bot_structure_from_dict(intent_router=intent_router, config=bot_structure_config)

        # Check the modality
        self.modality = config.pop("modality")
        log.debug("Modality for %s is set", self.__class__.__name__, modality=self.modality)

    async def run(self) -> None:
        """
        Chooses the specific loop to use for this combination of bot and modality and kicks it off.
        """
        if isinstance(self.bot, TurnBasedBotStructure):
            if self.modality == "text_messages":
                await self._run_text_messages(self.bot)
            else:
                raise ValueError(
                    f"Modality '{self.modality}' is not yet supported by '{self.bot.name}' bots."
                    "These are the supported modalities: 'text_messages'."
                )
        elif isinstance(self.bot, ContinuousStreamBotStructure):
            if self.modality == "audio_stream":
                await self._run_audio_stream(self.bot)
            else:
                raise ValueError(
                    f"Modality '{self.modality}' is not yet supported by '{self.bot.name}' bots."
                    "These are the supported modalities: 'audio_stream'."
                )
        else:
            raise ValueError(f"Bot '{self.bot.name}' is not yet supported by {self.__class__.__name__}.")

    async def handle_response_chunks(self, response: ResponseChunksIterator, event: Dict[str, Any]) -> None:
        """
        Stream out text messages from the bot through a TextChunksIterator.
        """
        if event["delta"]:
            await response.asend(event["delta"])

    async def _run_text_messages(self, bot: TurnBasedBotStructure) -> None:
        """
        Runs the interface for the text turns modality.
        """
        app = FastAPI(title="Intentional FastAPI")

        @app.get("/send")
        async def send_message(message: str):
            """
            Send a message to the bot.
            """
            response = ResponseChunksIterator()
            bot.add_event_handler(
                "on_text_message_from_model", lambda event: self.handle_response_chunks(response, event)
            )
            await self.bot.send({"role": "user", "content": message})
            return StreamingResponse(response)

        await bot.connect()

        config = uvicorn.Config(app, host="0.0.0.0", port=8000)
        server = uvicorn.Server(config)
        await server.serve()

    # TODO TEST THIS MODALITY!
    async def _run_audio_stream(self, bot: ContinuousStreamBotStructure) -> None:
        """
        Runs the interface for the audio stream modality.
        """

        app = FastAPI(title="Intentional FastAPI")

        @app.get("/ws/input")
        async def input_stream(websocket: WebSocket):
            await websocket.accept()
            while True:
                data = await websocket.receive()
                self.bot.send({"audio_chunk": data})

        @app.get("/ws/output")
        async def output_stream(websocket: WebSocket):
            await websocket.accept()

            async def send_audio_chunk(event: Dict[str, Any]) -> None:
                if event["delta"]:
                    await websocket.send_bytes(event["delta"])

            response = ResponseChunksIterator()
            bot.add_event_handler("on_audio_message_from_model", send_audio_chunk)
            return StreamingResponse(response)

        await bot.connect()

        config = uvicorn.Config(app, host="0.0.0.0", port=8000)
        server = uvicorn.Server(config)
        await server.serve()
