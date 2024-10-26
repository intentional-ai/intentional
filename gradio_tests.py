# import gradio as gr
# from gradio_unifiedaudio import UnifiedAudio
# from pathlib import Path
# import numpy as np
# import time


# # example = UnifiedAudio().example_inputs()

# # dir_ = Path(__file__).parent


# def add_to_stream(audio, stream):
#     if stream is None:
#         stream = audio
#     else:
#         stream = (audio[0], np.concatenate((stream[1], audio[1])))

#     print(stream[1].shape)
#     yield audio, stream
#     # return stream, stream
#     # return stream

# def stop_recording(audio):
#     return gr.Audio(label="Recording", type="numpy", value=audio)

# # def stop_playing():
# #     return UnifiedAudio(value=None, streaming=True), None

# with gr.Blocks() as demo:

#     stream = gr.State()
#     # mic = UnifiedAudio(sources=["microphone"], streaming=True)
#     mic = gr.Audio(sources=['microphone'], type="numpy", streaming=True)
#     out = gr.Audio(label="Output Audio", type="numpy", streaming=True, autoplay=True, interactive=False)
    
#     mic.stop_recording(stop_recording, stream, mic)
#     # mic.end(stop_playing, None, [mic, stream])
#     mic.stop_recording(stop_recording, stream, out)

#     mic.stream(
#         add_to_stream, 
#         [mic, stream], 
#         [out, stream],
#         show_progress='minimal',
#     )

# if __name__ == '__main__':
#     demo.launch()



import gradio
from gradio_unifiedaudio import UnifiedAudio
from pathlib import Path
import numpy as np
import time

# example = UnifiedAudio().example_inputs()
# dir_ = Path(__file__).parent

# def add_to_stream(audio, instream):
#     if instream is None:
#         ret = audio
#     else:
#         ret = (audio[0], np.concatenate((instream[1], audio[1])))
#     return audio, ret

# def stop_recording(audio):
#     return UnifiedAudio(value=audio, streaming=False)

# def stop_playing():
#     return UnifiedAudio(value=None, streaming=True), None

# with gr.Blocks() as demo:
#     mic = UnifiedAudio(sources=["microphone"], streaming=True)
#     stream = gr.State()

#     mic.stop_recording(stop_recording, stream, mic)
#     # mic.end(lambda: [None, None], None, [mic, stream])
#     mic.end(stop_playing, None, [mic, stream])
#     mic.stream(add_to_stream, [mic, stream], [mic, stream])

# if __name__ == '__main__':
#     demo.launch()





def add_to_stream(audio, stream):
    if stream is None:
        stream = audio
    else:
        stream = (audio[0], np.concatenate((stream[1], audio[1])))

    print(stream[1].shape)
    return audio, stream

def play_again(stream):
    time.sleep(0.5)
    print("----", stream[1].shape)
    return gradio.Audio(label="Recording", type="numpy", value=stream)

with gradio.Blocks() as demo:
    stream = gradio.State()
    mic = gradio.Audio(sources=['microphone'], type="numpy", streaming=True)
    out = gradio.Audio(label="Output Audio", type="numpy", autoplay=True, streaming=True, interactive=False)
    mic.stream(
        add_to_stream, 
        [mic, stream], 
        [out, stream],
    )
    mic.stop_recording(play_again, stream, out)

demo.launch()