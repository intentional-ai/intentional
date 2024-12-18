# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Sample tools for Intentional's examples.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from intentional_core.tools import Tool, ToolParameter


log = structlog.get_logger(logger_name=__name__)


class MockTool(Tool):
    """
    Simple tool that returns a fixed response to a fixed parameter value.

    Accepts a single parameter, "request", which is a string.
    """

    id = "mock_tool"

    def __init__(
        self, name, description, input_description, responses_dictionary=None, default_response=None
    ):  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self.name = name
        self.description = description
        self.parameters = [ToolParameter("request", input_description, "string", True, None)]
        self.responses_dictionary = responses_dictionary or {}
        self.default_response = default_response

    async def run(self, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Returns a fixed response to a fixed parameter value.
        """
        response = self.responses_dictionary.get(params["request"], self.default_response)
        if response:
            log.debug("ExampleTool found a match", request=params["request"], response=response)
        else:
            log.debug("ExampleTool did not find a match", request=params["request"])
        return response


class GetCurrentDateTimeTool(Tool):
    """
    Simple tool to get the current date and time.
    """

    id = "get_current_date_and_time"
    name = "get_current_date_and_time"
    description = "Get the current date and time in the format 'YYYY-MM-DD HH:MM:SS'."
    parameters = []

    async def run(self, params: Optional[Dict[str, Any]] = None) -> str:
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

    id = "reschedule_interview"
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

    async def run(self, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Returns the current time.
        """
        log.debug("Rescheduling the interview.")
        return "The interview was rescheduled successfully."
