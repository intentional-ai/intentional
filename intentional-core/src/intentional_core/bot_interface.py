# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Functions to load bots from config files.
"""

from typing import Dict, Any, Optional, Set

import json
from pathlib import Path
from abc import ABC, abstractmethod

import yaml
import structlog

from intentional_core.utils import import_plugin, inheritors
from intentional_core.intent_routing import IntentRouter


log = structlog.get_logger(logger_name=__name__)


_BOT_INTERFACES = {}
""" This is a global dictionary that maps bot interface names to their classes """


class BotInterface(ABC):
    """
    Tiny base class used to recognize Intentional bots interfaces.

    The class name is meant to represent the **communication channel** you will use to interact with your bot.
    For example an interface that uses a local command line interface would be called "TerminalBotInterface", one that
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
    log.debug("Loading YAML configuration file", config_file_path=path)
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
    log.debug("Loading bot interface from configuration:", bot_interface_config=json.dumps(config, indent=4))

    # Import all the necessary plugins
    plugins = config.pop("plugins")
    log.debug("Found plugins to import", plugins=plugins)
    for plugin in plugins:
        log.debug("Importing plugin", plugin=plugin)
        import_plugin(plugin)

    # Initialize the intent router
    log.debug("Creating intent router")
    intent_router = IntentRouter(config.pop("conversation", {}))

    # Get all the subclasses of Bot
    subclasses: Set[BotInterface] = inheritors(BotInterface)
    log.debug("Collected bot interface classes", bot_interfaces=subclasses)

    for subclass in subclasses:
        if not subclass.name:
            log.error(
                "Bot interface class '%s' does not have a name. This bot type will not be usable.",
                subclass,
                bot_interface_class=subclass,
            )
            continue

        if subclass.name in _BOT_INTERFACES:
            log.warning(
                "Duplicate bot interface type '%s' found. The older class will be replaced by the newly imported one.",
                subclass.name,
                old_bot_interface_name=subclass.name,
                old_bot_interface_class=_BOT_INTERFACES[subclass.name],
                new_bot_interface_class=subclass,
            )
        _BOT_INTERFACES[subclass.name] = subclass

    # Identify the type of bot interface and see if it's known
    interface_class = config.pop("interface", None)
    if not interface_class:
        raise ValueError("Bot configuration must contain an 'interface' key to know which interface to use.")

    if interface_class not in _BOT_INTERFACES:
        raise ValueError(
            f"Unknown bot interface type '{interface_class}'. Available types: {list(_BOT_INTERFACES)}. "
            "Did you forget to add the correct plugin name in the configuration file, or to install it?"
        )

    # Handoff to the subclass' init
    log.debug("Creating bot interface", bot_interface_class=interface_class)
    return _BOT_INTERFACES[interface_class](intent_router=intent_router, config=config)
