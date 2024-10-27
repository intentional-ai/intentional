# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
TTS Client base class and utilities.
"""
from typing import Any, Dict, Type, Set
import logging
from intentional_core.utils import inheritors


logger = logging.getLogger(__name__)


_TTS_CLASSES: Dict[str, Type["TTSClient"]] = {}


class TTSClient:
    """
    Base class for Text-To-Speech (TTS) clients.
    """

    name: str = None


def load_tts_from_dict(config: Dict[str, Any]) -> TTSClient:
    """
    Load a TTSClient from a configuration dictionary.

    Args:
        config:
            The configuration dictionary.

    Returns:
        The TTSClient instance.
    """

    subclasses: Set[TTSClient] = inheritors(TTSClient)
    logger.debug("Known TTS client classes: %s", subclasses)
    for subclass in subclasses:
        if not subclass.name:
            logger.error(
                "TTSClient class '%s' does not have a name. This TTS Client type will not be usable.", subclass
            )
            continue
        if subclass.name in _TTS_CLASSES:
            logger.warning(
                "Duplicate TTS client type '%s' found. The older class (%s) "
                "will be replaced by the newly imported one (%s).",
                subclass.name,
                _TTS_CLASSES[subclass.name],
                subclass,
            )
        _TTS_CLASSES[subclass.name] = subclass

    tts_type = config.pop("type")
    if tts_type not in _TTS_CLASSES:
        raise ValueError(
            f"Unknown TTS type: {tts_type}. Available types: {list(_TTS_CLASSES)}. "
            "Did you forget to install your plugin?"
        )

    return _TTS_CLASSES[tts_type](**config)
