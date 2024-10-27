# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Functions to load model client classes from config files.
"""
from typing import Optional, Dict, Any, Set, AsyncGenerator

import logging
from abc import ABC, abstractmethod

from intentional_core.utils import inheritors


logger = logging.getLogger(__name__)


_MODELCLIENT_CLASSES = {}
""" This is a global dictionary that maps model client names to their classes """


class ModelClient(ABC):
    """
    Tiny base class used to recognize Intentional model clients.

    In order for your client to be usable, you need to assign a value to the `_name` class variable
    in the client class' definition.
    """

    name: Optional[str] = None
    """
    The name of the client. This should be a unique identifier for the client type.
    This string will be used in configuration files to identify the type of client to serve a model from.
    """


class TurnBasedModelClient(ModelClient):
    """
    Base class for model clients that support turn-based message exchanges, as opposed to continuous streaming of data.
    """

    @abstractmethod
    async def send_message(self, message: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Send a message to the model.
        """


class ContinuousStreamModelClient(ModelClient):
    """
    Base class for model clients that support continuous streaming of data, as opposed to turn-based message exchanges.
    """

    def __init__(self):
        super().__init__()
        self.parent_event_handler = None

    @abstractmethod
    async def connect(self) -> None:
        """
        Connect to the model.
        """

    @abstractmethod
    async def stream_data(self, data: bytes) -> None:
        """
        Stream data to the model.
        """

    @abstractmethod
    async def run(self) -> None:
        """
        Handle events from the model.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Disconnect from the model.
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


def load_model_client_from_dict(config: Dict[str, Any]) -> ModelClient:
    """
    Load a model client from a dictionary configuration.

    Args:
        config: The configuration dictionary.

    Returns:
        The ModelClient instance.
    """
    # Get all the subclasses of ModelClient
    subclasses: Set[ModelClient] = inheritors(ModelClient)
    logger.debug("Known model client classes: %s", subclasses)
    for subclass in subclasses:
        if not subclass.name:
            logger.error(
                "Model client class '%s' does not have a name. This model client type will not be usable.", subclass
            )
            continue

        if subclass.name in _MODELCLIENT_CLASSES:
            logger.warning(
                "Duplicate model client type '%s' found. The older class (%s) "
                "will be replaced by the newly imported one (%s).",
                subclass.name,
                _MODELCLIENT_CLASSES[subclass.name],
                subclass,
            )
        _MODELCLIENT_CLASSES[subclass.name] = subclass

    # Identify the type of bot and see if it's known
    class_ = config.pop("client")
    logger.debug("Creating model client of type '%s'", class_)
    if class_ not in _MODELCLIENT_CLASSES:
        raise ValueError(
            f"Unknown model client type '{class_}'. Available types: {list(_MODELCLIENT_CLASSES)}. "
            "Did you forget to install your plugin?"
        )

    # Handoff to the subclass' init
    return _MODELCLIENT_CLASSES[class_](config)
