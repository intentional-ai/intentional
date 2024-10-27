# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Silero VAD client.
"""
from intentional_core import VADClient
from silero_vad import load_silero_vad, get_speech_timestamps


class SileroVADClient(VADClient):
    """
    Silero Voice Activity Detection (VAD) client for Intentional
    """

    name = "silero"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = None

    def load(self):
        """
        Load the VAD model
        """
        self.model = load_silero_vad()

    def detect(self, audio: bytes):
        """
        Detect voice activity
        """
        speech_timestamps = get_speech_timestamps(
            audio,
            self.model,
            return_seconds=True,  # Return speech timestamps in seconds (default is samples)
        )
        print(speech_timestamps)
