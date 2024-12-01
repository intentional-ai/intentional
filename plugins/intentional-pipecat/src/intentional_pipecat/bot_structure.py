# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Pipecat bot structure implementation.
"""

from typing import Dict, Any, AsyncGenerator

import os
import asyncio

import structlog

from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.azure import AzureTTSService
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.pipeline.pipeline import Pipeline
from pipecat.frames.frames import TextFrame, LLMFullResponseStartFrame, LLMFullResponseEndFrame
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import LLMUserResponseAggregator
from pipecat.transports.base_transport import TransportParams

from intentional_core.intent_routing import IntentRouter
from intentional_core.bot_structure import BotStructure
from intentional_core.llm_client import LLMClient, load_llm_client_from_dict

from intentional_pipecat.frame_processor import UserToLLMFrameProcessor, LLMToUserFrameProcessor
from intentional_pipecat.transport import AudioTransport


log = structlog.get_logger(logger_name=__name__)


class PipecatBotStructure(BotStructure):
    """
    Bot structure that uses Pipecat to make text-only models able to handle spoken input.
    """

    name = "pipecat"

    def __init__(self, config: Dict[str, Any], intent_router: IntentRouter):
        """
        Args:
            config:
                The configuration dictionary for the bot structure.
                It includes only the LLM definition under the `llm` key.
        """
        super().__init__()
        log.debug("Loading bot structure from config", bot_structure_config=config)

        # Init the model client
        llm_config = config.pop("llm", None)
        if not llm_config:
            raise ValueError(f"{self.__class__.__name__} requires a 'llm' configuration key.")
        self.llm: LLMClient = load_llm_client_from_dict(parent=self, intent_router=intent_router, config=llm_config)

        # Pipecat pipeline
        self.pipecat_task = None
        self.publisher = None
        self.transport = None

    async def connect(self) -> None:
        """
        Initializes the model and connects to it as/if necessary.
        """
        # Prepares the Pipecat pipeline
        transport_params = TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            transcription_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(start_secs=0.1, stop_secs=0.1, min_volume=0.6)),
            vad_audio_passthrough=True,
        )
        self.transport = AudioTransport(transport_params, self.llm.emit)

        stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"), sample_rate=16000)
        tts = AzureTTSService(api_key=os.getenv("AZURE_SPEECH_API_KEY"), region=os.getenv("AZURE_SPEECH_REGION"))
        user_response = LLMUserResponseAggregator()
        send_to_llm = UserToLLMFrameProcessor(self.llm)
        self.publisher = LLMToUserFrameProcessor()
        pipeline = Pipeline(
            [
                self.transport.input(),
                stt,
                user_response,
                send_to_llm,
                self.publisher,
                tts,
                self.transport.output(),
            ]
        )
        self.pipecat_task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

        self.add_event_handler("on_text_message_from_llm", self.handle_llm_text_messages)
        self.add_event_handler("on_llm_starts_generating_response", self.handle_llm_starts_generating_response)
        self.add_event_handler("on_llm_stops_generating_response", self.handle_llm_stops_generating_response)
        # Start the pipeline
        asyncio.create_task(self.pipecat_task.run())
        # Wait for the pipeline to actually connect and start
        while True:
            if self.transport.input().ready:
                break
            await asyncio.sleep(0.1)
        # Connects to the model, if necessary
        await self.llm.connect()

    async def handle_llm_text_messages(self, event: Dict[str, Any]) -> None:
        """
        Sends the text message to the Pipecat pipeline to be converted into audio.
        """
        if event["delta"]:
            await self.publisher.push_frame(TextFrame(event["delta"]), FrameDirection.DOWNSTREAM)

    async def handle_llm_starts_generating_response(self, _: Dict[str, Any]) -> None:
        """
        Warns the Pipecat pipeline of the start of a response from the LLM by sending an LLMFullResponseStartFrame()
        """
        await self.publisher.push_frame(LLMFullResponseStartFrame(), FrameDirection.DOWNSTREAM)

    async def handle_llm_stops_generating_response(self, _: Dict[str, Any]) -> None:
        """
        Warns the Pipecat pipeline of the end of a response from the LLM by sending an LLMFullResponseEndFrame()
        """
        await self.publisher.push_frame(LLMFullResponseEndFrame(), FrameDirection.DOWNSTREAM)

    async def disconnect(self) -> None:
        """
        Disconnects from the LLM and unloads/closes it as/if necessary.
        """
        await self.llm.disconnect()

    async def run(self) -> None:
        """
        Main loop for the bot.
        """
        log.debug(".run() is no-op for PipecatBotStructure, the Pipecat pipeline is self-sufficient.")

    async def send(self, data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Sends a message to the LLM and forward the response.

        Args:
            data: The message to send to the model in OpenAI format, like {"role": "user", "content": "Hello!"}
        """
        if "audio_chunk" in data:
            await self.transport.input().send_audio_frame(data["audio_chunk"])
        else:
            raise ValueError("PipecatBotStructure only supports audio data for now.")

    async def handle_interruption(self, lenght_to_interruption: int) -> None:
        """
        Handle an interruption in the streaming.

        Args:
            lenght_to_interruption: The length of the data that was produced to the user before the interruption.
                This value could be number of characters, number of words, milliseconds, number of audio frames, etc.
                depending on the bot structure that implements it.
        """
        log.warning("handle interruptions: TODO")
