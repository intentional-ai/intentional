# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from intentional_core.llm_client import LLMClient
from intentional_core.intent_routing import IntentRouter


class MockLLMClient(LLMClient):
    name = "mock"

    def __init__(self, parent, intent_router, config):
        super().__init__(parent, intent_router)

    async def run(self):
        pass

    async def send(self, data):
        pass

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def handle_interruption(self, length_to_interruption):
        pass


@pytest.fixture
def intent_router():
    return IntentRouter(
        {
            "stages": {
                "ask_for_name": {
                    "accessible_from": ["_start_"],
                    "goal": "Ask the user for their name",
                },
            }
        }
    )
