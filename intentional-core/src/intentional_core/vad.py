# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
VAD Client base class and utilities.
"""
from typing import Any, Dict, Type, Set
import logging
from intentional_core.utils import inheritors


logger = logging.getLogger(__name__)


_VAD_CLASSES: Dict[str, Type["VADClient"]] = {}


class VADClient:
    """
    Base class for Voice Activity Detection (VAD) clients.
    """

    name: str = None


def load_vad_from_dict(config: Dict[str, Any]) -> VADClient:
    """
    Load a VADClient from a configuration dictionary.

    Args:
        config:
            The configuration dictionary.

    Returns:
        The VADClient instance.
    """

    subclasses: Set[VADClient] = inheritors(VADClient)
    logger.debug("Known VAD client classes: %s", subclasses)
    for subclass in subclasses:
        if not subclass.name:
            logger.error(
                "VADClient class '%s' does not have a name. This VAD Client type will not be usable.", subclass
            )
            continue
        if subclass.name in _VAD_CLASSES:
            logger.warning(
                "Duplicate VAD client type '%s' found. The older class (%s) "
                "will be replaced by the newly imported one (%s).",
                subclass.name,
                _VAD_CLASSES[subclass.name],
                subclass,
            )
        _VAD_CLASSES[subclass.name] = subclass

    vad_type = config.pop("type")
    if vad_type not in _VAD_CLASSES:
        raise ValueError(
            f"Unknown VAD type: {vad_type}. Available types: {list(_VAD_CLASSES)}. "
            "Did you forget to install your plugin?"
        )

    return _VAD_CLASSES[vad_type](**config)
