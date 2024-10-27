# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
STT Client base class and utilities.
"""
from typing import Any, Dict, Type, Set
import logging
from intentional_core.utils import inheritors


logger = logging.getLogger(__name__)


_STT_CLASSES: Dict[str, Type["STTClient"]] = {}


class STTClient:
    """
    Base class for Speech-To-Text (STT) clients.
    """

    name: str = None


def load_stt_from_dict(config: Dict[str, Any]) -> STTClient:
    """
    Load a STTClient from a configuration dictionary.

    Args:
        config:
            The configuration dictionary.

    Returns:
        The STTClient instance.
    """

    subclasses: Set[STTClient] = inheritors(STTClient)
    logger.debug("Known STT client classes: %s", subclasses)
    for subclass in subclasses:
        if not subclass.name:
            logger.error(
                "STTClient class '%s' does not have a name. This STT Client type will not be usable.", subclass
            )
            continue
        if subclass.name in _STT_CLASSES:
            logger.warning(
                "Duplicate STT client type '%s' found. The older class (%s) "
                "will be replaced by the newly imported one (%s).",
                subclass.name,
                _STT_CLASSES[subclass.name],
                subclass,
            )
        _STT_CLASSES[subclass.name] = subclass

    stt_type = config.pop("type")
    if stt_type not in _STT_CLASSES:
        raise ValueError(
            f"Unknown STT type: {stt_type}. Available types: {list(_STT_CLASSES)}. "
            "Did you forget to install your plugin?"
        )

    return _STT_CLASSES[stt_type](**config)
