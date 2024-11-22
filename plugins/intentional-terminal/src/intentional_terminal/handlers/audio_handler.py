# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

# From https://github.com/run-llama/openai_realtime_client/blob/main/openai_realtime_client/handlers/audio_handler.py
# Original is MIT licensed.
"""
CLI handler for the bot's audio input and output.

Uses PyAudio for audio input and output, and runs a separate thread for recording and playing audio.

When playing audio, it uses a buffer to store audio data and plays it continuously to ensure smooth playback.
"""
from typing import Optional

import queue
import asyncio
import datetime
import threading

import pyaudio
import structlog
from pydub import AudioSegment


log = structlog.get_logger(logger_name=__name__)


class AudioHandler:
    """
    Handles audio input and output for the chatbot.

    Uses PyAudio for audio input and output, and runs a separate thread for recording and playing audio.

    When playing audio, it uses a buffer to store audio data and plays it continuously to ensure smooth playback.

    Args:
        audio_format:
            The audio format (paInt16).
        channels:
            The number of audio channels (1).
        rate:
            The sample rate (24000).
        chunk:
            The size of the audio buffer (1024).
    """

    def __init__(
        self,
        audio_format: int = pyaudio.paInt16,
        channels: int = 1,
        rate: int = 24000,
        chunk: int = 1024,
    ):
        # Audio parameters
        self.audio_format = audio_format
        self.channels = channels
        self.rate = rate
        self.chunk = chunk

        self.audio = pyaudio.PyAudio()

        # Recording attributes
        self.recording_stream: Optional[pyaudio.Stream] = None
        self.recording_thread = None
        self.recording = False

        # Model streaming attributes
        self.streaming = False
        self.model_stream = None

        # Playback attributes
        self.playback_stream = None
        self.playback_play_time = 0
        self.playback_buffer = queue.Queue()
        self.playback_event = threading.Event()
        self.playback_thread = None
        self.stop_playback = False

        self.frames = []
        self.currently_playing = False

    async def start_streaming(self, client_streaming_callback):
        """Start continuous audio streaming."""
        if self.streaming:
            return

        self.streaming = True
        self.model_stream = self.audio.open(
            format=self.audio_format, channels=self.channels, rate=self.rate, input=True, frames_per_buffer=self.chunk
        )
        while self.streaming:
            try:
                # Read raw PCM data
                data = self.model_stream.read(self.chunk, exception_on_overflow=False)
                # Stream directly without trying to decode
                await client_streaming_callback({"audio_chunk": data})
            except Exception:  # pylint: disable=broad-except
                log.exception("Error streaming")
                break
            await asyncio.sleep(0.01)

    def stop_streaming(self):
        """
        Stop audio streaming.
        """
        self.streaming = False
        if self.model_stream:
            self.model_stream.stop_stream()
            self.model_stream.close()
            self.model_stream = None

    def play_audio(self, audio_data: bytes):
        """
        Add audio data to the buffer

        Args:
            audio_data: The audio data to play.
        """
        audio_segment = AudioSegment(audio_data, sample_width=2, frame_rate=24000, channels=1)
        try:
            self.playback_buffer.put_nowait(audio_segment)
        except queue.Full:
            # If the buffer is full, remove the oldest chunk and add the new one
            self.playback_buffer.get_nowait()
            self.playback_buffer.put_nowait(audio_segment)

        if not self.playback_thread or not self.playback_thread.is_alive():
            self.stop_playback = False
            self.playback_event.clear()
            self.playback_thread = threading.Thread(target=self._continuous_playback)
            self.playback_thread.start()

    def _continuous_playback(self):
        """
        Continuously play audio from the buffer.
        """
        self.playback_stream = self.audio.open(
            format=self.audio_format, channels=self.channels, rate=self.rate, output=True, frames_per_buffer=self.chunk
        )
        while not self.stop_playback:
            try:
                audio_segment = self.playback_buffer.get(timeout=0.1)
                self.playback_play_time += len(audio_segment)
                self._play_audio_chunk(audio_segment)
            except queue.Empty:
                self.playback_play_time = 0
                log.debug("Audio buffer empty")
                continue

            if self.playback_event.is_set():
                break

        if self.playback_stream:
            self.playback_stream.stop_stream()
            self.playback_stream.close()
            self.playback_stream = None

    def _play_audio_chunk(self, audio_segment: AudioSegment):
        try:
            # Ensure the audio is in the correct format for playback
            audio_data = audio_segment.raw_data

            # Play the audio chunk in smaller portions to allow for quicker interruption
            chunk_size = 1024  # Adjust this value as needed
            for i in range(0, len(audio_data), chunk_size):
                if self.playback_event.is_set():
                    break
                chunk = audio_data[i : i + chunk_size]
                self.playback_stream.write(chunk)
        except Exception:  # pylint: disable=broad-except
            log.exception("Error playing audio chunk")

    def stop_playback_immediately(self) -> datetime.timedelta:
        """
        Stop audio playback immediately. Sets the relevant flags and empties the queue.

        """
        played_milliseconds = 0
        if self.playback_play_time:
            played_milliseconds = self.playback_play_time
            self.playback_play_time = 0

        self.stop_playback = True
        self.playback_buffer.queue.clear()  # Clear any pending audio
        self.currently_playing = False
        self.playback_event.set()
        return played_milliseconds

    def cleanup(self):
        """
        Clean up audio resources.
        """
        self.stop_playback_immediately()

        self.stop_playback = True
        if self.playback_thread:
            self.playback_thread.join()

        self.recording = False
        if self.recording_stream:
            self.recording_stream.stop_stream()
            self.recording_stream.close()

        if self.model_stream:
            self.model_stream.stop_stream()
            self.model_stream.close()

        self.audio.terminate()
