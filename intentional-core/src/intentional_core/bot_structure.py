# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Functions to load bot structure classes from config files.
"""

from typing import Dict, Any, Optional

import logging
from abc import abstractmethod


logger = logging.getLogger(__name__)


_BOT_STRUCTURES = {}
""" This is a global dictionary that maps bot structure names to their classes """


class BotStructure:
    """
    Tiny base class used to recognize Intentional bot structure classes.

    The bot structure's name is meant to represent the **structure** of the bot. For example a bot that uses a direct
    WebSocket connection to a model such as OpenAI's Realtime API could be called "RealtimeAPIBotStructure", one that
    uses a VAD-STT-LLM-TTS stack could be called "AudioToTextBotStructure", and so on

    In order for your bot structure to be usable, you need to assign a value to the `name` class variable in the bot
    structure class' definition.
    """

    name: Optional[str] = None
    """
    The name of this bot's structure. This should be a unique identifier for the bot structure type.

    The bot structure's name should directly recall the class name as much as possible. For example, the name of
    "RealtimeAPIBotStructure" should be "realtime_api", the name of "AudioToTextBotStructure" should be "audio_to_text",
    etc.
    """

    @property
    @abstractmethod
    def event_handlers(self):
        """
        Return a dictionary of event handlers for this bot structure.
        """

    @abstractmethod
    async def run(self) -> None:
        """
        Main loop for the bot.
        """

    @abstractmethod
    async def handle_event(self, event: Dict[str, Any]) -> None:
        """
        Handle different types of events that the bot or the user may generate.
        """


class ContinuousStreamBotStructure:
    """
    Base class for structures that support continuous streaming of data, as opposed to turn-based message exchanges.
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        Connect to the bot.
        """

    @abstractmethod
    async def stream_data(self, data: bytes) -> None:
        """
        Stream data to the bot.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Disconnect from the bot.
        """


class TurnBasedBotStructure:
    """
    Base class for structures that support turn-based message exchanges, as opposed to continuous streaming of data.
    """

    @abstractmethod
    async def send_message(self, message: Dict[str, Any]) -> None:
        """
        Send a message to the bot.
        """


def load_bot_structure_from_dict(config: Dict[str, Any]) -> BotStructure:
    """
    Load a bot structure from a dictionary configuration.

    Args:
        config: The configuration dictionary.

    Returns:
        The BotStructure instance.
    """
    # List all the subclasses of BotStructure for debugging purposes
    logger.debug("Known bot structure classes: %s", BotStructure.__subclasses__())

    # Get all the subclasses of Bot
    for subclass in BotStructure.__subclasses__():
        if not subclass.name:
            logger.error(
                "BotStructure class '%s' does not have a name. This bot structure type will not be usable.", subclass
            )
            continue

        if subclass.name in _BOT_STRUCTURES:
            logger.warning(
                "Duplicate bot structure type '%s' found. The older class (%s) "
                "will be replaced by the newly imported one (%s).",
                subclass.name,
                _BOT_STRUCTURES[subclass.name],
                subclass,
            )
        _BOT_STRUCTURES[subclass.name] = subclass

    # Identify the type of bot and see if it's known
    class_ = config.pop("type")
    logger.debug("Creating bot of type '%s'", class_)
    if class_ not in _BOT_STRUCTURES:
        raise ValueError(
            f"Unknown bot structure type '{class_}'. Available types: {list(_BOT_STRUCTURES)}. "
            "Did you forget to install your plugin?"
        )

    # Handoff to the subclass' init
    return _BOT_STRUCTURES[class_](config)
