# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tools baseclass for Intentional.
"""


class Tool:
    """
    Tools baseclass for Intentional.
    """

    def to_openai_tool(self):
        """
        The tool definition required by OpenAI.

        FIXME should go in the OpenAI plugin maybe?
        """
        return {"function": {"type": "function"}}
