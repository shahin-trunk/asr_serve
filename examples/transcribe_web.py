import argparse
import json
import wave
import websocket
import certifi
import ssl

parser = argparse.ArgumentParser()
parser.add_argument('--url', help='ASR url', required=False, default="ws://audio.artobai.com:6000")
parser.add_argument('--language', help='Language code eg: ar --> Arabic', default="ar", required=False)
parser.add_argument('--input', help='Input path', required=False, default="res/audio/ar/common_voice_ar_34934679.wav")
args = parser.parse_args()
WS_CONFIG_EXP = json.dumps({"audioConfig": {"aue": "PCM", "sampleRate": 16000},
                            "speechConfig": {"lang": args.language}})
MAX_NUMBER_OF_FRAMES = 3072
ssl_context = ssl.create_default_context()
ssl_context.load_verify_locations(certifi.where())


def on_message(ws, message):
    data = json.loads(message)
    print(data)


def on_error(ws, error):
    print(error)


def on_close(ws, close_status_code, close_msg):
    print(f"### Web socket connection closed. Status code: {close_status_code}, Close message: {close_msg} ###")


def on_open(ws):
    print("Opened connection")
    ws.send(WS_CONFIG_EXP)
    try:
        with wave.open(args.input, "rb") as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                raise Exception("Audio file must be WAV format mono PCM.")
            data = wf.readframes(MAX_NUMBER_OF_FRAMES)
            while len(data) > 0:
                ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
                data = wf.readframes(MAX_NUMBER_OF_FRAMES)
            ws.send("AudioEnd")
    except FileNotFoundError as e:
        print(e)


def test():
    ws = websocket.WebSocketApp(f"{args.url}/asr/{args.language.lower()}/ws",
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})  # Set dispatcher to automatic reconnection


test()
