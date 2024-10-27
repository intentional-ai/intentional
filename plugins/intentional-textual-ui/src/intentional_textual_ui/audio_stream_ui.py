# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.containers import Horizontal, Vertical
from textual.widgets import Markdown, Input


class ChatHistory(Markdown):

    def update_me(self, conversation: str):
        self.update(conversation)


class MessageBox(Input):
    pass


class BotListeningStatus(Markdown):
    pass


class UserSpeakingStatus(Markdown):
    pass


class SystemPrompt(Markdown):

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.set_interval(1, self.update_me)

    def update_me(self):
        self.update("# System Prompt\nCurrent Time: " + str(datetime.now()))


class AudioStreamInterface(App):
    CSS_PATH = "example.tcss"

    def __init__(self):
        super().__init__()
        self.conversation = ""

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                BotListeningStatus("# Bot is connecting..."),
                UserSpeakingStatus("# User is silent..."),
                Markdown("# Chat History"),
                ScrollableContainer(ChatHistory()),
                classes="column bordered chat",
            ),
            SystemPrompt(classes="bordered column"),
        )

    def update_chat_history(self, message: str) -> None:
        self.conversation += message + "\n\n"
        self.query_one(ChatHistory).update(self.conversation)

    def update_bot_listening_status(self, status: str) -> None:
        self.query_one(BotListeningStatus).update("# Bot is " + status + "...")

    def update_user_speaking_status(self, status: str) -> None:
        self.query_one(UserSpeakingStatus).update("# User is " + status + "...")


if __name__ == "__main__":
    app = AudioStreamInterface()
    app.run()
