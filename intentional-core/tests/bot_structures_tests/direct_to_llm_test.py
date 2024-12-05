# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from intentional_core.bot_structures.direct_to_llm import DirectToLLMBotStructure


def test_bot_structure_init(intent_router):
    assert DirectToLLMBotStructure({"llm": {"client": "mock"}}, intent_router)


def test_bot_structure_needs_llm_config(intent_router):
    with pytest.raises(ValueError, match="DirectToLLMBotStructure requires a 'llm' configuration key"):
        DirectToLLMBotStructure({"llm": {}}, intent_router)
