# Copyright (c) 2020, NVIDIA CORPORATION. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#  * Neither the name of NVIDIA CORPORATION nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import queue
import sys

import grpc
import pyaudio
import riva_api.riva_asr_pb2 as rasr
import riva_api.riva_asr_pb2_grpc as rasr_srv
import riva_api.riva_audio_pb2 as ra

from camel_tools.utils.charmap import CharMapper
from camel_tools.utils.transliterate import Transliterator

RATE = 16000
# CHUNK = int(RATE / 10)  # 100ms
CHUNK = 7200 # 100ms
LANG_AR = "ar-SA"
LANG_EN = "en-US"
LANG_FR = "fr-FR"
LANG_HI = "hi-IN"
MODEL_AR = "CMR_AR_EM_CH_06_BWR_STR"
MODEL_FR = "rodin_conformer_fr_streaming"
MODEL_EN = "CNF_EN_18L_512D_128V"
# MODEL_HI = "CNF_HI_18L_512D_3072V_LM4G"
# MODEL_HI = "stt_hi_conformer_ctc_medium"
MODEL_HI = "CMR_HI_18L_128V"
LANG = LANG_AR
MODEL = MODEL_AR


def get_args():
    parser = argparse.ArgumentParser(description="Streaming transcription via Riva AI Services")
    # parser.add_argument("--server", default="77.242.240.151:443", type=str, help="URI to GRPC server endpoint")
    parser.add_argument("--server", default="audio.rodinai.site:50051", type=str, help="URI to GRPC server endpoint")
    parser.add_argument("--input-device", type=int, default=None, help="output device to use")
    parser.add_argument("--list-devices", action="store_true", help="list output devices indices")
    parser.add_argument("--language-code", default=LANG, type=str, help="Language code of the model to be used")
    return parser.parse_args()


class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self, rate, chunk, device=None):
        self._rate = rate
        self._chunk = chunk
        self._device = device

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            input_device_index=self._device,
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)


bw_marker = "नक"
bw2ar = Transliterator(CharMapper.builtin_mapper('bw2ar'), marker=bw_marker)


def convert2ar(bw_text: str) -> str:
    ar_text = bw2ar.transliterate(bw_text, strip_markers=True)
    return ar_text


def listen_print_loop(responses):
    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue

        partial_transcript = ""
        for result in response.results:
            if not result.alternatives:
                continue

            transcript = result.alternatives[0].transcript
            transcript = " ".join([convert2ar(word) for word in transcript.strip().split()])

            if not result.is_final:
                partial_transcript += transcript
            else:
                # overwrite_chars = ' ' * (num_chars_printed - len(transcript))
                overwrite_chars = ''
                print(""+ transcript + overwrite_chars + "\n")
                num_chars_printed = 0

        if partial_transcript != "":
            # overwrite_chars = ' ' * (num_chars_printed - len(partial_transcript))
            overwrite_chars = ''
            sys.stdout.write("" + partial_transcript + overwrite_chars + '\r')
            sys.stdout.flush()
            # num_chars_printed = len(partial_transcript) + 3


#
# def listen_print_loop(responses):
#     # num_chars_printed = 0
#     for response in responses:
#         if not response.results:
#             continue
#
#         partial_transcript = ""
#         for result in response.results:
#             # print("audio_processed: {}".format(result.audio_processed))
#             # print("stability: {}".format(result.stability))
#             if not result.alternatives:
#                 continue
#
#             # for index, alternative in enumerate(result.alternatives):
#             #     print("{}: {}".format(index, alternative.confidence))
#
#             transcript = result.alternatives[0].transcript
#             # if LANG == LANG_AR:
#             #     if "ال ال" in transcript:
#             #         transcript = transcript.replace("ال ال", " [موسيقى] ").replace("  ", " ")
#             #     elif transcript == "ال":
#             #         transcript = "[صوت غير معروف]"
#             # transcript = transcript.replace("  ", "**").replace(" ", "").replace("**", " ")
#             # words = []
#             # for word in str(transcript).split("  "):
#             #     word = word.replace(" ", "")
#             #     words.append(word)
#
#             # transcript = " ".join(words)
#
#             if not result.is_final:
#                 partial_transcript += transcript
#             else:
#                 # overwrite_chars = ' ' * (num_chars_printed - len(transcript))
#                 # print("## " + transcript + "." + "\n")
#                 print(transcript)
#                 # num_chars_printed = 0
#
#         if partial_transcript != "":
#             # overwrite_chars = ' ' * (num_chars_printed - len(partial_transcript))
#             sys.stdout.write(">> " + partial_transcript + '\r')
#             sys.stdout.flush()
#             # num_chars_printed = len(partial_transcript) + 3


def main():
    args = get_args()

    if args.list_devices:
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] < 1:
                continue
            print(f"{info['index']}: {info['name']}")
        sys.exit(0)

    channel = grpc.insecure_channel(args.server)
    client = rasr_srv.RivaSpeechRecognitionStub(channel)

    config = rasr.RecognitionConfig(
        encoding=ra.AudioEncoding.LINEAR_PCM,
        sample_rate_hertz=RATE,
        language_code=args.language_code,
        max_alternatives=1,
        audio_channel_count=1,
        enable_word_time_offsets=True,
        verbatim_transcripts=True,
        enable_separate_recognition_per_channel=False,
        model=MODEL,
        enable_automatic_punctuation=False
    )
    streaming_config = rasr.StreamingRecognitionConfig(config=config, interim_results=True)

    with MicrophoneStream(RATE, CHUNK, device=args.input_device) as stream:
        audio_generator = stream.generator()
        requests = (rasr.StreamingRecognizeRequest(audio_content=content) for content in audio_generator)

        def build_generator(cfg, gen):
            yield rasr.StreamingRecognizeRequest(streaming_config=cfg)
            for x in gen:
                yield x

        responses = client.StreamingRecognize(build_generator(streaming_config, requests))

        listen_print_loop(responses)


if __name__ == '__main__':
    main()
