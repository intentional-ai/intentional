# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Tool utilities to interact with tools in OpenAI.
"""

from intentional_core import Tool


def to_openai_tool(tool: Tool):
    """
    The tool definition required by OpenAI.
    """
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description,
        "parameters": {
            "type": "object",
            "properties": {
                param.name: {"description": param.description, "type": param.type, "default": param.default}
                for param in tool.parameters
            },
            "required": [param.name for param in tool.parameters if param.required],
        },
    }
