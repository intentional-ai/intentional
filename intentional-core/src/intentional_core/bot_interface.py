# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Functions to load bots from config files.
"""

from typing import Dict, Any, Optional, Set

import json
import logging
from pathlib import Path
from abc import ABC, abstractmethod

import yaml

from intentional_core.utils import import_plugin, inheritors


logger = logging.getLogger(__name__)


_BOT_INTERFACES = {}
""" This is a global dictionary that maps bot interface names to their classes """


class BotInterface(ABC):
    """
    Tiny base class used to recognize Intentional bots interfaces.

    The class name is meant to represent the **communication channel** you will use to interact with your bot.
    For example an interface that uses a local command line interface would be called "LocalBotInterface", one that
    uses Whatsapp would be called "WhatsappBotInterface", one that uses Twilio would be called "TwilioBotInterface",
    etc.

    In order for your bot to be usable, you need to assign a value to the `name` class variable in the class definition.
    """

    name: Optional[str] = None
    """
    The name of the bot interface. This should be a unique identifier for the bot interface.
    This string will be used in configuration files to identify the bot interface.

    The bot interface name should directly recall the class name as much as possible.
    For example, the name of "LocalBotInterface" should be "local", the name of "WhatsappBotInterface" should be
    "whatsapp", etc.
    """

    @abstractmethod
    async def run(self):
        """
        Run the bot interface.

        This method should be overridden by the subclass to implement the bot's main loop.
        """
        raise NotImplementedError("BotInterface subclasses must implement the run method.")


def load_configuration_file(path: Path) -> BotInterface:
    """
    Load an Intentional bot from a YAML configuration file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        The bot instance.
    """
    logger.debug("Loading YAML configuration file from '%s'", path)
    with open(path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return load_bot_interface_from_dict(config)


def load_bot_interface_from_dict(config: Dict[str, Any]) -> BotInterface:
    """
    Load a bot interface, and all its inner classes, from a dictionary configuration.

    Args:
        config: The configuration dictionary.

    Returns:
        The bot interface instance.
    """
    logger.debug("Loading bot interface from configuration:\n%s", json.dumps(config, indent=4))

    # Import all the necessary plugins
    plugins = config.pop("plugins")
    logger.debug("Plugins to import: %s", plugins)
    for plugin in plugins:
        import_plugin(plugin)

    # Get all the subclasses of Bot
    subclasses: Set[BotInterface] = inheritors(BotInterface)
    logger.debug("Known bot interface classes: %s", subclasses)

    for subclass in subclasses:
        if not subclass.name:
            logger.error("Bot interface class '%s' does not have a name. This bot type will not be usable.", subclass)
            continue

        if subclass.name in _BOT_INTERFACES:
            logger.warning(
                "Duplicate bot interface type '%s' found. The older class (%s) "
                "will be replaced by the newly imported one (%s).",
                subclass.name,
                _BOT_INTERFACES[subclass.name],
                subclass,
            )
        _BOT_INTERFACES[subclass.name] = subclass

    # Identify the type of bot interface and see if it's known
    interface_config = config.pop("interface")
    interface_class_ = interface_config.pop("name", None)
    if not interface_class_:
        raise ValueError("Bot interface configuration requires a 'name' key to know which interface to use.")

    logger.debug("Creating bot interface of type '%s'", interface_class_)
    if interface_class_ not in _BOT_INTERFACES:
        raise ValueError(
            f"Unknown bot interface type '{interface_class_}'. Available types: {list(_BOT_INTERFACES)}. "
            "Did you forget to add the correct plugin name in the configuration file, or to install it?"
        )

    # Handoff to the subclass' init
    return _BOT_INTERFACES[interface_class_](config)
