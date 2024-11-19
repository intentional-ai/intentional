# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Entry point for the Intentional CLI.
"""
import json
import asyncio
import logging
import argparse

import yaml
from intentional_core import load_configuration_file, IntentRouter
from intentional_core.utils import import_plugin

from intentional.draw import to_image


logger = logging.getLogger("intentional")


def main():
    """
    Entry point for the Intentional CLI.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="the path to the configuration file to load.", type=str)
    parser.add_argument("--draw", help="Draw the graph.", action="store_true")
    parser.add_argument("--log-level", help="Select the logging level.", type=str)
    args = parser.parse_args()

    if args.log_level:
        level = logging.getLevelName(args.log_level.upper())
        logging.basicConfig(level=level)

    if args.draw:
        asyncio.run(draw_intent_graph_from_config(args.path))
        return

    bot = load_configuration_file(args.path)
    asyncio.run(bot.run())


async def draw_intent_graph_from_config(path: str) -> IntentRouter:
    """
    Load the intent router from the configuration file.
    """
    logger.debug("Loading YAML configuration file from '%s'", path)

    with open(path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    logger.debug("Loading bot interface from configuration:\n%s", json.dumps(config, indent=4))

    plugins = config.pop("plugins")
    logger.debug("Plugins to import: %s", plugins)
    for plugin in plugins:
        import_plugin(plugin)

    intent_router = IntentRouter(config.pop("conversation", {}))
    return await to_image(intent_router, path + ".png")
