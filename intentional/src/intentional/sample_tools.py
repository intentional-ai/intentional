# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Sample tools for Intentional's examples.
"""

from datetime import datetime
import structlog
from intentional_core.tools import Tool, ToolParameter


log = structlog.get_logger(logger_name=__name__)


class EndConversationTool(Tool):
    """
    Tool to end the conversation. This tool must be handled by each model client. TODO
    """

    name = "end_conversation"
    description = "End the conversation."
    parameters = []

    async def run(self, _) -> str:
        """
        Ends the conversation.
        """
        log.debug("Ending the conversation.")
        return "The conversation has ended."


class GetCurrentDateTimeTool(Tool):
    """
    Simple tool to get the current date and time.
    """

    name = "get_current_date_and_time"
    description = "Get the current date and time in the format 'YYYY-MM-DD HH:MM:SS'."
    parameters = []

    async def run(self, _) -> str:
        """
        Returns the current time.
        """
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.debug("Getting the current date and time.", current_date_time=current_datetime)
        return current_datetime


class RescheduleInterviewTool(Tool):
    """
    Mock tool to reschedule an interview.
    """

    name = "reschedule_interview"
    description = "Set a new date and time for the interview in the database."
    parameters = [
        ToolParameter(
            "date",
            "The new date for the interview.",
            "string",
            True,
            None,
        ),
        ToolParameter(
            "time",
            "The new time for the interview.",
            "string",
            True,
            None,
        ),
    ]

    async def run(self, _) -> str:
        """
        Returns the current time.
        """
        log.debug("Rescheduling the interview.")
        return "The interview was rescheduled successfully."
