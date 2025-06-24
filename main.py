import pyaudio
import sys
import json
from vosk import Model, KaldiRecognizer
from ollama import chat
from ollama import ChatResponse

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"

model = Model("Models/vosk-model-small-en-us-0.15")
recognizer = KaldiRecognizer(model, 16000)

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192, input_device_index=2)
stream.start_stream()

messages = []

print(f"{BLUE}\n\nGo ahead and start talking to the AI...")

understanding = False

while True:
    data = stream.read(4096, exception_on_overflow=False)
    if recognizer.AcceptWaveform(data):
        understanding = True
        result = json.loads(recognizer.Result())
    else:
        if understanding == True:
            if result["text"] == "quit":
                print(f"{RED}\n\nI am now quitting the application! Thank you!")
                sys.exit()

            if result["text"] == "reset" or len(messages) > 100:
                print(f"{YELLOW}\n\n🔄 Conversation reset.")
                messages = []
                understanding = False
                continue

            if result["text"] != "":
                print(f"{GREEN}\n\n👤:", result["text"])

                messages.append({
                    'role': 'user',
                    'content': result["text"],
                })

                response: ChatResponse = chat(model='llama3.2', messages=messages)

                messages.append({
                    'role': 'assistant',
                    'content': response.message.content,
                })

                print(f"{CYAN}\n\n🧠:", response.message.content)
                understanding = False