# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Module import functions to handle dynamic plugins import.
"""

import inspect
import importlib
import structlog


log = structlog.get_logger(logger_name=__name__)


def import_plugin(name: str):
    """
    Imports the specified package. It does NOT check if this is an Intentional package or not.
    """
    try:
        log.debug("Importing module", module_name=name)
        module = importlib.import_module(name)
        # Print all classes in the module
        class_found = False
        for _, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                log.debug("Class found in module", module_name=name, found_class=obj)
                class_found = True
        if not class_found:
            log.debug(
                "No classes found in module: are they imported in the top-level __init__ file of the plugin?",
                module_name=name,
            )
    except ModuleNotFoundError:
        log.exception("Module '%s' not found for import, is it installed?", name, module_name=name)


def import_all_plugins():
    """
    Imports all the `intentional-*` packages found in the current environment.
    """
    for dist in importlib.metadata.distributions():
        if not hasattr(dist, "_path"):
            log.debug("'_path' not found in '%s', ignoring", dist, dist=dist)
        path = dist._path  # pylint: disable=protected-access
        if path.name.startswith("intentional_"):
            with open(path / "top_level.txt", encoding="utf-8") as file:
                for name in file.read().splitlines():
                    import_plugin(name)
