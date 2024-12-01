# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Base class for very simplified event emitter and listener.
"""

from typing import Dict, Any, Callable
from abc import ABC

import structlog


log = structlog.get_logger(logger_name=__name__)


class EventListener(ABC):
    """
    Listens to events and handles them.
    """

    def __init__(self):
        """
        Initialize the listener.
        """
        self.event_handlers: Dict[str, Callable] = {}

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
        log.debug("Emitting event", event_name=event_name)
        await self._events_listener.handle_event(event_name, event)
