#!/usr/bin/env python3
import os
import subprocess
import sys
import time
import json
import shutil
import platform
import sounddevice as sd

# --- CONFIG ---
CONFIG = {
    "vosk_model_path": "~/.local/share/vosk-model-small-en-us",
    "silence_timeout": 3,      # seconds of silence to detect end of speech
    "sample_rate": 16000,
    "ollama_model": "llama2",
    "shellgpt_path": shutil.which("sgpt") or "sgpt",
    "wake_word": "hey jarvis",
    "python_packages": ["vosk", "sounddevice", "numpy", "pyaudio", "shell-gpt"]
}

# === UTILS ===
def run_cmd(cmd, shell=False):
    try:
        subprocess.run(cmd, shell=shell, check=True)
    except Exception as e:
        print(f"Error running command {cmd}: {e}")

# === DEPENDENCY CHECKS & INSTALL ===
def install_brew(pkg):
    if not shutil.which(pkg):
        if not shutil.which("brew"):
            print("🍺 Installing Homebrew…")
            run_cmd(['/bin/bash', '-c', "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"])
        print(f"📦 Installing {pkg} via brew…")
        run_cmd(["brew", "install", pkg])

def install_pip(pkg):
    try:
        __import__(pkg)
    except ImportError:
        print(f"🐍 Installing Python package {pkg}…")
        run_cmd([sys.executable, "-m", "pip", "install", "--user", pkg])

def ensure_dependencies():
    for pkg in ["ffmpeg", "jq"]:
        install_brew(pkg)
    for pkg in CONFIG["python_packages"]:
        install_pip(pkg)
    if shutil.which("ollama") is None:
        print("⬇️ Installing Ollama CLI…")
        if platform.system() == "Darwin":
            run_cmd(["brew", "install", "--cask", "ollama"])
        else:
            print("⚠️ Automatic Ollama install only supported on macOS")
    model_path = os.path.expanduser(CONFIG["vosk_model_path"])
    if not os.path.exists(model_path):
        print("⬇️ Downloading Vosk English model…")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        run_cmd([
            "curl", "-L",
            "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
            "-o", "/tmp/vosk.zip"
        ])
        run_cmd(["unzip", "-o", "/tmp/vosk.zip", "-d", os.path.dirname(model_path)])
        print("✅ Vosk model ready.")

ensure_dependencies()

# === IMPORT AFTER INSTALL ===
from vosk import Model, KaldiRecognizer
import numpy as np

# Load Vosk model
vosk_model_path = os.path.expanduser(CONFIG["vosk_model_path"])
model = Model(vosk_model_path)
recognizer = KaldiRecognizer(model, CONFIG["sample_rate"])

# === VOICE FUNCTIONS ===
def listen_for_wake_word():
    print(f"🟢 Listening for wake word '{CONFIG['wake_word']}'…")
    while True:
        with sd.RawInputStream(
            samplerate=CONFIG["sample_rate"],
            blocksize=8000,
            dtype="int16",
            channels=1,
        ) as stream:
            data = stream.read(4000)[0]
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()
                if CONFIG["wake_word"] in text:
                    print("🟡 Wake word detected!")
                    return

def listen():
    print("🎤 Listening for command…")
    last_voice_time = time.time()

    def callback(indata, frames, time_info, status):
        nonlocal last_voice_time
        if recognizer.AcceptWaveform(indata):
            result = json.loads(recognizer.Result())
            if result.get("text"):
                last_voice_time = time.time()
        else:
            partial = json.loads(recognizer.PartialResult()).get("partial", "")
            if partial:
                last_voice_time = time.time()

    with sd.RawInputStream(
        samplerate=CONFIG["sample_rate"],
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=callback
    ):
        while True:
            if time.time() - last_voice_time > CONFIG["silence_timeout"]:
                result = json.loads(recognizer.FinalResult())
                text = result.get("text", "").strip()
                if text:
                    return text
                else:
                    return None
            time.sleep(0.1)

def speak(text):
    subprocess.run(["say", text])

# === OFFLINE LLM FUNCTIONS ===
def query_local_llm(prompt):
    if shutil.which("ollama") is None:
        return "⚠️ Offline LLM not available. Install Ollama."
    try:
        result = subprocess.check_output(
            ["ollama", "generate", CONFIG["ollama_model"], prompt],
            text=True
        )
        return result.strip()
    except Exception as e:
        return f"Error: {e}"

# === SHELL EXECUTION ===
def execute_shell(prompt):
    if shutil.which(CONFIG["shellgpt_path"]) is None:
        return "⚠️ ShellGPT not installed or path incorrect."
    try:
        output = subprocess.check_output([CONFIG["shellgpt_path"], prompt], text=True)
        return output
    except subprocess.CalledProcessError as e:
        return f"Error executing sgpt: {e}"

# === MAIN LOOP ===
def main():
    print("🟢 Jarvis is ready! Say 'Hey Jarvis' to activate.")
    while True:
        listen_for_wake_word()
        text = listen()
        if not text:
            continue
        print(f"🗣 You said: {text}")

        if "exit" in text.lower() or "quit" in text.lower():
            speak("Goodbye!")
            break

        if "run" in text.lower() or "execute" in text.lower():
            response = execute_shell(text)
        else:
            response = query_local_llm(text)

        print(f"🤖 Jarvis: {response}")
        speak(response)

if __name__ == "__main__":
    main()
