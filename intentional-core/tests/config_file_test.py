# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

from intentional_core.llm_client import LLMClient
from intentional_core import load_configuration_file


class MockLLMClient(LLMClient):
    name = "mock"

    def __init__(self, config, parent, intent_router):
        self.intent_router = intent_router
        pass

    def run(self):
        pass

    def send(self):
        pass

    def handle_interruption(self):
        pass


def test_config_file_no_vars_no_brackets(tmp_path):
    config_content = """
interface: terminal
modality: text_messages
bot:
    type: direct_to_llm
    llm:
        client: mock

conversation:
    background: "You're an interviewer."

    stages:
        ask_for_availability:
            accessible_from: _start_
            goal: ask if the user has some time to answer some questions.
            outcomes:
                ok:
                    description: user says they have time to answer questions
                    move_to: _end_
    """
    with open(tmp_path / "config.yaml", "w") as file:
        file.write(config_content)
    bot = load_configuration_file(tmp_path / "config.yaml")
    assert (
        bot.bot.llm.intent_router.stages["ask_for_availability"].goal
        == "ask if the user has some time to answer some questions."
    )
