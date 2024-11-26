# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

# Inspired by
# https://github.com/run-llama/openai_realtime_client/blob/main/openai_realtime_client/client/realtime_client.py
# Original is MIT licensed.
"""
Client for OpenAI's Realtime API.
"""

from typing import Dict, Any, Callable

import os
import math
import json
import base64
import asyncio

import structlog
import websockets

from intentional_core import ContinuousStreamModelClient
from intentional_core.intent_routing import IntentRouter
from intentional_core.end_conversation import EndConversationTool
from intentional_openai.tools import to_openai_tool


log = structlog.get_logger(logger_name=__name__)


class RealtimeAPIClient(ContinuousStreamModelClient):
    """
    A client for interacting with the OpenAI Realtime API that lets you manage the WebSocket connection, send text and
    audio data, and handle responses and events.
    """

    name = "openai_realtime"

    events_translation = {
        "error": "on_error",
        "response.text.delta": "on_text_message_from_model",
        "response.audio.delta": "on_audio_message_from_model",
        "response.created": "on_model_starts_generating_response",
        "response.done": "on_model_stops_generating_response",
        "input_audio_buffer.speech_started": "on_user_speech_started",
        "input_audio_buffer.speech_stopped": "on_user_speech_ended",
        "conversation.item.input_audio_transcription.completed": "on_user_speech_transcribed",
        "response.audio_transcript.done": "on_model_speech_transcribed",
    }

    def __init__(self, parent: Callable, intent_router: IntentRouter, config: Dict[str, Any]):
        """
        A client for interacting with the OpenAI Realtime API that lets you manage the WebSocket connection, send text
        and audio data, and handle responses and events.
        """
        log.debug("Loading %s from config", self.__class__.__name__, model_client_config=config)
        super().__init__(parent, intent_router)

        self.model_name = config.get("name")
        if not self.model_name:
            raise ValueError("RealtimeAPIClient requires a 'name' configuration key to know which model to use.")
        if "realtime" not in self.model_name:
            raise ValueError(
                "RealtimeAPIClient requires a 'realtime' model to use the Realtime API. "
                "To use any other OpenAI model, use the OpenAIClient instead."
            )

        self.api_key_name = config.get("api_key_name", "OPENAI_API_KEY")
        if not os.environ.get(self.api_key_name):
            raise ValueError(
                "RealtimeAPIClient requires an API key to authenticate with OpenAI. "
                f"The provided environment variable name ({self.api_key_name}) is not set or is empty."
            )
        self.api_key = os.environ.get(self.api_key_name)
        self.voice = config.get("voice", "alloy")

        # WebSocket connection data
        self.ws = None
        self.base_url = "wss://api.openai.com/v1/realtime"

        # Track current response state
        self._connecting = False
        self._updating_system_prompt = False
        self._current_response_id = None
        self._current_item_id = None

        # Intent routering data
        self.intent_router = intent_router
        self.system_prompt = None
        self.tools = None
        self.setup_initial_prompt()

    def setup_initial_prompt(self) -> None:
        """
        Setup initial prompt and tools. Used also after conversation end to reset the state.
        """
        self.system_prompt = self.intent_router.get_prompt()
        self.tools = self.intent_router.current_stage.tools

    async def connect(self) -> None:
        """
        Establish WebSocket connection with the Realtime API.
        """
        log.debug("Initializing websocket connection to OpenAI Realtime API")

        url = f"{self.base_url}?model={self.model_name}"
        headers = {"Authorization": f"Bearer {self.api_key}", "OpenAI-Beta": "realtime=v1"}
        self.ws = await websockets.connect(url, additional_headers=headers)

        await self._update_session(
            {
                "modalities": ["text", "audio"],
                "instructions": self.system_prompt,
                "voice": self.voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {"model": "whisper-1"},
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 500,
                    "silence_duration_ms": 200,
                },
                "tools": [to_openai_tool(tool) for tool in self.tools.values()],
                "tool_choice": "auto",
                "temperature": 0.8,
            }
        )
        # Flag that we're connecting and look for this event in the run loop
        self._connecting = True

    async def disconnect(self) -> None:
        """
        Close the WebSocket connection.
        """
        if self.ws:
            log.debug("Disconnecting from OpenAI Realtime API")
            await self.ws.close()
        else:
            log.debug("Attempted disconnection of a OpenAIRealtimeAPIClient that was never connected, nothing done.")
        await self.emit("on_model_disconnection", {})

    async def run(self) -> None:  # pylint: disable=too-many-branches
        """
        Handles events coming from the WebSocket connection.

        This method is an infinite loop that listens for messages from the WebSocket connection and processes them
        accordingly. It also triggers the event handlers for the corresponding event types.
        """
        try:
            async for message in self.ws:
                event = json.loads(message)
                event_name = event.get("type")
                log.debug("Received event", event_name=event_name)

                if event_name == "error":
                    log.error("An error response was returned", event_data=event)

                elif event_name == "session.updated":
                    log.debug("Session configuration updated", event_data=event)
                    # Check why we updated the session and emit the corresponding event
                    if self._connecting:
                        self._connecting = False
                        await self.emit("on_model_connection", event)
                    if self._updating_system_prompt:
                        self._updating_system_prompt = False
                        await self.emit("on_system_prompt_updated", {"system_prompt": event["session"]["instructions"]})

                # Track agent response state
                elif event_name == "response.created":
                    self._current_response_id = event.get("response", {}).get("id")
                    log.debug("Agent started responding. Response created.", response_id=self._current_response_id)

                elif event_name == "response.output_item.added":
                    self._current_item_id = event.get("item", {}).get("id")
                    log.debug("Agent is responding. Added response item.", response_id=self._current_item_id)

                elif event_name == "response.done":
                    log.debug("Agent finished generating a response.", response_id=self._current_item_id)

                # Tool call
                elif event_name == "response.function_call_arguments.done":
                    await self._call_tool(event)

                # Events from VAD related to the user's input
                elif event_name == "input_audio_buffer.speech_started":
                    log.debug("Speech detected.")

                elif event_name == "input_audio_buffer.speech_stopped":
                    log.debug("Speech ended.")

                # Relay the event to the parent BotStructure - regardless whether it was processed above or not
                if event_name in self.events_translation:
                    log.debug(
                        "Translating event",
                        old_event_name=event_name,
                        new_event_name=self.events_translation[event_name],
                    )
                    event["type"] = self.events_translation[event_name]
                    await self.emit(self.events_translation[event_name], event)
                else:
                    log.debug("Sending native event to parent", event_name=event_name)
                    await self.emit(event_name, event)

        except websockets.exceptions.ConnectionClosedOK:
            await asyncio.sleep(1)
            log.warning("Connection closed.")
            return

        except Exception:  # pylint: disable=broad-except
            await asyncio.sleep(1)
            log.exception("Error in message handling")
            return

        log.debug(".run() exited without errors.")

    async def send(self, data: Dict[str, Any]) -> None:
        """
        Stream data to the API.

        Args:
            data:
                The data chunk to stream. It should be in the format {"audio": bytes}.
        """
        if "audio_chunk" in data:
            await self._send_audio_stream(data["audio_chunk"])
        # if "audio_message" in data:
        #     await self._send_audio(data["audio_message"])
        # if "text_message" in data:
        #     await self._send_text_message(data["text_message"])

    async def update_system_prompt(self) -> None:
        """
        Update the system prompt to use in the conversation.
        """
        log.debug("Setting new system prompt", system_prompt=self.system_prompt)
        log.debug("Setting new tools", tools=list(self.tools.keys()))
        await self._update_session(
            {"instructions": self.system_prompt, "tools": [to_openai_tool(t) for t in self.tools.values()]}
        )
        # Flag that we're updating the system prompt and look for this event in the run loop
        self._updating_system_prompt = True

    async def handle_interruption(self, lenght_to_interruption: int) -> None:
        """
        Handle user interruption of the current response.

        Args:
            lenght_to_interruption (int):
                The length in milliseconds of the audio that was played to the user before the interruption.
                May be zero if the interruption happened before any audio was played.
        """
        log.info("[Handling interruption at %s ms]", lenght_to_interruption, interruption_time=lenght_to_interruption)

        # Cancel the current response
        # Cancelling responses is effective when the response is still being generated by the model.
        if self._current_response_id:
            log.debug("Cancelling response due to a user's interruption.", response_id=self._current_response_id)
            event = {"type": "response.cancel"}
            await self.ws.send(json.dumps(event))
        else:
            log.warning("No response ID found to cancel.")

        # Truncate the conversation item to what was actually played
        # Truncating the response is effective when the response has already been generated by the model and is being
        # played out.
        if lenght_to_interruption:
            log.debug(
                "Truncating the response due to a user's interruption at %s ms",
                lenght_to_interruption,
                interruption_time=lenght_to_interruption,
            )
            event = {
                "type": "conversation.item.truncate",
                "item_id": self._current_item_id,
                "content_index": 0,
                "audio_end_ms": math.floor(lenght_to_interruption),
            }
            await self.ws.send(json.dumps(event))

    async def _update_session(self, config: Dict[str, Any]) -> None:
        """
        Update session configuration.

        Args:
            config (Dict[str, Any]):
                The new session configuration.
        """
        event = {"type": "session.update", "session": config}
        await self.ws.send(json.dumps(event))

    async def _send_text_message(self, text: str) -> None:
        """
        Send text message to the API.

        Args:
            text (str):
                The text message to send.
        """
        event = {
            "type": "conversation.item.create",
            "item": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": text}]},
        }
        await self.ws.send(json.dumps(event))
        await self._request_response_from_model()

    async def _send_audio_stream(self, audio_bytes: bytes) -> None:
        audio_b64 = base64.b64encode(audio_bytes).decode()
        append_event = {"type": "input_audio_buffer.append", "audio": audio_b64}
        await self.ws.send(json.dumps(append_event))

    # async def _send_audio_message(self, audio_bytes: bytes) -> None:
    #     """
    #     Send audio data to the API.

    #     Args:
    #         audio_bytes (bytes):
    #             The audio data to send.
    #     """
    #     # Convert audio to required format (24kHz, mono, PCM16)
    #     audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    #     audio = audio.set_frame_rate(24000).set_channels(1).set_sample_width(2)
    #     pcm_data = base64.b64encode(audio.raw_data).decode()

    #     # Append audio to buffer
    #     append_event = {"type": "input_audio_buffer.append", "audio": pcm_data}
    #     await self.ws.send(json.dumps(append_event))

    #     # Commit the buffer
    #     commit_event = {"type": "input_audio_buffer.commit"}
    #     await self.ws.send(json.dumps(commit_event))

    async def _send_function_result(self, call_id: str, result: Any) -> None:
        """
        Send function call result back to the API.

        Args:
            call_id (str):
                The ID of the function call.
            result (Any):
                The result of the function call.
        """
        event = {
            "type": "conversation.item.create",
            "item": {"type": "function_call_output", "call_id": call_id, "output": result},
        }
        await self.ws.send(json.dumps(event))
        await self._request_response_from_model()

    async def _request_response_from_model(self) -> None:
        """
        Asks the LLM for a response to the messages it just received.
        You need to call this function right after sending a messages that is not streamed like the audio (where the
        model's VAD would decide when to reply instead).
        """
        event = {"type": "response.create", "response": {"modalities": ["text", "audio"]}}
        await self.ws.send(json.dumps(event))

    async def _call_tool(self, event: Dict[str, Any]) -> None:
        """
        Calls the tool requested by the model.

        Args:
            event (Dict[str, Any]):
                The event containing the tool call information.
        """
        call_id = event["call_id"]
        tool_name = event["name"]
        tool_arguments = json.loads(event["arguments"])
        log.debug("Calling tool", tool_name=tool_name, tool_arguments=tool_arguments, call_id=call_id)

        # Check if it's the router
        if tool_name == self.intent_router.name:
            self.system_prompt, self.tools = await self.intent_router.run(tool_arguments)
            await self.update_system_prompt()
            await self._send_function_result(event["call_id"], "ok")
            return

        # Check if the conversation should end
        if tool_name == EndConversationTool.name:
            await self.tools[EndConversationTool.name].run()
            await self.disconnect()
            self.setup_initial_prompt()
            await self.emit("on_conversation_ended", {})
            await self.connect()
            return

        # Emit the event
        self.emit("on_tool_invoked", {"name": tool_name, "args": tool_arguments})

        # Make sure the tool actually exists
        if tool_name not in self.tools:
            log.error("Tool '%s' not found in the list of available tools.", tool_name)
            await self._send_function_result(call_id, f"Error: Tool {tool_name} not found")

        # Invoke the tool and send back the output
        result = await self.tools.get(tool_name).run(tool_arguments)
        log.debug("Tool run", tool_name=tool_name, tool_output=result)
        await self._send_function_result(call_id, str(result))
