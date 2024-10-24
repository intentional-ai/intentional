# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Utils for inheritance checks, to discover subclasses of a base Intentional class.
"""

from typing import Set, Any
import logging
import inspect


logger = logging.getLogger(__name__)


def inheritors(class_: Any, include_abstract: bool = False) -> Set[Any]:
    """
    Find all subclasses of a class, regardless of depth.

    Args:
        class_: The class to find subclasses of.
        include_abstract: Whether to include abstract classes in the results.
    """
    subclasses = set()
    to_process = [class_]
    while to_process:
        parent = to_process.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                to_process.append(child)
                print(child, inspect.isabstract(child))
                if not include_abstract and inspect.isabstract(child):
                    logger.debug(
                        "Skipping abstract class from inheritor's list: %s. Abstract methods: %s",
                        child,
                        child.__abstractmethods__,
                    )
                else:
                    subclasses.add(child)

    return subclasses
