# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

# SPDX-FileCopyrightText: 2024-present Kwal Inc. <sara@kwal.ai>
# SPDX-License-Identifier: MIT
"""
Pipecat frame processor implementation
"""
import structlog
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.frames.frames import (
    Frame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    LLMMessagesFrame,
)
from intentional_core.llm_client import LLMClient


log = structlog.get_logger(logger_name=__name__)


class UserToLLMFrameProcessor(FrameProcessor):
    """
    FrameProcessor that takes the user input and sends it to the LLM.
    """

    def __init__(self, llm_client: LLMClient):
        super().__init__()
        self.llm_client = llm_client
        self.transcription = ""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """
        Processes the incoming frames if relevant.
        """
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMMessagesFrame):
            user_message = frame.messages[-1]["content"]
            log.debug("LLMMessageFrame received, sending message to LLM", user_message=user_message)
            await self.llm_client.emit("on_user_speech_transcribed", {"type": "user", "transcript": user_message})
            await self.llm_client.send({"text_message": {"role": "user", "content": user_message}})
        else:
            if isinstance(frame, UserStartedSpeakingFrame):
                await self.llm_client.emit("on_user_speech_started", {})
            elif isinstance(frame, UserStoppedSpeakingFrame):
                await self.llm_client.emit("on_user_speech_ended", {})
            await self.push_frame(frame, direction)


class LLMToUserFrameProcessor(FrameProcessor):
    """
    FrameProcessor that takes the LLM output and sends it to the user.

    Note: this processor itself is doing nothing else than changing the default behavior of `process_frame()` to not
    swallow frames when they reach it. The processor is actually used by `PipecatBotStructure` to generate frames when
    a reply from the LLM is received.
    """

    def __init__(self):
        super().__init__()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """
        Simply forwards all framews ahead. The default behavior of FrameProcessor is to block them instead.
        """
        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)
