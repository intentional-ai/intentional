# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

# Inspired from
# https://github.com/run-llama/openai_realtime_client/blob/main/openai_realtime_client/client/realtime_client.py
# Original is MIT licensed.
"""
Client for OpenAI's Realtime API.
"""

from typing import Optional, Dict, Any, Callable, List

import os
import math
import json
import base64
import logging
import websockets

from intentional_core import ContinuousStreamModelClient, Tool, IntentRoutingTool


logger = logging.getLogger(__name__)


ROUTING_SYSTEM_PROMPTS = {
    "gpt-4o-realtime-preview-2024-10-01": """Every time I say something call the 'classify_response' tool.
Wait for the tool reply before doing anything else!""",
}


class RealtimeAPIClient(ContinuousStreamModelClient):
    """
    A client for interacting with the OpenAI Realtime API that lets you manage the WebSocket connection, send text and
    audio data, and handle responses and events.
    """

    name = "openai_realtime"

    native_events_to_known_events = {
        "response.text.delta": "on_text_message",
        "response.audio.delta": "on_audio_message",
        "input_audio_buffer.speech_started": "on_speech_started",
        "input_audio_buffer.speech_stopped": "on_speech_stopped",
    }

    def __init__(self, config: Dict[str, Any]):
        """
        A client for interacting with the OpenAI Realtime API that lets you manage the WebSocket connection, send text
        and audio data, and handle responses and events.
        """
        logger.debug("Loading RealtimeAPIClient from config: %s", config)
        super().__init__()

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
        # self.system_prompt = config.get("system_prompt", "You're a helpful assistant.")

        self.ws = None
        self.base_url = "wss://api.openai.com/v1/realtime"

        # Track current response state
        self._current_response_id = None
        self._current_item_id = None

        # Event handler of the parent's BotStructure class, if needed
        self.parent_event_handler: Optional[Callable] = None

        # Intent routering data
        self.intent_router = IntentRoutingTool()
        self.routing_system_prompt = ROUTING_SYSTEM_PROMPTS[self.model_name]
        self.system_prompt = ""  # Fallback, shouldn't be needed
        self.tools = {}

    async def connect(self) -> None:
        """
        Establish WebSocket connection with the Realtime API.
        """
        logger.debug("Initializing websocket connection to OpenAI Realtime API")

        url = f"{self.base_url}?model={self.model_name}"
        headers = {"Authorization": f"Bearer {self.api_key}", "OpenAI-Beta": "realtime=v1"}
        self.ws = await websockets.connect(url, extra_headers=headers)

        # This initial session is setup to do routing by intent
        await self._update_session(
            {
                "modalities": ["text", "audio"],
                "instructions": self.routing_system_prompt,
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
                "tools": [self.intent_router.to_openai_tool()],  # For now we know we only need the intent router tool
                "tool_choice": "required",
                "temperature": 0.8,
            }
        )

    async def disconnect(self) -> None:
        """
        Close the WebSocket connection.
        """
        if self.ws:
            logger.debug("Disconnecting from OpenAI Realtime API")
            await self.ws.close()
        else:
            logger.debug("Attempted disconnection of a OpenAIRealtimeAPIClient that was never connected, nothing done.")

    async def update_system_prompt(self, new_prompt: str, new_tools: List[Tool]) -> None:
        """
        Update the system prompt to use in the conversation.

        Args:
            new_prompt (str):
                The new system prompt to use.
            new_tools (List[Tool]):
                The new tools to use in the conversation.
        """
        logger.debug("Setting system prompt to: %s", new_prompt)
        await self._update_session(
            {"instructions": new_prompt, "tools": [t.to_openai_tool() for t in new_tools], "tool_choice": "auto"}
        )

    async def restore_routing_prompt(self) -> None:
        """
        Restores the routing prompt.
        """
        logger.debug("Restoring routing prompt.")
        await self._update_session(
            {
                "instructions": self.routing_system_prompt,
                "tools": [self.intent_router.to_openai_tool()],
                "tool_choice": "required",
            }
        )

    async def run(self) -> None:  # pylint: disable=too-many-branches
        """
        Handles events coming from the WebSocket connection.

        This method is an infinite loop that listens for messages from the WebSocket connection and processes them
        accordingly. It also triggers the event handlers for the corresponding event types.
        """
        print("Running!!")
        try:
            async for message in self.ws:
                event = json.loads(message)
                event_type = event.get("type")
                logger.debug("Received event: %s", event_type)

                if event_type == "error":
                    logger.error("An error response was returned: %s", event)

                elif event_type == "session.updated":
                    logger.debug("Session updated to the following configuration: %s", event)

                # Track response state
                elif event_type == "response.created":
                    self._current_response_id = event.get("response", {}).get("id")
                    logger.debug("Agent strarted responding. Response created with ID: %s", self._current_response_id)

                elif event_type == "response.output_item.added":
                    self._current_item_id = event.get("item", {}).get("id")
                    logger.debug("Agent is responding. Added response item with ID: %s", self._current_item_id)

                elif event_type == "response.done":
                    logger.debug("Agent finished generating a response.")
                    await self.restore_routing_prompt()

                elif event_type == "response.function_call_arguments.done":
                    await self.call_tool(event)

                # Handle interruptions
                elif event_type == "input_audio_buffer.speech_started":
                    logger.debug("Speech detected, listening...")

                elif event_type == "input_audio_buffer.speech_stopped":
                    logger.debug("Speech ended.")

                # Call the bot's event handler in all cases, if defined
                if self.parent_event_handler:
                    self.parent_event_handler: Callable

                    if event_type in self.native_events_to_known_events:
                        logger.debug(
                            "Translating event type %s to parent's event handler %s",
                            event_type,
                            self.native_events_to_known_events[event_type],
                        )
                        await self.parent_event_handler(self.native_events_to_known_events[event_type], event)
                    else:
                        logger.debug("Sending native event type %s to parent's event handler", event_type)
                        await self.parent_event_handler(event_type, event)

        except websockets.exceptions.ConnectionClosed:
            logging.info("Connection closed")
        except Exception as e:  # pylint: disable=broad-except
            logging.exception("Error in message handling: %s", str(e))

        print("################### FINISHED RUNNING ##############################")

    async def stream_data(self, data: bytes) -> None:
        return await self._stream_audio(data)

    async def _update_session(self, config: Dict[str, Any]) -> None:
        """
        Update session configuration.

        Args:
            config (Dict[str, Any]):
                The new session configuration.
        """
        event = {"type": "session.update", "session": config}
        await self.ws.send(json.dumps(event))

    async def _stream_audio(self, audio_chunk: bytes) -> None:
        """
        Stream raw audio data to the API.

        Args:
            audio_chunk (bytes):
                The audio data to stream.
        """
        audio_b64 = base64.b64encode(audio_chunk).decode()
        append_event = {"type": "input_audio_buffer.append", "audio": audio_b64}
        await self.ws.send(json.dumps(append_event))

    async def handle_interruption(self, lenght_to_interruption: int) -> None:
        """
        Handle user interruption of the current response.

        Args:
            lenght_to_interruption (int):
                The length in milliseconds of the audio that was played to the user before the interruption.
                May be zero if the interruption happened before any audio was played.
        """
        logging.info("[Handling interruption at %s ms]", lenght_to_interruption)

        # Cancel the current response
        # Cancelling responses is effective when the response is still being generated by the model.
        if self._current_response_id:
            await self._cancel_response()
        else:
            logger.warning("No response ID found to cancel.")

        # Truncate the conversation item to what was actually played
        # Truncating the response is effective when the response has already been generated by the model and is being
        # played out.
        if lenght_to_interruption:
            print(f"[Truncating response at {lenght_to_interruption} ms]")
            await self._truncate_response(lenght_to_interruption)

    async def _cancel_response(self) -> None:
        """
        Cancel the current response.
        """
        logger.debug("Cancelling response %s due to a user's interruption.", self._current_response_id)
        event = {"type": "response.cancel"}
        await self.ws.send(json.dumps(event))

    async def _truncate_response(self, milliseconds_played) -> None:
        """
        Truncate the conversation item to match what was actually played.
        Necessary to correctly handle interruptions.
        """
        print(f"[Truncating response at {milliseconds_played} ms]")
        logger.debug("Truncating the response due to a user's interruption at %s ms", milliseconds_played)
        event = {
            "type": "conversation.item.truncate",
            "item_id": self._current_item_id,
            "content_index": 0,
            "audio_end_ms": math.floor(milliseconds_played),
        }
        await self.ws.send(json.dumps(event))

    async def _send_text(self, text: str) -> None:
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
        await self._create_response()

    # async def _send_audio(self, audio_bytes: bytes) -> None:
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

        # functions need a manual response
        await self._create_response()

    async def _create_response(self, functions: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Request a response from the API.
        Needed for all messages that are not streamed in a continuous flow like the audio.

        Args:
            functions (Optional[List[Dict[str, Any]]]):
                The functions to call on the response, if any.
        """
        event = {"type": "response.create", "response": {"modalities": ["text", "audio"]}}
        if functions:
            event["response"]["tools"] = functions
        await self.ws.send(json.dumps(event))

    async def call_tool(self, event: Dict[str, Any]) -> None:
        """
        Calls the tool requested by the model

        Args:
            event (Dict[str, Any]):
                The event containing the tool call information.
        """
        call_id = event["call_id"]
        tool_name = event["name"]
        tool_arguments = json.loads(event["arguments"])
        logger.debug("Calling tool %s with arguments %s (call_id: %s)", tool_name, tool_arguments, call_id)

        # Check if it's the router
        if tool_name == "classify_response":
            self.system_prompt, self.tools = await self.intent_router.run(tool_arguments)
            await self.update_system_prompt(self.system_prompt, self.tools)
            await self._send_function_result(event["call_id"], "OK")
            return

        # Make sure the tool actually exists
        if tool_name not in self.tools:
            logger.error("Tool %s not found in the list of available tools.", tool_name)
            await self._send_function_result(call_id, f"Error: Tool {tool_name} not found")

        # Invoke the tool
        result = await self.tools.get(tool_name).run(tool_arguments)
        logger.debug("Tool %s returned: %s", tool_name, result)

        await self._send_function_result(call_id, str(result))
