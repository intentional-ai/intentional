# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Gradio-based bot interface for Intentional.
"""

from typing import Any, Dict

import asyncio
import base64
import threading
import logging

import numpy as np
from pydub import AudioSegment

import gradio
from intentional_core import (
    BotInterface,
    BotStructure,
    TurnBasedBotStructure,
    ContinuousStreamBotStructure,
    load_bot_structure_from_dict,
)


logger = logging.getLogger(__name__)

logging.getLogger("multipart").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("matplotlib").setLevel(logging.ERROR)
logging.getLogger("numba").setLevel(logging.ERROR)


class GradioBotInterface(BotInterface):
    """
    Bot that uses a Gradio interface to interact with the user.
    """

    name = "gradio"

    def __init__(self, config: Dict[str, Any]):
        # Init the structure
        bot_structure_config = config.pop("bot", None)
        if not bot_structure_config:
            raise ValueError("GradioBotInterface requires a 'bot' configuration key to know how to structure the bot.")
        logger.debug("Creating bot structure of type '%s'", bot_structure_config)
        self.bot: BotStructure = load_bot_structure_from_dict(bot_structure_config)

        self.title = config.pop("title", "Intentional")
        self.description = config.pop("description", "An AI assistant powered by Intentional.")

        # Check the modality
        self.modality = config.pop("modality")
        logger.debug("Modality for GradioBotInterface is set to: %s", self.modality)

        self.recording_thread = None

    async def run(self) -> None:
        """
        Chooses the specific loop to use for this combination of bot and modality and kicks it off.
        """
        if isinstance(self.bot, ContinuousStreamBotStructure):
            if self.modality == "audio_stream":
                await self._run_audio_stream(self.bot)
            else:
                raise ValueError(
                    f"Modality '{self.modality}' is not yet supported for '{self.bot.name}' bots."
                    "These are the supported modalities: 'audio_stream'."
                )

        if isinstance(self.bot, TurnBasedBotStructure):
            if self.modality == "text_turns":
                await self._run_text_turns(self.bot)
            else:
                raise ValueError(
                    f"Modality '{self.modality}' is not yet supported for '{self.bot.name}' bots."
                    "These are the supported modalities: 'text_turns'."
                )

    async def _run_text_turns(self, bot: TurnBasedBotStructure) -> None:
        """
        Runs the interface interface for the text turns modality.
        """
        logger.debug("Running the GradioBotInterface in text turns mode.")

        async def send_message(message, _):
            response = await bot.send_message({"role": "user", "content": message})
            output = ""
            async for delta in response:
                output += delta.get("content", "")
                yield output

        with gradio.Blocks() as demo:
            with gradio.Row():
                gradio.Markdown(f"# {self.title}")
            with gradio.Row():
                with gradio.Column(scale=2, min_width=300):
                    gradio.ChatInterface(send_message, type="messages", theme="soft")
                with gradio.Column(scale=1, min_width=300):
                    gradio.Markdown("### Current System Prompt\n\n TDB")
        demo.launch()

    async def _run_audio_stream(self, bot: ContinuousStreamBotStructure) -> None:
        """
        Runs the CLI interface for the continuous audio streaming modality.
        """
        logger.debug("Running the LocalBotInterface in continuous audio streaming mode.")

        # import time

        # def add_to_stream(audio, stream):
        #     if stream is None:
        #         stream = audio
        #     else:
        #         stream = (audio[0], np.concatenate((stream[1], audio[1])))

        #     print(stream[1].shape)
        #     return audio, stream

        # def play_again(stream):
        #     time.sleep(0.5)
        #     print("----", stream[1].shape)
        #     return gradio.Audio(label="Recording", type="numpy", value=stream)

        # with gradio.Blocks() as demo:
        #     stream = gradio.State()
        #     mic = gradio.Audio(sources=['microphone'], type="numpy", streaming=True)
        #     out = gradio.Audio(label="Output Audio", type="numpy", autoplay=True, streaming=True, interactive=False)
        #     mic.stream(
        #         add_to_stream,
        #         [mic, stream],
        #         [out, stream],
        #     )
        #     mic.stop_recording(play_again, stream, out)

        # demo.launch()

        try:

            async def stream_to_model(audio_data, input_state):
                # print(audio_data, audio_data[1].shape)
                try:

                    audio = np.array([audio_data[1][:, 0]])
                    sound = AudioSegment(
                        audio.tobytes(), frame_rate=audio_data[0], sample_width=audio_data[1].dtype.itemsize, channels=1
                    )
                    sound = sound.set_frame_rate(24000)
                    numpy_sound = np.array([sound.get_array_of_samples()]).T

                    # print(sound, sound[1].shape)
                    await bot.stream_data(numpy_sound.tobytes())

                    sound_to_store = (24000, numpy_sound)
                    if not input_state:
                        input_state = sound_to_store
                    else:
                        input_state = (sound_to_store[0], np.concatenate((input_state[1], sound_to_store[1])))
                    return input_state

                except Exception as e:  # pylint: disable=broad-except
                    logger.exception("Error streaming: %s", e)
                    return

            def get_audio_from_state(state):
                if state:
                    return state.pop(0)
                return None

            def play_recording(state):
                print("Playing recording!")

                # Save the audio to a file
                with open("audio.wav", "wb") as f:
                    f.write(state[1].tobytes())

                return gradio.Audio(label="Recording", type="numpy", value=state)

            with gradio.Blocks(analytics_enabled=False) as demo:
                input_state = gradio.State()
                output_state = gradio.State()

                mic = gradio.Audio(
                    sources=["microphone"],
                    type="numpy",
                    streaming=True,
                    every=0.5,
                )
                _ = gradio.Audio(
                    label="Output",
                    type="numpy",
                    autoplay=True,
                    streaming=True,
                    interactive=False,
                    value=get_audio_from_state,
                    inputs=[output_state],
                )
                out2 = gradio.Audio(label="Recording", type="numpy")
                mic.stream(stream_to_model, [mic, input_state], [input_state])  # pylint: disable=no-member
                mic.stop_recording(play_recording, input_state, out2)  # pylint: disable=no-member

            async def queue_audio_from_model(event, output_state):
                print("Playing response!")
                print(event["delta"])
                output_state.append(base64.b64decode(event["delta"]))

            # Connect the event handlers
            bot.add_event_handler("*", self.check_for_transcripts)
            bot.add_event_handler("on_audio_message", lambda event: queue_audio_from_model(event, output_state))
            bot.add_event_handler("on_speech_started", self.speech_started)
            bot.add_event_handler("on_speech_stopped", self.speech_stopped)

            logger.debug("Asking the bot to connect to the model...")
            await bot.connect()
            logger.debug("############# Connected to the model!")

            self.recording_thread = threading.Thread(
                target=lambda: asyncio.run(bot.run())
            )  # pylint: disable=attribute-defined-outside-init
            self.recording_thread.start()

            demo.launch()

        except Exception as e:  # pylint: disable=broad-except
            logger.exception("An error occurred: %s", str(e))
        finally:
            await bot.disconnect()
            print("Chat is finished. Bye!")

    # try:
    #     with gradio.Blocks() as demo:
    #         with gradio.Row():
    #             with gradio.Column():
    #                 input_audio = gradio.Audio(label="Input", sources="microphone", type="numpy", streaming=True)
    #                 # gradio.Interface(fn=…, inputs=gradio.Image(streaming=True), output="plot", live=True)
    #             with gradio.Column():
    #                 output_audio = gradio.Audio(label="Output Audio", streaming=True, autoplay=True, type="filepath")

    #         async def stream_data(data):
    #             try:
    #                 # Stream directly without trying to decode
    #                 sampling_rate, audio_array = data

    #                 # # Save the audio to a file
    #                 from pydub import AudioSegment

    #                 audio_buffer = io.BytesIO()
    #                 segment = AudioSegment(
    #                     audio_array.tobytes(),
    #                     frame_rate=sampling_rate,
    #                     sample_width=audio_array.dtype.itemsize,
    #                     channels=(1 if len(audio_array.shape) == 1 else audio_array.shape[1]),
    #                 )
    #                 segment.export(audio_buffer, format="wav")

    #                 await bot.stream_data(audio_buffer.getvalue())

    #                 # with open("audio.wav", "wb") as f:
    #                 #     f.write(audio_buffer.getvalue())

    #             except Exception as e:  # pylint: disable=broad-except
    #                 logger.exception("Error streaming: %s", e)
    #                 return

    #         stream = input_audio.stream(
    #             stream_data,
    #             [input_audio],
    #             [output_audio],
    #             stream_every=0.1,
    #             time_limit=3600,
    #             show_progress=False
    #         )

    #     async def play_response(event):
    #         print("Playing response!")
    #         print(event["delta"])
    #         # await output_audio.play(base64.b64decode(event["delta"]))

    #     # Connect the event handlers
    #     bot.add_event_handler("*", self.check_for_transcripts)
    #     bot.add_event_handler("on_audio_message", play_response)
    #     bot.add_event_handler("on_speech_started", self.speech_started)
    #     bot.add_event_handler("on_speech_stopped", self.speech_stopped)

    #     logger.debug("Asking the bot to connect to the model...")
    #     await bot.connect()
    #     logger.debug("############# Connected to the model!")

    #     self.recording_thread = threading.Thread(target=lambda: asyncio.run(bot.run()))
    #     self.recording_thread.start()

    #     demo.launch()
    #     # self.recording_thread = threading.Thread(target=demo.launch)
    #     # self.recording_thread.start()

    #     # # print("About to run bot!")
    #     # # await bot.run()

    #     # # logger.debug("############# After run()")

    #     # logger.debug("Asking the bot to connect to the model...")
    #     # await bot.connect()
    #     # asyncio.create_task(bot.run())

    #     # print("Chat is ready. Start speaking!")
    #     # print("Press 'q' to quit")
    #     # print("")

    #     # # # Start continuous audio streaming
    #     # # asyncio.create_task(self.audio_handler.start_streaming(bot.stream_data))

    #     # # Simple input loop for quit command
    #     # while True:
    #     #     await asyncio.sleep(1)

    # except Exception as e:  # pylint: disable=broad-except
    #     logger.exception("An error occurred: %s", str(e))
    # finally:
    #     await bot.disconnect()
    #     print("Chat is finished. Bye!")

    async def check_for_transcripts(self, event: Dict[str, Any]) -> None:
        """
        Checks for transcripts from the bot.

        Args:
            event: The event dictionary containing the transcript.
        """
        print(f"Event: {event}")
        if "transcript" in event:
            print(f"[{event["type"]}] Transcript: {event['transcript']}")

    # async def handle_audio_messages(self, event: Dict[str, Any]) -> None:
    #     """
    #     Plays audio responses from the bot.

    #     Args:
    #         event: The event dictionary containing the audio message.
    #     """
    #     self.audio_handler.play_audio(base64.b64decode(event["delta"]))

    async def speech_started(self, event: Dict[str, Any]) -> None:  # pylint: disable=unused-argument
        """
        Prints to the console when the bot starts speaking.

        Args:
            event: The event dictionary containing the speech start event.
        """
        print("[User is speaking]")

        # Handle interruptions if it is the case
        played_milliseconds = self.audio_handler.stop_playback_immediately()  # pylint: disable=no-member
        logging.debug("Played the response for %s milliseconds.", played_milliseconds)

        # If we're interrupting the bot, handle the interruption on the model side too
        if played_milliseconds:
            logging.info("Handling interruption...")
            await self.bot.handle_interruption(played_milliseconds)

    async def speech_stopped(self, event: Dict[str, Any]) -> None:  # pylint: disable=unused-argument
        """
        Prints to the console when the bot stops speaking.

        Args:
            event: The event dictionary containing the speech stop event.
        """
        print("[User stopped speaking]")
