# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Callable, Dict, List
import logging
from textual import on
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.containers import Horizontal, Vertical
from textual.widgets import Markdown, Input


class ChatHistory(Markdown):
    pass

class MessageBox(Input):
    pass

class SystemPrompt(Markdown):
    pass

class TextChatInterface(App):
    CSS_PATH = "example.tcss"

    def __init__(
        self,
        send_message_callback: Callable[[str], None] = None,
        check_end_conversation: Callable[[], None] = None,
        get_system_prompt: Callable[[], None] = None,
    ):
        super().__init__()
        self.send_message_callback = send_message_callback
        self.check_end_conversation = check_end_conversation
        self.get_system_prompt = get_system_prompt
        self.conversation = ""

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                Markdown("# Chat History"),
                ScrollableContainer(ChatHistory()),
                MessageBox(placeholder="Message..."),
                classes="column bordered chat",
            ),
            Vertical(
                ScrollableContainer(SystemPrompt()),
                classes="column bordered",
            )
        )

    def on_mount(self) -> None:
        self.query_one(SystemPrompt).update("# System Prompt\n" + self.get_system_prompt())
        self.query_one(MessageBox).focus()

    @on(MessageBox.Submitted)
    async def send_message(self, event: MessageBox.Changed) -> None:
        self.query_one(SystemPrompt).update("# System Prompt\n" + self.get_system_prompt())

        self.conversation += "\n\n**User**: " + event.value
        self.query_one(MessageBox).clear()
        self.query_one(ChatHistory).update(self.conversation)

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
        
        self.query_one(SystemPrompt).update("# System Prompt\n" + self.get_system_prompt())



if __name__ == "__main__":
    app = TextChatInterface()
    app.run()
