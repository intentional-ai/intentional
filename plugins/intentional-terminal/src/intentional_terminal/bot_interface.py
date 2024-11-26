# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Local bot interface for Intentional.
"""

from typing import Any, Dict

import sys
import asyncio
import base64

import structlog
from pynput import keyboard
from intentional_core import (
    BotInterface,
    BotStructure,
    ContinuousStreamBotStructure,
    TurnBasedBotStructure,
    load_bot_structure_from_dict,
    IntentRouter,
)

from intentional_terminal.handlers import InputHandler, AudioHandler


log = structlog.get_logger(logger_name=__name__)


class TerminalBotInterface(BotInterface):
    """
    Bot that uses the local command line interface to interact with the user.
    """

    name = "terminal"

    def __init__(self, intent_router: IntentRouter, config: Dict[str, Any]):
        # Init the structure
        bot_structure_config = config.pop("bot", None)
        if not bot_structure_config:
            raise ValueError(
                f"{self.__class__.__name__} requires a 'bot' configuration key to know how to structure the bot."
            )
        log.debug("Creating bot structure", bot_structure_type=bot_structure_config)
        self.intent_router = intent_router
        self.bot_structure_config = bot_structure_config
        self.bot: BotStructure = load_bot_structure_from_dict(self.intent_router, self.bot_structure_config)

        # Check the modality
        self.modality = config.pop("modality")
        log.debug("Setting interface modality", modality=self.modality)

        self.audio_handler = None
        self.input_handler = None

    async def run(self) -> None:
        """
        Chooses the specific loop to use for this combination of bot and modality and kicks it off.
        """
        log.debug("Running the bot", bot_type=self.bot.__class__.__name__, modality=self.modality)

        if isinstance(self.bot, ContinuousStreamBotStructure):
            if self.modality == "audio_stream":
                await self._run_audio_stream(self.bot)
            else:
                raise ValueError(
                    f"Modality '{self.modality}' is not yet supported for '{self.bot.name}' bots."
                    "These are the supported modalities: 'audio_stream'."
                )

        if isinstance(self.bot, TurnBasedBotStructure):
            if self.modality == "text_messages":
                await self._run_text_messages(self.bot)
            else:
                raise ValueError(
                    f"Modality '{self.modality}' is not yet supported for '{self.bot.name}' bots."
                    "These are the supported modalities: 'text_messages'."
                )

    async def _run_text_messages(self, bot: TurnBasedBotStructure) -> None:
        """
        Runs the CLI interface for the text turns modality.
        """
        bot.add_event_handler("on_text_message_from_model", self.handle_text_messages)
        bot.add_event_handler("on_model_starts_generating_response", self.handle_start_text_response)
        bot.add_event_handler("on_model_stops_generating_response", self.handle_finish_text_response)
        bot.add_event_handler("on_model_connection", self.handle_model_connection)
        bot.add_event_handler("on_conversation_ended", self.handle_conversation_ended)
        await bot.connect()

    async def _run_audio_stream(self, bot: ContinuousStreamBotStructure) -> None:
        """
        Runs the CLI interface for the continuous audio streaming modality.
        """
        # Create the handlers
        self.audio_handler = AudioHandler()
        self.input_handler = InputHandler()
        self.input_handler.loop = asyncio.get_running_loop()

        # Connect the event handlers
        bot.add_event_handler("*", self.check_for_transcripts)
        bot.add_event_handler("on_conversation_ended", self.handle_conversation_ended)
        # bot.add_event_handler("on_text_message_from_model", self.handle_text_messages)
        bot.add_event_handler("on_audio_message_from_model", self.handle_audio_messages)
        bot.add_event_handler("on_user_speech_started", self.speech_started)
        bot.add_event_handler("on_user_speech_ended", self.speech_stopped)

        # Start keyboard listener in a separate thread
        listener = keyboard.Listener(on_press=self.input_handler.on_press)
        listener.start()

        try:
            log.debug("Connecting to the model")
            await bot.connect()
            asyncio.create_task(bot.run())

            print("Chat is ready. Start speaking!")
            print("Press 'q' to quit")
            print("")

            # Start continuous audio streaming
            asyncio.create_task(self.audio_handler.start_streaming(bot.send))

            # Simple input loop for quit command
            while True:
                command, _ = await self.input_handler.command_queue.get()

                if command == "q":
                    break

        except Exception:  # pylint: disable=broad-except
            log.exception("An error occurred")
        finally:
            self.audio_handler.stop_streaming()
            self.audio_handler.cleanup()
            await bot.disconnect()
            print("Chat is finished. Bye!")

    async def check_for_transcripts(self, event: Dict[str, Any]) -> None:
        """
        Checks for transcripts from the bot.

        Args:
            event: The event dictionary containing the transcript.
        """
        if "transcript" in event:
            print(f"[{event['type']}] Transcript: {event['transcript']}")

    async def handle_start_text_response(self, _) -> None:
        """
        Prints to the console when the bot starts generating a text response.
        """
        print("Assistant: ", end="")

    async def handle_finish_text_response(self, _) -> None:
        """
        Prints to the console when the bot starts generating a text response.
        """
        print("")
        await self.bot.send({"role": "user", "content": input("User: ")})

    async def handle_model_connection(self, event: Dict[str, Any]) -> None:
        """
        Prints to the console when the bot connects to the model.

        Args:
            event: The event dictionary containing the model connection event.
        """
        print("==> Chat is ready!")
        await self.handle_finish_text_response(event)

    async def handle_text_messages(self, event: Dict[str, Any]) -> None:
        """
        Prints to the console any text message from the bot.

        Args:
            event: The event dictionary containing the message.
        """
        if event["delta"]:
            print(event["delta"], end="", flush=True)

    async def handle_audio_messages(self, event: Dict[str, Any]) -> None:
        """
        Plays audio responses from the bot.

        Args:
            event: The event dictionary containing the audio message.
        """
        self.audio_handler.play_audio(base64.b64decode(event["delta"]))

    async def speech_started(self, event: Dict[str, Any]) -> None:  # pylint: disable=unused-argument
        """
        Prints to the console when the bot starts speaking.

        Args:
            event: The event dictionary containing the speech start event.
        """
        print("[User is speaking]")

        # Handle interruptions if it is the case
        played_milliseconds = self.audio_handler.stop_playback_immediately()
        log.debug("Audio response played", play_duration=played_milliseconds)

        # If we're interrupting the bot, handle the interruption on the model side too
        if played_milliseconds:
            log.info("Handling interruption", play_duration=played_milliseconds)
            await self.bot.handle_interruption(played_milliseconds)

    async def speech_stopped(self, event: Dict[str, Any]) -> None:  # pylint: disable=unused-argument
        """
        Prints to the console when the bot stops speaking.

        Args:
            event: The event dictionary containing the speech stop event.
        """
        print("[User stopped speaking]")

    async def handle_conversation_ended(self, _):
        """
        The conversation is over, so let's ask the user if they want to have another go.
        """
        restart = input("==> The conversation was ended by the bot. Do you want to restart? (y/N)")
        if "y" not in restart.lower():
            sys.exit(0)

        self.bot: BotStructure = load_bot_structure_from_dict(self.intent_router, self.bot_structure_config)
        await self.run()
