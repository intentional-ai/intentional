# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tools baseclass for Intentional.
"""
from typing import List, Any, Dict, Set
from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
from intentional_core.utils import inheritors


logger = logging.getLogger(__name__)


_TOOL_CLASSES = {}
""" This is a global dictionary that maps tool names to their classes """


@dataclass
class ToolParameter:
    """
    A parameter for an Intentional tool.
    """

    name: str
    description: str
    type: Any
    required: bool
    default: Any


class Tool(ABC):
    """
    Tools baseclass for Intentional.
    """

    name: str = None
    description: str = None
    parameters: List[ToolParameter] = None

    @abstractmethod
    async def run(self, params: dict) -> Any:
        """
        Run the tool.
        """


def load_tools_from_dict(config: List[Dict[str, Any]]) -> Dict[str, Tool]:
    """
    Load a list of tools from a dictionary configuration.

    Args:
        config: The configuration dictionary.

    Returns:
        A list of Tool instances.
    """
    # Get all the subclasses of Tool
    if not _TOOL_CLASSES:
        subclasses: Set[Tool] = inheritors(Tool)
        logger.debug("Known tool classes: %s", subclasses)
        for subclass in subclasses:
            if not subclass.name:
                logger.error("Tool class '%s' does not have a name. This tool will not be usable.", subclass)
                continue

            if subclass.name in _TOOL_CLASSES:
                logger.warning(
                    "Duplicate tool '%s' found. The older class (%s) will be replaced by the newly imported one (%s).",
                    subclass.name,
                    _TOOL_CLASSES[subclass.name],
                    subclass,
                )
            _TOOL_CLASSES[subclass.name] = subclass

    # Initialize the tools
    tools = {}
    for tool_config in config:
        class_ = tool_config.pop("name")
        logger.debug("Creating tool of type '%s'", class_)
        if class_ not in _TOOL_CLASSES:
            raise ValueError(
                f"Unknown tool '{class_}'. Available tools: {list(_TOOL_CLASSES)}. "
                "Did you forget to install a plugin?"
            )
        tool_instance = _TOOL_CLASSES[class_](**tool_config)
        tools[tool_instance.name] = tool_instance

    return tools
