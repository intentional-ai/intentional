# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Callable, Dict, List
from datetime import datetime
from textual import on
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.containers import Horizontal, Vertical
from textual.widgets import Markdown, Input


class ChatHistory(Markdown):

    def update_me(self, conversation: str):
        self.update(conversation)


class MessageBox(Input):
    pass


class SystemPrompt(Markdown):

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.set_interval(1, self.update_me)

    def update_me(self):
        self.update("# System Prompt\nCurrent Time: " + str(datetime.now()))


class TextChatInterface(App):
    CSS_PATH = "example.tcss"

    def __init__(
        self,
        send_message_callback: Callable[[str], None] = None,
        check_end_conversation: Callable[[], None] = None,
    ):
        super().__init__()
        self.send_message_callback = send_message_callback
        self.check_end_conversation = check_end_conversation
        self.conversation = ""

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                Markdown("# Chat History"),
                ScrollableContainer(ChatHistory()),
                MessageBox(placeholder="Message..."),
                classes="column bordered chat",
            ),
            SystemPrompt(classes="bordered column"),
        )

    def on_mount(self) -> None:
        self.query_one(MessageBox).focus()

    def update_chat_history(self, conversation: List[Dict[str, str]]) -> None:
        self.query_one(ChatHistory).update_me(conversation)

    @on(MessageBox.Submitted)
    async def send_message(self, event: MessageBox.Changed) -> None:
        self.conversation += "\n\n**User**: " + event.value
        self.query_one(MessageBox).clear()

        if self.send_message_callback:
            response_stream = self.send_message_callback({"role": "user", "content": event.value})

        self.conversation += "\n\n**Assistant**: "
        async for delta in response_stream:
            self.conversation += delta.get("content") or " "
            self.query_one(ChatHistory).update(self.conversation)

        if self.check_end_conversation():
            self.query_one(MessageBox).disable()
            self.query_one(MessageBox).placeholder = "Conversation has ended."
            self.query_one(MessageBox).focus()


if __name__ == "__main__":
    app = TextChatInterface()
    app.run()
