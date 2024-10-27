# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Local bot interface for Intentional.
"""

from typing import Any, Dict

import logging
import asyncio
import base64
import threading

from pynput import keyboard
from intentional_core import (
    BotInterface,
    BotStructure,
    ContinuousStreamBotStructure,
    TurnBasedBotStructure,
    load_bot_structure_from_dict,
    IntentRouter,
)
from intentional_local.handlers import InputHandler, AudioHandler

from intentional_textual_ui.audio_stream_ui import AudioStreamInterface
from intentional_textual_ui.text_chat_ui import TextChatInterface


logger = logging.getLogger(__name__)


class TextualUIBotInterface(BotInterface):
    """
    Bot that uses a Textual UI command line interface to interact with the user.
    """

    name = "textual_ui"

    def __init__(self, config: Dict[str, Any], intent_router: IntentRouter):
        # Init the structure
        bot_structure_config = config.pop("bot", None)
        if not bot_structure_config:
            raise ValueError(
                "TextualUIBotInterface requires a 'bot' configuration key to know how to structure the bot."
            )
        logger.debug("Creating bot structure of type '%s'", bot_structure_config)
        self.bot: BotStructure = load_bot_structure_from_dict(bot_structure_config, intent_router)

        # Check the modality
        self.modality = config.pop("modality")
        logger.debug("Modality for TextualUIBotInterface is set to: %s", self.modality)

        self.audio_handler = None
        self.input_handler = None

    async def run(self) -> None:
        """
        Chooses the specific loop to use for this combination of bot and modality and kicks it off.
        """
        if isinstance(self.bot, ContinuousStreamBotStructure):
            if self.modality == "audio_stream":
                await self._run_audio_stream(self.bot)
            else:
                raise ValueError(
                    f"Modality '{self.modality}' is not yet supported for '{self.bot.name}' bots."
                    "These are the supported modalities: 'audio_stream'."
                )

        if isinstance(self.bot, TurnBasedBotStructure):
            if self.modality == "text_turns":
                await self._run_text_turns(self.bot)
            else:
                raise ValueError(
                    f"Modality '{self.modality}' is not yet supported for '{self.bot.name}' bots."
                    "These are the supported modalities: 'text_turns'."
                )

    async def _run_text_turns(self, bot: TurnBasedBotStructure) -> None:
        """
        Runs the CLI interface for the text turns modality.
        """
        logger.debug("Running the TextualUIBotInterface in text turns mode.")
        app = TextChatInterface(
            send_message_callback=bot.send_message,
            check_end_conversation=lambda: self.bot.model.conversation_ended,
        )
        app._loop = asyncio.get_running_loop()
        app._thread_id = threading.get_ident()
        with app._context():
            try:
                await app.run_async(
                    headless=False, inline=False, inline_no_clear=False, mouse=True, size=None, auto_pilot=None
                )
            finally:
                app._loop = None
                app._thread_id = 0

    async def _run_audio_stream(self, bot: ContinuousStreamBotStructure) -> None:
        """
        Runs the CLI interface for the continuous audio streaming modality.
        """
        logger.debug("Running the TextualUIBotInterface in continuous audio streaming mode.")

        # Create the handlers
        self.audio_handler = AudioHandler()
        self.input_handler = InputHandler()
        self.input_handler.loop = asyncio.get_running_loop()

        # Connect the event handlers
        bot.add_event_handler("*", self.check_for_transcripts)
        # bot.add_event_handler("on_text_message", self.handle_text_messages)
        bot.add_event_handler("on_audio_message", self.handle_audio_messages)
        bot.add_event_handler("on_speech_started", self.speech_started)
        bot.add_event_handler("on_speech_stopped", self.speech_stopped)

        # Start keyboard listener in a separate thread
        listener = keyboard.Listener(on_press=self.input_handler.on_press)
        listener.start()

        try:

            logger.debug("Asking the bot to connect to the model...")
            await bot.connect()

            # Start continuous audio streaming
            asyncio.create_task(self.audio_handler.start_streaming(bot.stream_data))

            self.app = AudioStreamInterface()
            self.app.run()

            self.app._loop = asyncio.get_running_loop()
            self.app._thread_id = threading.get_ident()
            with self.app._context():
                try:
                    asyncio.gather(
                        self.app.run_async(
                            headless=False, inline=False, inline_no_clear=False, mouse=True, size=None, auto_pilot=None
                        ),
                        bot.run(),
                    )

                finally:
                    self.app._loop = None
                    self.app._thread_id = 0

        except Exception as e:  # pylint: disable=broad-except
            raise e
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
            self.app.update_chat_history(f"[{event["type"]}] {event['transcript']}")

    # async def handle_text_messages(self, event: Dict[str, Any]) -> None:
    #     """
    #     Prints to the console any text message from the bot.

    #     Args:
    #         event: The event dictionary containing the message.
    #     """
    #     print(f"Assistant: {event['delta']}")

    async def handle_audio_messages(self, event: Dict[str, Any]) -> None:
        """
        Plays audio responses from the bot.

        Args:
            event: The event dictionary containing the audio message.
        """
        self.app.update_bot_listening_status("talking")
        self.audio_handler.play_audio(base64.b64decode(event["delta"]))
        self.app.update_bot_listening_status("listening")

    async def speech_started(self, event: Dict[str, Any]) -> None:  # pylint: disable=unused-argument
        """
        Prints to the console when the bot starts speaking.

        Args:
            event: The event dictionary containing the speech start event.
        """
        self.app.update_user_speaking_status("speaking")

        # Handle interruptions if it is the case
        played_milliseconds = self.audio_handler.stop_playback_immediately()
        logging.debug("Played the response for %s milliseconds.", played_milliseconds)

        # If we're interrupting the bot, handle the interruption on the model side too
        if played_milliseconds:
            self.app.update_bot_listening_status("listening")
            logging.info("Handling interruption...")
            await self.bot.handle_interruption(played_milliseconds)

    async def speech_stopped(self, event: Dict[str, Any]) -> None:  # pylint: disable=unused-argument
        """
        Prints to the console when the bot stops speaking.

        Args:
            event: The event dictionary containing the speech stop event.
        """
        self.app.update_user_speaking_status("silent")
