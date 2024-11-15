# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Textual UI for text-based bots.
"""

from typing import Dict, Any
from textual import on
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.containers import Horizontal, Vertical
from textual.widgets import Markdown, Input
from intentional_core import TurnBasedBotStructure


class ChatHistory(Markdown):
    """
    A markdown widget that displays the chat history.
    """


class MessageBox(Input):
    """
    An input widget that allows the user to type a message.
    """

    placeholder = "Message..."


class SystemPrompt(Markdown):
    """
    A markdown widget that displays the system prompt.
    """


class TextChatInterface(App):
    """
    The main interface class for the text-based bot UI.
    """

    CSS_PATH = "example.tcss"

    def __init__(self, bot: TurnBasedBotStructure):
        super().__init__()
        self.bot = bot
        self.bot.add_event_handler("on_text_message_from_model", self.handle_text_messages)
        self.bot.add_event_handler("on_model_starts_generating_response", self.handle_start_text_response)
        self.bot.add_event_handler("on_model_stops_generating_response", self.handle_finish_text_response)
        self.bot.add_event_handler("on_system_prompt_updated", self.handle_system_prompt_updated)

        self.conversation = ""
        self.generating_response = False

    def compose(self) -> ComposeResult:
        """
        Layout for the text-based bot UI.
        """
        yield Horizontal(
            Vertical(
                Markdown("# Chat History"),
                ScrollableContainer(ChatHistory()),
                MessageBox(placeholder="Message..."),
                classes="column bordered chat",
            ),
            Vertical(
                Markdown("# System Prompt"),
                ScrollableContainer(SystemPrompt()),
                classes="column bordered",
            ),
        )

    def on_mount(self) -> None:
        """
        Operations to perform when the UI is mounted.
        """
        self.query_one(SystemPrompt).update(self.bot.model.system_prompt)
        self.query_one(MessageBox).focus()

    @on(MessageBox.Submitted)
    async def send_message(self, event: MessageBox.Changed) -> None:
        """
        Sends a message to the bot when the user presses enter.

        Args:
            event: The event containing the message to send.
        """
        self.conversation += "\n\n**User**: " + event.value
        self.query_one(MessageBox).clear()
        self.query_one(ChatHistory).update(self.conversation)
        await self.bot.send({"role": "user", "content": event.value})

    async def handle_start_text_response(self, _) -> None:
        """
        Prints to the console when the bot starts generating a text response.
        """
        if not self.generating_response:  # To avoid the duplication due to function calls.
            self.generating_response = True
            self.conversation += "\n\n**Assistant:** "
            self.query_one(ChatHistory).update(self.conversation)

    async def handle_finish_text_response(self, _) -> None:
        """
        Prints to the console when the bot stops generating a text response.
        """
        self.generating_response = False

    async def handle_text_messages(self, event: Dict[str, Any]) -> None:
        """
        Prints to the console any text message from the bot. It is usually a chunk as the output is being streamed out.

        Args:
            event: The event dictionary containing the message chunk.
        """
        if event["delta"]:
            self.conversation += event["delta"]
            self.query_one(ChatHistory).update(self.conversation)

    async def handle_system_prompt_updated(self, event: Dict[str, Any]) -> None:
        """
        Prints to the console any text message from the bot.

        Args:
            event: The event dictionary containing the message.
        """
        self.query_one(SystemPrompt).update(event["system_prompt"])  # self.bot.model.system_prompt)
