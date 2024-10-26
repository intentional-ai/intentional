# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Sample tools for Intentional's examples.
"""

from datetime import datetime
from intentional_core.tools import Tool


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
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
