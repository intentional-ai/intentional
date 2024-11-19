# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Entry point for the Intentional CLI.
"""
import json
import asyncio
import logging
import logging.config
import argparse

import yaml
import structlog
from intentional_core import load_configuration_file, IntentRouter
from intentional_core.utils import import_plugin

from intentional.draw import to_image


log = structlog.get_logger(logger_name=__name__)


def main():
    """
    Entry point for the Intentional CLI.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="the path to the configuration file to load.", type=str)
    parser.add_argument("--draw", help="Draw the graph.", action="store_true")
    parser.add_argument("--log-cli-level", help="Select the logging level to the console.", type=str, default="INFO")
    parser.add_argument("--log-file", help="Path to the log file.", type=str)
    parser.add_argument(
        "--log-file-level",
        help="Select the logging level to the file. Ignore if no path is specified with --log-file",
        type=str,
        default="DEBUG",
    )
    args = parser.parse_args()

    # Set the CLI log level
    cli_level = logging.getLevelName(args.log_cli_level.upper())
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(cli_level))

    if args.log_file:
        # https://www.structlog.org/en/stable/standard-library.html
        file_level = logging.getLevelName(args.log_file_level.upper())
        timestamper = structlog.processors.TimeStamper(fmt="iso")
        pre_chain = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.ExtraAdder(),
            timestamper,
        ]
        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "handlers": {
                    "default": {
                        "level": cli_level,
                        "class": "logging.StreamHandler",
                        "formatter": "colored",
                    },
                    "file": {
                        "level": file_level,
                        "class": "logging.handlers.WatchedFileHandler",
                        "filename": args.log_file,
                        "formatter": "json",
                    },
                },
                "formatters": {
                    "json": {
                        "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                        "fmt": "%(asctime)s %(levelname)s %(message)s",
                    },
                    "colored": {
                        "()": structlog.stdlib.ProcessorFormatter,
                        "processors": [
                            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                            structlog.dev.ConsoleRenderer(colors=True),
                        ],
                        "foreign_pre_chain": pre_chain,
                    },
                },
                "loggers": {
                    "": {
                        "handlers": ["default", "file"],
                        "level": "DEBUG",
                        "propagate": True,
                    },
                },
            }
        )
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                timestamper,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    if args.draw:
        asyncio.run(draw_intent_graph_from_config(args.path))
        return

    bot = load_configuration_file(args.path)
    asyncio.run(bot.run())


async def draw_intent_graph_from_config(path: str) -> IntentRouter:
    """
    Load the intent router from the configuration file.
    """
    log.debug("Loading YAML configuration file", config_file_path=path)

    with open(path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    log.debug("Loading bot interface", bot_interface_config=json.dumps(config, indent=4))

    plugins = config.pop("plugins")
    log.debug("Collected_plugins", plugins=plugins)
    for plugin in plugins:
        import_plugin(plugin)

    intent_router = IntentRouter(config.pop("conversation", {}))
    return await to_image(intent_router, path + ".png")
