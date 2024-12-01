# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Functions to load bot structure classes from config files.
"""

from typing import Dict, Any, Optional, Set, Callable, AsyncGenerator

from abc import abstractmethod

import structlog

from intentional_core.utils import inheritors
from intentional_core.intent_routing import IntentRouter
from intentional_core.events import EventListener
from intentional_core.llm_client import LLMClient, load_llm_client_from_dict


log = structlog.get_logger(logger_name=__name__)


_BOT_STRUCTURES = {}
""" This is a global dictionary that maps bot structure names to their classes """


class BotStructure(EventListener):
    """
    Tiny base class used to recognize Intentional bot structure classes.

    The bot structure's name is meant to represent the **structure** of the bot. For example a bot that simply sends the
    user's input to the LLM can be called DirectToLLMBotStructure, one that uses a VAD-STT-LLM-TTS stack could be called
    "AudioToTextBotStructure", and so on.

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
            log.debug(
                "Event handler for '%s' was already assigned. The older handler will be replaced by the new one.",
                event_name,
                event_name=event_name,
                event_handler=self.event_handlers[event_name],
            )
        log.debug("Adding event handler", event_name=event_name, event_handler=handler)
        self.event_handlers[event_name] = handler

    async def handle_event(self, event_name: str, event: Dict[str, Any]) -> None:
        """
        Handle different types of events that the LLM may generate.
        """
        if "*" in self.event_handlers:
            log.debug("Calling wildcard event handler", event_name=event_name)
            await self.event_handlers["*"](event)

        if event_name in self.event_handlers:
            log.debug("Calling event handler", event_name=event_name)
            await self.event_handlers[event_name](event)
        else:
            log.debug("No event handler for event", event_name=event_name)


class DirectToLLMBotStructure(BotStructure):
    """
    Bot structure that sends the user's input directly to the LLM and vice-versa.
    """

    name = "direct_to_llm"

    def __init__(self, config: Dict[str, Any], intent_router: IntentRouter):
        """
        Args:
            config:
                The configuration dictionary for the bot structure.
                It includes only the LLM definition under the `llm` key.
        """
        super().__init__()
        log.debug("Loading bot structure from config", bot_structure_config=config)

        # Init the model client
        llm_config = config.pop("llm", None)
        if not llm_config:
            raise ValueError(f"{self.__class__.__name__} requires a 'llm' configuration key.")
        self.llm: LLMClient = load_llm_client_from_dict(parent=self, intent_router=intent_router, config=llm_config)

    async def connect(self) -> None:
        """
        Initializes the model and connects to it as/if necessary.
        """
        await self.llm.connect()

    async def disconnect(self) -> None:
        """
        Disconnects from the model and unloads/closes it as/if necessary.
        """
        await self.llm.disconnect()

    async def run(self) -> None:
        """
        Main loop for the bot.
        """
        await self.llm.run()

    async def send(self, data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Sends a message to the model and forward the response.

        Args:
            data: The message to send to the model in OpenAI format, like {"role": "user", "content": "Hello!"}
        """
        await self.llm.send(data)

    async def handle_interruption(self, lenght_to_interruption: int) -> None:
        """
        Handle an interruption in the streaming.

        Args:
            lenght_to_interruption: The length of the data that was produced to the user before the interruption.
                This value could be number of characters, number of words, milliseconds, number of audio frames, etc.
                depending on the bot structure that implements it.
        """
        await self.llm.handle_interruption(lenght_to_interruption)


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
    log.debug("Collected bot structure classes", bot_structure_classes=subclasses)
    for subclass in subclasses:
        if not subclass.name:
            log.error(
                "BotStructure class '%s' does not have a name. This bot structure type will not be usable.",
                subclass,
                bot_structure_class=subclass,
            )
            continue

        if subclass.name in _BOT_STRUCTURES:
            log.warning(
                "Duplicate bot structure type '%s' found. The older class will be replaced by the newly imported one.",
                subclass.name,
                old_bot_structure_name=subclass.name,
                old_bot_structure_class=_BOT_STRUCTURES[subclass.name],
                new_bot_structure_class=subclass,
            )
        _BOT_STRUCTURES[subclass.name] = subclass

    # Identify the type of bot and see if it's known
    bot_structure_class = config.pop("type")
    log.debug("Creating bot structure", bot_structure_class=bot_structure_class)
    if bot_structure_class not in _BOT_STRUCTURES:
        raise ValueError(
            f"Unknown bot structure type '{bot_structure_class}'. Available types: {list(_BOT_STRUCTURES)}. "
            "Did you forget to install your plugin?"
        )

    # Handoff to the subclass' init
    return _BOT_STRUCTURES[bot_structure_class](config, intent_router)
