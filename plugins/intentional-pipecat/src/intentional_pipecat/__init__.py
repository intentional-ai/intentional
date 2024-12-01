# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Intentional plugin for Pipecat
"""
import sys

import structlog
from intentional_pipecat.bot_structure import PipecatBotStructure

# Use structlog for logging instead of loguru (the default in Pipecat)
structlog.logger = structlog.get_logger(logger_name="pipecat")
structlog.logger.trace = structlog.logger.debug
sys.modules["loguru"] = structlog


__all__ = ["PipecatBotStructure"]
