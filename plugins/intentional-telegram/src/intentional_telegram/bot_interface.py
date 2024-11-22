# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Telegram bot interface for Intentional.
"""

from typing import Any, Dict
import os
import asyncio

import structlog

from intentional_core import (
    BotInterface,
    BotStructure,
    TurnBasedBotStructure,
    load_bot_structure_from_dict,
    IntentRouter,
)

from telegram import Update, Bot
from telegram.error import NetworkError, Forbidden


log = structlog.get_logger(logger_name=__name__)


class TelegramBotInterface(BotInterface):
    """
    Bot that uses Telegram to interact with the user.
    """

    name = "telegram"

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

        self.telegram_bot = None
        self.latest_update = None
        self.latest_message = ""

    async def run(self) -> None:
        """
        Chooses the specific loop to use for this combination of bot and modality and kicks it off.
        """
        if isinstance(self.bot, TurnBasedBotStructure):
            if self.modality == "text_messages":
                await self._run_text_messages(self.bot)
            else:
                raise ValueError(
                    f"Modality '{self.modality}' is not yet supported for '{self.bot.name}' bots."
                    "These are the supported modalities: 'text_messages'."
                )
        else:
            raise ValueError(f"Bot '{self.bot.name}' is not yet supported for {self.__class__.__name__}.")

    async def _run_text_messages(self, bot: TurnBasedBotStructure) -> None:
        """
        Runs the CLI interface for the text turns modality.
        """
        async with Bot(os.getenv("TELEGRAM_BOT_TOKEN")) as telegram_bot:

            # Startup by checking it there's any new update
            async for update in updates_generator(telegram_bot):
                log.debug("Past Telegram updates processed", telegram_updates=update)
                self.latest_update = update
                break

            bot.add_event_handler("on_text_message_from_model", self.handle_text_messages)
            bot.add_event_handler("on_model_starts_generating_response", self.handle_start_text_response)
            bot.add_event_handler("on_model_stops_generating_response", self.handle_finish_text_response)

            await bot.connect()
            await self._process_updates(telegram_bot)

    async def handle_text_messages(self, event: Dict[str, Any]) -> None:
        """
        Accumulates text messages delta
        """
        if event["delta"]:
            self.latest_message += event["delta"]

    async def handle_start_text_response(self, _) -> None:
        """
        Resets the current message's content
        """
        self.latest_message = ""

    async def handle_finish_text_response(self, _) -> None:
        """
        Publishes the message on the Telegram chat
        """
        if self.latest_message:
            await self.latest_update.message.reply_text(self.latest_message)
            self.latest_message = ""

    async def _process_updates(self, telegram_bot) -> None:
        """
        Process updates from the telegram bot.
        """
        async for update in updates_generator(telegram_bot):
            log.info("Received Telegram update", telegram_update=update)
            if update.message:
                # If the message is a text message, send it to the bot
                if update.message.text:
                    await self.bot.send({"role": "user", "content": update.message.text})
                    self.latest_update = update

            if update.message_reaction:
                await self.bot.send({"role": "user", "content": (update.message_reaction.new_reaction)[0].emoji})


async def updates_generator(telegram_bot):
    """
    Generator for the Telegram updates.
    """
    latest_update_id = 0
    while True:
        try:
            # bot.get_updates keep sending the same update over and over.
            # offset can be used to specify what was the last update we processed, so to send only updates with an
            # update_id higher that that.
            update_tuple = await telegram_bot.get_updates(
                offset=latest_update_id, timeout=10, allowed_updates=Update.ALL_TYPES
            )
            # Occasionally we may receive empty updates (no idea why)
            if not update_tuple:
                continue

            # Get the update and store its update_id
            update = update_tuple[0]
            latest_update_id = update.update_id + 1

            # Give out the update
            yield update

        except NetworkError:
            log.exception("")
            await asyncio.sleep(1)
        except Forbidden:
            log.exception("The user has removed or blocked the bot.")
        except Exception:  # pylint: disable=broad-except
            log.exception("An exception occurred")
            await update.message.reply_text("An error occurred! Check the logs.")
