# # Copyright (c) 2021, ARTOB AI. All rights reserved.
# #
# # Redistribution and use in source and binary forms, with or without
# # modification, are permitted provided that the following conditions
# # are met:
# #  * Redistributions of source code must retain the above copyright
# #    notice, this list of conditions and the following disclaimer.
# #  * Redistributions in binary form must reproduce the above copyright
# #    notice, this list of conditions and the following disclaimer in the
# #    documentation and/or other materials provided with the distribution.
# #  * Neither the name of ARTOB AI nor the names of its
# #    contributors may be used to endorse or promote products derived
# #    from this software without specific prior written permission.
# #
# # THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
# # EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# # IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# # PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# # CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# # EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# # PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# # PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# # OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# # (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# # OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# import argparse
# import queue
# import sys
# import json
#
# import pyaudio
# import websocket
# import certifi
# import ssl
#
# RATE = 16000
# # CHUNK = int(RATE / 10)  # 100ms
# CHUNK = 3072  # 100ms
# LANG_AR = "ar"
# MODEL_AR = "CMR_AR_EM_CH_06_BWR_STR"
# LANG = LANG_AR
# MODEL = MODEL_AR
#
# WS_CONFIG_EXP = json.dumps({"audioConfig": {"aue": "PCM", "sampleRate": 16000}, "speechConfig": {"lang": LANG_AR}})
#
#
# def get_args():
#     parser = argparse.ArgumentParser(description="Streaming transcription via Riva AI Services")
#     parser.add_argument("--url", default="ws://audio.artobai.com:6000", type=str, help="URI to websocket endpoint")
#     parser.add_argument("--input-device", type=int, default=None, help="input device to use")
#     parser.add_argument("--language-code", default=LANG, type=str, help="Language code of the model to be used")
#     return parser.parse_args()
#
#
# args = get_args()
#
#
# class MicrophoneStream(object):
#     """Opens a recording stream as a generator yielding the audio chunks."""
#
#     def __init__(self, rate, chunk, device=None):
#         self._rate = rate
#         self._chunk = chunk
#         self._device = device
#
#         # Create a thread-safe buffer of audio data
#         self._buff = queue.Queue()
#         self.closed = True
#
#     def __enter__(self):
#         self._audio_interface = pyaudio.PyAudio()
#         self._audio_stream = self._audio_interface.open(
#             format=pyaudio.paInt16,
#             input_device_index=self._device,
#             channels=1,
#             rate=self._rate,
#             input=True,
#             frames_per_buffer=self._chunk,
#             stream_callback=self._fill_buffer,
#         )
#
#         self.closed = False
#
#         return self
#
#     def __exit__(self, type, value, traceback):
#         self._audio_stream.stop_stream()
#         self._audio_stream.close()
#         self.closed = True
#         # Signal the generator to terminate so that the client's
#         # streaming_recognize method will not block the process termination.
#         self._buff.put(None)
#         self._audio_interface.terminate()
#
#     def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
#         """Continuously collect data from the audio stream, into the buffer."""
#         self._buff.put(in_data)
#         return None, pyaudio.paContinue
#
#     def generator(self):
#         while not self.closed:
#             chunk = self._buff.get()
#             if chunk is None:
#                 return
#             data = [chunk]
#
#             while True:
#                 try:
#                     chunk = self._buff.get(block=False)
#                     if chunk is None:
#                         return
#                     data.append(chunk)
#                 except queue.Empty:
#                     break
#
#             yield b''.join(data)
#
#
# def listen_print_loop(responses):
#     for response in responses:
#         if not response.results:
#             continue
#
#         partial_transcript = ""
#         for result in response.results:
#             if not result.alternatives:
#                 continue
#
#             transcript = result.alternatives[0].transcript
#             transcript = " ".join([word for word in transcript.strip().split()])
#
#             if not result.is_final:
#                 partial_transcript += transcript
#             else:
#                 overwrite_chars = ''
#                 print("" + transcript + overwrite_chars + "\n")
#
#         if partial_transcript != "":
#             overwrite_chars = ''
#             sys.stdout.write("" + partial_transcript + overwrite_chars + '\r')
#             sys.stdout.flush()
#
#
#
#
# import asyncio
# import json
# import websockets
# import pyaudio
# import sys
#
# URL = "ws://audio.rodinai.site:6000/asr/ar/ws"
# FRAMES_PER_BUFFER = 3200
# FORMAT = pyaudio.paInt16
# CHANNELS = 1
# RATE = 16000
# p = pyaudio.PyAudio()
# # starts recording
# stream = p.open(
#     format=FORMAT,
#     channels=CHANNELS,
#     rate=RATE,
#     input=True,
#     frames_per_buffer=FRAMES_PER_BUFFER,
# )
#
#
# async def send_receive():
#     print(f"Connecting websocket to url ${URL}")
#     async with websockets.connect(
#             URL,
#             ping_interval=5,
#             ping_timeout=20,
#     ) as _ws:
#         await asyncio.sleep(0.1)
#         print("Receiving SessionBegins ...")
#         await _ws.send(json.dumps({"audioConfig": {"aue": "PCM", "sampleRate": 16000}, "speechConfig": {"lang": "ar"}}))
#         session_begins = await _ws.recv()
#         print(session_begins)
#         print("Sending messages ...")
#
#         async def send():
#             while True:
#                 try:
#                     data = stream.read(FRAMES_PER_BUFFER)
#                     await _ws.send(data)
#                 except websockets.WebSocketException as e:
#                     print(e)
#                     assert e.code == 4008
#                     break
#                 except Exception as e:
#                     print(e)
#                     assert False, "Not a websocket 4008 error"
#                 await asyncio.sleep(0.01)
#             return True
#
#         async def receive():
#             partial_transcript = ""
#             while True:
#                 try:
#                     result_str = await _ws.recv()
#                     jd = json.loads(result_str)
#                     transcript = jd["text"]
#                     t_type = jd["type"]
#                     if t_type != "complete":
#                         partial_transcript += transcript
#                     else:
#                         overwrite_chars = ''
#                         print("" + transcript + overwrite_chars + "\n")
#                         partial_transcript = ""
#
#                     if partial_transcript != "":
#                         overwrite_chars = ''
#                         sys.stdout.write("" + partial_transcript + overwrite_chars + '\r')
#                         sys.stdout.flush()
#
#                 except websockets.WebSocketException as e:
#                     print(e)
#                     assert e.code == 4008
#                     break
#                 except Exception as e:
#                     assert False, "Not a websocket 4008 error"
#
#         send_result, receive_result = await asyncio.gather(send(), receive())
#
#
# # use async to run in a loop
# asyncio.run(send_receive())

import asyncio
import websockets
import sys
import json
import logging
import pyaudio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WST")
WS_CONFIG_EXP = json.dumps({"audioConfig": {"aue": "PCM", "sampleRate": 16000}, "speechConfig": {"lang": "ar"}})

FRAMES_PER_BUFFER = 3200
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
p = pyaudio.PyAudio()
# starts recording
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=FRAMES_PER_BUFFER,
)


async def producer_handler(websocket):
    await websocket.send(WS_CONFIG_EXP)
    while True:
        data = stream.read(FRAMES_PER_BUFFER)
        if len(data) > 0:
            # logger.info(data)
            await websocket.send(data)
        await asyncio.sleep(0.00001)


async def consumer_handler(websocket):
    partial_transcript = ""
    async for message in websocket:
        jd = json.loads(message)
        if "text" in jd:
            transcript = jd["text"]
            t_type = jd["type"]
            if t_type != "complete":
                partial_transcript = transcript
            else:
                overwrite_chars = ''
                sys.stdout.write("" + transcript + overwrite_chars + "\n\n")
                partial_transcript = ""
                sys.stdout.flush()

            if partial_transcript != "":
                overwrite_chars = ''
                sys.stdout.write("" + partial_transcript + overwrite_chars + '\r')
                sys.stdout.flush()
        else:
            logger.info(message)


async def handler(websocket):
    await asyncio.gather(
        consumer_handler(websocket),
        producer_handler(websocket),
    )


async def main():
    async with websockets.connect('ws://audio.artobai.com:6000/asr/ar/ws') as websocket:
        await handler(websocket)


loop = asyncio.get_event_loop()
try:
    loop.create_task(main())
    loop.run_forever()
except Exception as e:
    logger.error(e)
finally:
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()
