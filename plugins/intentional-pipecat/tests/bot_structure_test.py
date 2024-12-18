# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import Mock, patch
from intentional_core.llm_client import LLMClient
from intentional_pipecat import PipecatBotStructure


@pytest.fixture
def mock_pipecat_module():
    module = Mock()
    module.MockClass.return_value = Mock
    return module


class MockLLMClient(LLMClient):
    name = "mock"

    def __init__(self, config, parent, intent_router):
        pass

    def run(self):
        pass

    def send(self):
        pass

    def handle_interruption(self):
        pass


def test_config_base(mock_pipecat_module):
    with patch("intentional_pipecat.bot_structure.importlib.import_module", return_value=mock_pipecat_module):
        instance = PipecatBotStructure(
            config={
                "llm": {
                    "client": "mock",
                },
                "vad": {
                    "module": "mock",
                    "class": "MockClass",
                },
                "stt": {
                    "module": "mock",
                    "class": "MockClass",
                },
                "tts": {
                    "module": "mock",
                    "class": "MockClass",
                },
            },
            intent_router=Mock(),
        )
        assert isinstance(instance.llm, MockLLMClient)
        assert isinstance(instance.vad_class, Mock)
        assert isinstance(instance.stt_class, Mock)
        assert isinstance(instance.tts_class, Mock)


def test_config_needs_llm():
    with pytest.raises(ValueError, match="llm"):
        PipecatBotStructure(
            config={
                "vad": {
                    "module": "mock",
                    "class": "Mock",
                },
                "stt": {
                    "module": "mock",
                    "class": "Mock",
                },
                "tts": {
                    "module": "mock",
                    "class": "Mock",
                },
            },
            intent_router=Mock(),
        )


def test_config_needs_vad(mock_pipecat_module):
    with patch("intentional_pipecat.bot_structure.importlib.import_module", return_value=mock_pipecat_module):
        with pytest.raises(ValueError, match="vad"):
            PipecatBotStructure(
                config={
                    "llm": {
                        "client": "mock",
                    },
                    "stt": {
                        "module": "mock",
                        "class": "Mock",
                    },
                    "tts": {
                        "module": "mock",
                        "class": "Mock",
                    },
                },
                intent_router=Mock(),
            )


def test_config_needs_stt(mock_pipecat_module):
    with patch("intentional_pipecat.bot_structure.importlib.import_module", return_value=mock_pipecat_module):
        with pytest.raises(ValueError, match="stt"):
            PipecatBotStructure(
                config={
                    "llm": {
                        "client": "mock",
                    },
                    "vad": {
                        "module": "mock",
                        "class": "Mock",
                    },
                    "tts": {
                        "module": "mock",
                        "class": "Mock",
                    },
                },
                intent_router=Mock(),
            )


def test_config_needs_tts(mock_pipecat_module):
    with patch("intentional_pipecat.bot_structure.importlib.import_module", return_value=mock_pipecat_module):
        with pytest.raises(ValueError, match="tts"):
            PipecatBotStructure(
                config={
                    "llm": {
                        "client": "mock",
                    },
                    "vad": {
                        "module": "mock",
                        "class": "Mock",
                    },
                    "stt": {
                        "module": "mock",
                        "class": "Mock",
                    },
                },
                intent_router=Mock(),
            )
