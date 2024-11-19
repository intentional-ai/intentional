# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Textual UI for audio stream bots.
"""

from typing import Dict, Any
import base64
import structlog
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.containers import Horizontal, Vertical
from textual.widgets import Markdown
from intentional_core import ContinuousStreamBotStructure
from intentional_terminal.handlers import AudioHandler


log = structlog.get_logger(logger_name=__name__)


class ChatHistory(Markdown):
    """
    A markdown widget that displays the chat history.
    """


class UserStatus(Markdown):
    """
    A markdown widget that displays the user status (speaking/silent).
    """


class SystemPrompt(Markdown):
    """
    A markdown widget that displays the system prompt.
    """


class AudioStreamInterface(App):
    """
    The main interface class for the audio stream bot UI.
    """

    CSS_PATH = "example.tcss"

    def __init__(self, bot: ContinuousStreamBotStructure, audio_output_handler: "AudioHandler"):
        super().__init__()
        self.bot = bot
        self.audio_handler = audio_output_handler
        self.bot.add_event_handler("on_audio_message_from_model", self.handle_audio_messages)
        self.bot.add_event_handler("on_model_speech_transcribed", self.handle_transcript)
        self.bot.add_event_handler("on_user_speech_transcribed", self.handle_transcript)
        self.bot.add_event_handler("on_user_speech_started", self.handle_start_user_response)
        self.bot.add_event_handler("on_user_speech_ended", self.handle_finish_user_response)
        self.bot.add_event_handler("on_system_prompt_updated", self.handle_system_prompt_updated)

        self.conversation = ""

    def compose(self) -> ComposeResult:
        """
        Layout of the UI.
        """
        yield Horizontal(
            Vertical(
                Markdown("# Chat History"),
                ScrollableContainer(ChatHistory()),
                UserStatus("# User is silent..."),
                classes="column bordered chat",
            ),
            Vertical(
                Markdown("# System Prompt"),
                SystemPrompt(),
                classes="bordered column",
            ),
        )

    def on_mount(self) -> None:
        """
        Operations to be performed at mount time.
        """
        self.query_one(SystemPrompt).update(self.bot.model.system_prompt)

    async def handle_transcript(self, event: Dict[str, Any]) -> None:
        """
        Prints the transcripts in the chat history.
        """
        if event["type"] == "on_user_speech_transcribed":
            self.conversation += f"\n**User:** {event['transcript']}\n"
        elif event["type"] == "on_model_speech_transcribed":
            self.conversation += f"\n**Assistant:** {event['transcript']}\n"
        else:
            log.debug("Unknown event with transcript received.", event_name=event["type"])
            self.conversation += f"\n**{event['type']}:** {event['transcript']}\n"
        self.query_one(ChatHistory).update(self.conversation)

    async def handle_system_prompt_updated(self, event: Dict[str, Any]) -> None:
        """
        Prints to the console any text message from the bot.

        Args:
            event: The event dictionary containing the message.
        """
        self.query_one(SystemPrompt).update(event["system_prompt"])  # self.bot.model.system_prompt)

    async def handle_start_user_response(self, _) -> None:
        """
        Updates the user status when they start speaking.
        """
        self.query_one(UserStatus).update("# User is speaking...")

    async def handle_finish_user_response(self, _) -> None:
        """
        Updates the user status when they stop speaking.
        """
        self.query_one(UserStatus).update("# User is silent...")

    async def handle_audio_messages(self, event: Dict[str, Any]) -> None:
        """
        Plays audio responses from the bot and updates the bot status line.

        Args:
            event: The event dictionary containing the audio message.
        """
        # self.query_one(BotStatus).update("# Bot is speaking...")
        if event["delta"]:
            self.audio_handler.play_audio(base64.b64decode(event["delta"]))
