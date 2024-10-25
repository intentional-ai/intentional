# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

# Inspired from
# https://github.com/run-llama/openai_realtime_client/blob/main/openai_realtime_client/client/realtime_client.py
# Original is MIT licensed.
"""
Client for OpenAI's Realtime API.
"""

from typing import Optional, Dict, Any, Callable

import os
import math
import json
import base64
import logging
import websockets

from intentional_core import ContinuousStreamModelClient


logger = logging.getLogger(__name__)


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
        self.system_prompt = config.get("system_prompt", "You're a helpful assistant.")
        self.tools = config.get("tools", [])

        self.ws = None
        self.base_url = "wss://api.openai.com/v1/realtime"

        # Track current response state
        self._current_response_id = None
        self._current_item_id = None

        # Event handler of the parent's BotStructure class, if needed
        self.parent_event_handler: Optional[Callable] = None

    async def connect(self) -> None:
        """
        Establish WebSocket connection with the Realtime API.
        """
        logger.debug("Initializing websocket connection to OpenAI Realtime API")

        url = f"{self.base_url}?model={self.model_name}"
        headers = {"Authorization": f"Bearer {self.api_key}", "OpenAI-Beta": "realtime=v1"}
        self.ws = await websockets.connect(url, extra_headers=headers)

        # Set up default session configuration
        tools = [t.to_openai_tool()["function"] for t in self.tools]
        for t in tools:
            t["type"] = "function"  # TODO: OpenAI docs didn't say this was needed, but it was

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
                "tools": tools,
                "tool_choice": "auto",
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

    async def run(self) -> None:
        """
        Handles events coming from the WebSocket connection.

        This method is an infinite loop that listens for messages from the WebSocket connection and processes them
        accordingly. It also triggers the event handlers for the corresponding event types.
        """
        try:
            async for message in self.ws:
                event = json.loads(message)
                event_type = event.get("type")
                logger.debug("Received event: %s", event_type)

                if event_type == "error":
                    logger.error("An error response was returned: %s", event)

                # Track response state
                elif event_type == "response.created":
                    self._current_response_id = event.get("response", {}).get("id")
                    logger.debug("Agent strarted responding. Response created with ID: %s", self._current_response_id)

                elif event_type == "response.output_item.added":
                    self._current_item_id = event.get("item", {}).get("id")
                    logger.debug("Agent is responding. Added response item with ID: %s", self._current_item_id)

                elif event_type == "response.done":
                    logger.debug("Agent finished generating a response.")

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

    # async def _send_text(self, text: str) -> None:
    #     """
    #     Send text message to the API.

    #     Args:
    #         text (str):
    #             The text message to send.
    #     """
    #     event = {
    #         "type": "conversation.item.create",
    #         "item": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": text}]},
    #     }
    #     await self.ws.send(json.dumps(event))
    #     await self._create_response()

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

    # async def _send_function_result(self, call_id: str, result: Any) -> None:
    #     """
    #     Send function call result back to the API.

    #     Args:
    #         call_id (str):
    #             The ID of the function call.
    #         result (Any):
    #             The result of the function call.
    #     """
    #     event = {
    #         "type": "conversation.item.create",
    #         "item": {"type": "function_call_output", "call_id": call_id, "output": result},
    #     }
    #     await self.ws.send(json.dumps(event))

    #     # functions need a manual response
    #     await self._create_response()

    # async def _create_response(self, functions: Optional[List[Dict[str, Any]]] = None) -> None:
    #     """
    #     Request a response from the API.
    #     Needed for all messages that are not streamed in a continuous flow like the audio.

    #     Args:
    #         functions (Optional[List[Dict[str, Any]]]):
    #             The functions to call on the response, if any.
    #     """
    #     event = {"type": "response.create", "response": {"modalities": ["text", "audio"]}}
    #     if functions:
    #         event["response"]["tools"] = functions
    #     await self.ws.send(json.dumps(event))

    # async def call_tool(self, event: Dict[str, Any] ) -> None:
    #     call_id = event["call_id"]
    #     tool_name = event['name']
    #     tool_arguments = json.loads(event['arguments'])

    #     tool_selection = ToolSelection(
    #         tool_id="tool_id",
    #         tool_name=tool_name,
    #         tool_kwargs=tool_arguments
    #     )

    #     # avoid blocking the event loop with sync tools
    #     # by using asyncio.to_thread
    #     tool_result = await asyncio.to_thread(
    #         call_tool_with_selection,
    #         tool_selection,
    #         self.tools,
    #         verbose=True
    #     )
    #     await self.send_function_result(call_id, str(tool_result))
