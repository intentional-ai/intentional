# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Entry point for the Intentional CLI.
"""

import asyncio
import logging
import argparse

from intentional_core import load_configuration_file

logging.basicConfig(filename="logs.log", filemode="w", level=logging.DEBUG)


def main():
    """
    Entry point for the Intentional CLI.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="the path to the configuration file to load.", type=str)
    parser.add_argument("--log-level", help="Select the logging level.", type=str)
    args = parser.parse_args()

    if args.log_level:
        level = logging.getLevelName(args.log_level.upper())
        logging.basicConfig(level=level)

    bot = load_configuration_file(args.path)
    asyncio.run(bot.run())
