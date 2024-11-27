# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Bot structures supported by Intentional.
"""

from intentional_core.bot_structures.bot_structure import (
    BotStructure,
    ContinuousStreamBotStructure,
    TurnBasedBotStructure,
    load_bot_structure_from_dict,
)
from intentional_core.bot_structures.text_chat import TextChatBotStructure
from intentional_core.bot_structures.websocket import WebsocketBotStructure


__all__ = [
    "BotStructure",
    "load_bot_structure_from_dict",
    "ContinuousStreamBotStructure",
    "TurnBasedBotStructure",
    "TextChatBotStructure",
    "WebsocketBotStructure",
]
