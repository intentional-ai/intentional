# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Module import functions to handle dynamic plugins import.
"""

import logging
import inspect
import importlib


logger = logging.getLogger(__name__)


def import_plugin(name: str):
    """
    Imports the specified package. It does NOT check if this is an Intentional package or not.
    """
    try:
        logger.debug("Importing module %s", name)
        module = importlib.import_module(name)
        # Print all classes in the module
        for _, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                logger.debug("Class found: %s", obj)
    except ModuleNotFoundError:
        logger.exception("Module '%s' not found for import, is it installed?", name)


def import_all_plugins():
    """
    Imports all the `intentional-*` packages found in the current environment.
    """
    for dist in importlib.metadata.distributions():
        if not hasattr(dist, "_path"):
            logger.debug("'_path' not found in '%s', ignoring", dist)
        path = dist._path  # pylint: disable=protected-access
        if path.name.startswith("intentional_"):
            with open(path / "top_level.txt", encoding="utf-8") as file:
                for name in file.read().splitlines():
                    import_plugin(name)
