import os
import subprocess

# Make sure Python can find ffmpeg
os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

# Quick check
subprocess.run(["ffmpeg", "-version"], check=True)

import whisper

print("Loading model...")
model = whisper.load_model("tiny")

print("Transcribing...")
result = model.transcribe("test.ogg")

print("Result:")
print(result["text"])
