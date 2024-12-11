# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
import intentional_core.tools as tools
from intentional_core.tools import Tool, ToolParameter, load_tools_from_dict


@pytest.fixture(autouse=True)
def clear_collected_tools():
    tools._TOOL_CLASSES = {}


def test_define_tool():

    class TestTool(Tool):
        id = "ok-test-tool"
        name = "OK Test Tool"
        description = "A test tool for testing purposes."
        parameters = [
            ToolParameter(
                name="test_param",
                description="A test parameter.",
                type=str,
                required=True,
                default=None,
            )
        ]

        async def run(self, params=None):
            return True

    tools = load_tools_from_dict([{"id": "ok-test-tool"}])
    assert len(tools) == 1
    assert list(tools.keys()) == ["OK Test Tool"]
    assert isinstance(tools["OK Test Tool"], TestTool)


def test_missing_id():

    class TestTool(Tool):
        name = "No ID Test Tool"
        description = "A test tool for testing purposes."
        parameters = [
            ToolParameter(
                name="test_param",
                description="A test parameter.",
                type=str,
                required=True,
                default=None,
            )
        ]

        async def run(self, params=None):
            return True

    with pytest.raises(ValueError, match="Unknown tool"):
        load_tools_from_dict([{"id": "no-id-test-tool"}])


def test_missing_name():

    class TestTool(Tool):
        id = "no-name-test-tool"
        description = "A test tool for testing purposes."
        parameters = [
            ToolParameter(
                name="test_param",
                description="A test parameter.",
                type=str,
                required=True,
                default=None,
            )
        ]

        async def run(self, params=None):
            return True

    with pytest.raises(ValueError, match="must have a name"):
        load_tools_from_dict([{"id": "no-name-test-tool"}])


def test_missing_description():

    class TestTool(Tool):
        id = "no-desc-test-tool"
        name = "No Desc Test Tool"
        parameters = [
            ToolParameter(
                name="test_param",
                description="A test parameter.",
                type=str,
                required=True,
                default=None,
            )
        ]

        async def run(self, params=None):
            return True

    with pytest.raises(ValueError, match="must have a description"):
        load_tools_from_dict([{"id": "no-desc-test-tool"}])


def test_missing_parameters():

    class TestTool(Tool):
        id = "no-params-test-tool"
        name = "No Params Test Tool"
        description = "A test tool for testing purposes."

        async def run(self, params=None):
            return True

    with pytest.raises(ValueError, match="must have parameters"):
        load_tools_from_dict([{"id": "no-params-test-tool"}])


def test_missing_run():

    class TestTool(Tool):
        id = "no-run-test-tool"
        name = "No Run Test Tool"
        description = "A test tool for testing purposes."
        parameters = [
            ToolParameter(
                name="test_param",
                description="A test parameter.",
                type=str,
                required=True,
                default=None,
            )
        ]

    with pytest.raises(ValueError, match="Unknown tool"):
        load_tools_from_dict([{"id": "no-run-test-tool"}])
