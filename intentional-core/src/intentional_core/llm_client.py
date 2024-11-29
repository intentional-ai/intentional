# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Functions to load LLM client classes from config files.
"""
from typing import Optional, Dict, Any, Set, TYPE_CHECKING

from abc import ABC, abstractmethod

import structlog

from intentional_core.utils import inheritors
from intentional_core.events import EventEmitter
from intentional_core.intent_routing import IntentRouter

if TYPE_CHECKING:
    from intentional_core.bot_structures.bot_structure import BotStructure


log = structlog.get_logger(logger_name=__name__)


_LLM_CLIENTS = {}
""" This is a global dictionary that maps LLM client names to their classes """

KNOWN_LLM_EVENTS = [
    "*",
    "on_error",
    "on_llm_connection",
    "on_llm_disconnection",
    "on_system_prompt_updated",
    "on_llm_starts_generating_response",
    "on_llm_stops_generating_response",
    "on_text_message_from_llm",
    "on_audio_message_from_llm",
    "on_user_speech_started",
    "on_user_speech_ended",
    "on_user_speech_transcribed",
    "on_llm_speech_transcribed",
    "on_tool_invoked",
    "on_conversation_ended",
]


class LLMClient(ABC, EventEmitter):
    """
    Tiny base class used to recognize Intentional LLM clients.

    In order for your client to be usable, you need to assign a value to the `name` class variable
    in the client class' definition.
    """

    name: Optional[str] = None
    """
    The name of the client. This should be a unique identifier for the client type.
    This string will be used in configuration files to identify the type of client to serve a LLM from.
    """

    def __init__(self, parent: "BotStructure", intent_router: IntentRouter) -> None:
        """
        Initialize the LLM client.

        Args:
            parent: The parent bot structure.
        """
        super().__init__(parent)
        self.intent_router = intent_router

    async def connect(self) -> None:
        """
        Connect to the LLM.
        """
        await self.emit("on_llm_connection", {})

    async def disconnect(self) -> None:
        """
        Disconnect from the LLM.
        """
        await self.emit("on_llm_disconnection", {})

    @abstractmethod
    async def run(self) -> None:
        """
        Handle events from the LLM by either processing them internally or by translating them into higher-level
        events that the BotStructure class can understand, then re-emitting them.
        """

    @abstractmethod
    async def send(self, data: Dict[str, Any]) -> None:
        """
        Send a unit of data to the LLM. The response is streamed out as an async generator.
        """

    @abstractmethod
    async def handle_interruption(self, lenght_to_interruption: int) -> None:
        """
        Handle an interruption while rendering the output to the user.

        Args:
            lenght_to_interruption: The length of the data that was produced to the user before the interruption.
                This value could be number of characters, number of words, milliseconds, number of audio frames, etc.
                depending on the bot structure that implements it.
        """


def load_llm_client_from_dict(parent: "BotStructure", intent_router: IntentRouter, config: Dict[str, Any]) -> LLMClient:
    """
    Load a LLM client from a dictionary configuration.

    Args:
        config: The configuration dictionary.

    Returns:
        The LLMClient instance.
    """
    # Get all the subclasses of LLMClient
    subclasses: Set[LLMClient] = inheritors(LLMClient)
    log.debug("Collected LLM client classes", llm_client_classes=subclasses)
    for subclass in subclasses:
        if not subclass.name:
            log.error(
                "LLM client class '%s' does not have a name. This LLM client type will not be usable.",
                subclass,
                llm_client_class=subclass,
            )
            continue

        if subclass.name in _LLM_CLIENTS:
            log.warning(
                "Duplicate LLM client type '%s' found. The older class will be replaced by the newly imported one.",
                subclass.name,
                old_llm_client_name=subclass.name,
                old_llm_client_class=_LLM_CLIENTS[subclass.name],
                new_llm_client_class=subclass,
            )
        _LLM_CLIENTS[subclass.name] = subclass

    # Identify the type of bot and see if it's known
    llm_client_class = config.pop("client")
    log.debug("Creating LLM client", llm_client_class=llm_client_class)
    if llm_client_class not in _LLM_CLIENTS:
        raise ValueError(
            f"Unknown LLM client type '{llm_client_class}'. Available types: {list(_LLM_CLIENTS)}. "
            "Did you forget to install your plugin?"
        )

    # Handoff to the subclass' init
    return _LLM_CLIENTS[llm_client_class](parent=parent, intent_router=intent_router, config=config)
