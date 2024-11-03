# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Functions to load bot structure classes from config files.
"""

from typing import Dict, Any, Optional, Set, Callable

import logging
from abc import abstractmethod

from intentional_core.utils import inheritors
from intentional_core.intent_routing import IntentRouter
from intentional_core.events import EventListener


logger = logging.getLogger(__name__)


_BOT_STRUCTURES = {}
""" This is a global dictionary that maps bot structure names to their classes """


class BotStructure(EventListener):
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
    "WebsocketBotStructure" should be "websocket", the name of "AudioToTextBotStructure" should be "audio_to_text",
    etc.
    """

    def __init__(self) -> None:
        """
        Initialize the bot structure.
        """
        self.event_handlers: Dict[str, Callable] = {}

    async def connect(self) -> None:
        """
        Connect to the bot.
        """

    async def disconnect(self) -> None:
        """
        Disconnect from the bot.
        """

    @abstractmethod
    async def run(self) -> None:
        """
        Main loop for the bot.
        """

    @abstractmethod
    async def send(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to the bot.
        """

    @abstractmethod
    async def handle_interruption(self, lenght_to_interruption: int) -> None:
        """
        Handle an interruption in the streaming.

        Args:
            lenght_to_interruption: The length of the data that was produced to the user before the interruption.
                This value could be number of characters, number of words, milliseconds, number of audio frames, etc.
                depending on the bot structure that implements it.
        """

    def add_event_handler(self, event_name: str, handler: Callable) -> None:
        """
        Add an event handler for a specific event type.

        Args:
            event_name: The name of the event to handle.
            handler: The handler function to call when the event is received.
        """
        if event_name in self.event_handlers:
            logger.warning(
                "Event handler for '%s' already exists. The older handler will be replaced by the new one.",
                event_name,
            )

        logger.debug("Adding event handler for event '%s'", event_name)
        self.event_handlers[event_name] = handler

    async def handle_event(self, event_name: str, event: Dict[str, Any]) -> None:
        """
        Handle different types of events that the model may generate.
        """
        logger.debug("Received event '%s'", event_name)

        if "*" in self.event_handlers:
            logger.debug("Calling wildcard event handler for event '%s'", event_name)
            await self.event_handlers["*"](event)

        if event_name in self.event_handlers:
            logger.debug("Calling event handler for event '%s'", event_name)
            await self.event_handlers[event_name](event)


class ContinuousStreamBotStructure(BotStructure):
    """
    Base class for structures that support continuous streaming of data, as opposed to turn-based message exchanges.
    """


class TurnBasedBotStructure(BotStructure):
    """
    Base class for structures that support turn-based message exchanges, as opposed to continuous streaming of data.
    """


def load_bot_structure_from_dict(intent_router: IntentRouter, config: Dict[str, Any]) -> BotStructure:
    """
    Load a bot structure from a dictionary configuration.

    Args:
        config: The configuration dictionary.

    Returns:
        The BotStructure instance.
    """
    # Get all the subclasses of Bot
    subclasses: Set[BotStructure] = inheritors(BotStructure)
    logger.debug("Known bot structure classes: %s", subclasses)
    for subclass in subclasses:
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
    return _BOT_STRUCTURES[class_](config, intent_router)
