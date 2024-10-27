# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Websocket bot structure for Intentional.
"""
from typing import Any, Dict
import logging

from intentional_core import (
    ContinuousStreamBotStructure,
    TurnBasedModelClient,
    load_model_client_from_dict,
    IntentRouter,
)

from intentional_transcribed_audio.vad import VADClient, load_vad_from_dict
from intentional_transcribed_audio.stt import STTClient, load_stt_from_dict
from intentional_transcribed_audio.tts import TTSClient, load_tts_from_dict


logger = logging.getLogger(__name__)


class TranscribedAudioBotStructure(ContinuousStreamBotStructure):
    """
    Bot structure implementation for the VAD-STT-LLM-TTS architecture.
    """

    name = "transcribed_audio"

    def __init__(self, config: Dict[str, Any], intent_router: IntentRouter):
        """
        Args:
            config:
                The configuration dictionary for the bot structure.
        """
        super().__init__()
        logger.debug("Loading TranscribedAudioBotStructure from config: %s", config)

        # Init the model client
        llm_config = config.pop("llm", None)
        if not llm_config:
            raise ValueError("TranscribedAudioBotStructure requires a 'llm' config key to know which model to use.")
        self.llm: TurnBasedModelClient = load_model_client_from_dict(llm_config)

        # Init the VAD
        vad_config = config.pop("vad", None)
        if not vad_config:
            raise ValueError("TranscribedAudioBotStructure requires a 'vad' config key to know which VAD to use.")
        self.vad: VADClient = load_vad_from_dict(vad_config)

        # Init the STT
        stt_config = config.pop("stt", None)
        if not stt_config:
            raise ValueError("TranscribedAudioBotStructure requires a 'stt' config key to know which STT to use.")
        self.stt: STTClient = load_stt_from_dict(stt_config)

        # Init the TTS
        tts_config = config.pop("tts", None)
        if not tts_config:
            raise ValueError("TranscribedAudioBotStructure requires a 'tts' config key to know which TTS to use.")
        self.tts: TTSClient = load_tts_from_dict(tts_config)

        self.llm.parent_event_handler = self.handle_event
        self.llm.intent_router = intent_router

    async def run(self) -> None:
        """
        Main loop for the bot.
        """
        await self.llm.run()

    async def stream_data(self, data: bytes) -> None:
        await self.llm.stream_data(data)

    async def connect(self) -> None:
        logger.debug("connect() is no-op in TranscribedAudioBotStructure.")

    async def disconnect(self) -> None:
        logger.debug("disconnect() is no-op in TranscribedAudioBotStructure.")

    async def handle_interruption(self, lenght_to_interruption: int) -> None:
        print("TODO handle_interruption")
        # await self.llm.handle_interruption(lenght_to_interruption)
