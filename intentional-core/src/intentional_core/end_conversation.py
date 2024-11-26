# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Tool that ends and resets the conversation.
Once a conversation reaches this stage, the bot should restart from the _start_ stage. See IntentRouter.
"""

from typing import TYPE_CHECKING
import structlog
from intentional_core.tools import Tool

if TYPE_CHECKING:
    from intentional_core.intent_routing import IntentRouter

log = structlog.get_logger(logger_name=__name__)


class EndConversationTool(Tool):
    """
    Tool to end the conversation. Resets the intent router to its initial stage.
    """

    name = "end_conversation"
    description = "End the conversation."
    parameters = []

    def __init__(self, intent_router: "IntentRouter"):
        self.router = intent_router

    async def run(self, params=None) -> str:
        """
        Ends the conversation and resets the intent router to its initial stage.
        """
        log.debug("The conversation has ended.")
        self.router.current_stage_name = self.router.initial_stage
        log.debug("Intent router reset to initial stage.", initial_stage=self.router.initial_stage)
