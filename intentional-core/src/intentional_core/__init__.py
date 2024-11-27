# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Init file for `intentional_core`.
"""

from intentional_core.events import EventEmitter, EventListener

from intentional_core.bot_interface import BotInterface, load_bot_interface_from_dict, load_configuration_file

from intentional_core.bot_structures.bot_structure import (
    BotStructure,
    ContinuousStreamBotStructure,
    TurnBasedBotStructure,
    load_bot_structure_from_dict,
)
from intentional_core.bot_structures.text_chat import TextChatBotStructure
from intentional_core.bot_structures.websocket import WebsocketBotStructure

from intentional_core.model_client import (
    ModelClient,
    ContinuousStreamModelClient,
    TurnBasedModelClient,
    load_model_client_from_dict,
)

from intentional_core.tools import Tool, load_tools_from_dict
from intentional_core.intent_routing import IntentRouter

__all__ = [
    "EventEmitter",
    "EventListener",
    "BotInterface",
    "load_bot_interface_from_dict",
    "load_configuration_file",
    "BotStructure",
    "ContinuousStreamBotStructure",
    "TurnBasedBotStructure",
    "load_bot_structure_from_dict",
    "TextChatBotStructure",
    "WebsocketBotStructure",
    "ModelClient",
    "ContinuousStreamModelClient",
    "TurnBasedModelClient",
    "load_model_client_from_dict",
    "Tool",
    "IntentRouter",
    "load_tools_from_dict",
]
