# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Local bot interface for Intentional.
"""

from typing import Any, Dict, List, Callable

import asyncio
import threading

import structlog
from intentional_core import (
    BotInterface,
    BotStructure,
    ContinuousStreamBotStructure,
    TurnBasedBotStructure,
    load_bot_structure_from_dict,
    IntentRouter,
)
from intentional_terminal.handlers import AudioHandler

from intentional_textual_ui.audio_stream_ui import AudioStreamInterface
from intentional_textual_ui.text_chat_ui import TextChatInterface


log = structlog.get_logger(logger_name=__name__)


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
                f"{self.__class__.__name__} requires a 'bot' configuration key to know how to structure the bot."
            )
        log.debug("Creating bot structure", bot_structure_config=bot_structure_config)
        self.bot: BotStructure = load_bot_structure_from_dict(intent_router=intent_router, config=bot_structure_config)

        # Check the modality
        self.modality = config.pop("modality")
        log.debug("Setting modality for bot structure", modality=self.modality)

        # Handlers
        self.audio_handler = None
        self.input_handler = None
        self.app = None

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
        log.debug("Running in text turns mode.")
        self.app = TextChatInterface(bot=bot)
        await bot.connect()
        await self._launch_ui()

    async def _run_audio_stream(self, bot: ContinuousStreamBotStructure) -> None:
        """
        Runs the CLI interface for the continuous audio streaming modality.
        """
        log.debug("Running in continuous audio streaming mode.")

        try:
            self.audio_handler = AudioHandler()
            self.app = AudioStreamInterface(bot=bot, audio_output_handler=self.audio_handler)
            await bot.connect()
            await self._launch_ui(gather=[self.bot.run()])
            await self.audio_handler.start_streaming(bot.send)

        except Exception as e:  # pylint: disable=broad-except
            raise e
        finally:
            self.audio_handler.stop_streaming()
            self.audio_handler.cleanup()
            await bot.disconnect()
            print("Chat is finished. Bye!")

    async def _launch_ui(self, gather: List[Callable] = None):
        """
        Launches the Textual UI interface. If there's any async task that should be run in parallel, it can be passed
        as a list of callables to the `gather` parameter.

        Args:
            gather: A list of callables that should be run in parallel with the UI.
        """
        self.app._loop = asyncio.get_running_loop()  # pylint: disable=protected-access
        self.app._thread_id = threading.get_ident()  # pylint: disable=protected-access
        with self.app._context():  # pylint: disable=protected-access
            try:
                if not gather:
                    await self.app.run_async(
                        headless=False, inline=False, inline_no_clear=False, mouse=True, size=None, auto_pilot=None
                    )
                else:
                    asyncio.gather(
                        self.app.run_async(
                            headless=False, inline=False, inline_no_clear=False, mouse=True, size=None, auto_pilot=None
                        ),
                        *gather,
                    )
            finally:
                self.app._loop = None  # pylint: disable=protected-access
                self.app._thread_id = 0  # pylint: disable=protected-access
