# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Local bot interface for Intentional.
"""

from typing import Any, Dict

import logging
import asyncio
import base64

from pynput import keyboard
from intentional_core import (
    BotInterface,
    BotStructure,
    ContinuousStreamBotStructure,
    TurnBasedBotStructure,
    load_bot_structure_from_dict,
)

from intentional_local.handlers import InputHandler, AudioHandler


logger = logging.getLogger(__name__)


class LocalBotInterface(BotInterface):
    """
    Bot that uses the local command line interface to interact with the user.
    """

    name = "local"

    def __init__(self, config: Dict[str, Any]):
        # Init the structure
        bot_structure_config = config.pop("bot", None)
        if not bot_structure_config:
            raise ValueError("LocalBot requires a 'bot' configuration key to know how to structure the bot.")
        logger.debug("Creating bot structure of type '%s'", bot_structure_config)
        self.bot: BotStructure = load_bot_structure_from_dict(bot_structure_config)

        # Check the modality
        self.modality = config.pop("modality", "auto")
        logger.debug("Modality for LocalBotInterface is set to: %s", self.modality)

    async def run(self) -> None:
        """
        Chooses the specific loop to use for this combination of bot and modality and kicks it off.
        """
        if isinstance(self.bot, ContinuousStreamBotStructure):
            if self.modality == "continuous_audio":
                await self._run_audio_stream()
                return

        if isinstance(self.bot, TurnBasedBotStructure):
            if self.modality == "text":
                await self._run_text_turns()
                return

            if self.modality == "audio":
                await self._run_audio_turns()
                return

        raise ValueError(f"Modality '{self.modality}' is not yet supported for '{self.bot.name}' bots.")

    async def _run_text_turns(self) -> None:
        raise NotImplementedError("Text turns are not yet supported for LocalBotInterface.")

    async def _run_audio_turns(self) -> None:
        raise NotImplementedError("Audio turns are not yet supported for LocalBotInterface.")

    async def _run_audio_stream(self) -> None:
        """
        Runs the CLI interface for the continuous audio streaming modality.
        """
        # Create the handlers
        audio_handler = AudioHandler()
        input_handler = InputHandler()
        input_handler.loop = asyncio.get_running_loop()

        self.bot.event_handlers["response.text.delta"] = lambda event: print(
            f"\nAssistant: {event['delta']}", end="", flush=True
        )
        self.bot.event_handlers["response.audio.delta"] = lambda event: audio_handler.play_audio(
            base64.b64decode(event["delta"])
        )
        self.bot.event_handlers["user.interruption"] = audio_handler.stop_playback_immediately

        # Start keyboard listener in a separate thread
        listener = keyboard.Listener(on_press=input_handler.on_press)
        listener.start()

        try:
            await self.bot.connect()
            asyncio.create_task(self.bot.run())

            print("Connected to OpenAI Realtime API!")
            print("Audio streaming will start automatically.")
            print("Press 'q' to quit")
            print("")

            # Start continuous audio streaming
            asyncio.create_task(audio_handler.start_streaming(self.bot.stream_data))

            # Simple input loop for quit command
            while True:
                command, _ = await input_handler.command_queue.get()

                if command == "q":
                    break

        except Exception as e:  # pylint: disable=broad-except
            logger.exception("An error occurred: %s", str(e))
        finally:
            audio_handler.stop_streaming()
            audio_handler.cleanup()
            await self.bot.disconnect()
