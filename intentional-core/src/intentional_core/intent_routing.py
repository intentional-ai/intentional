# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Intent routing logic.
"""

from typing import Any, Dict
from intentional_core.tools import Tool, ToolParameter


class IntentRoutingTool(Tool):
    """
    Special tool used to alter the system prompt depending on the user's response.
    """

    name = "classify_response"
    description = "Classify the user's response for later use."
    parameters = [
        ToolParameter(
            "response_type",
            "The type of response, to choose among 'positive', 'negative' or 'neutral'.",
            "string",
            True,
            None,
        ),
    ]

    async def run(self, params: Dict[str, Any]) -> str:
        """
        Given the response's classification, returns the new system prompt.

        Args:
            params: The parameters for the tool. Contains the response_type.

        Returns:
            The new system prompt.
        """
        if params["response_type"] == "positive":
            return "You're an interviewer with a list of questions to ask. First, ask what's my name", {}

        if params["response_type"] == "negative":
            return "You're an interviewer with a list of questions to ask. First, ask what's my age", {}

        return "You're an interviewer with a list of questions to ask. First, ask where do I live", {}
