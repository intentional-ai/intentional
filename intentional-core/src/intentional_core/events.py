# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Base class for very simplified event emitter and listener.
"""

import logging
from typing import Dict, Any
from abc import ABC, abstractmethod


logger = logging.getLogger("intentional")


class EventListener(ABC):
    """
    Listens to events and handles them.
    """

    @abstractmethod
    async def handle_event(self, event_name: str, event: Dict[str, Any]):
        """
        Handle the event.
        """


class EventEmitter:
    """
    Sends any event to the listener.
    TODO see if there's any scenario where we need more as this pattern is easy to extend but can get messy.
    """

    def __init__(self, listener: EventListener):
        """
        Register the listener.
        """
        self._events_listener = listener

    async def emit(self, event_name: str, event: Dict[str, Any]):
        """
        Send the event to the listener.
        """
        logger.debug("Emitting event %s", event_name)
        await self._events_listener.handle_event(event_name, event)
