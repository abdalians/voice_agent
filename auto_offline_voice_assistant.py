#!/usr/bin/env python3
import os
import subprocess
import sys
import time
import json
import shutil
import platform

# --- CONFIG ---
CONFIG = {
    "vosk_model_path": "~/.local/share/vosk-model-small-en-us",
    "silence_timeout": 3,  # seconds of silence to detect end of speech
    "sample_rate": 16000,
    "ollama_model": "llama2",
    "shellgpt_path": shutil.which("sgpt") or "sgpt",
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
    # Homebrew packages
    for pkg in ["ffmpeg", "jq"]:
        install_brew(pkg)
    # Python packages
    for pkg in CONFIG["python_packages"]:
        install_pip(pkg)
    # Ollama installation
    if shutil.which("ollama") is None:
        print("⬇️ Installing Ollama CLI…")
        if platform.system() == "Darwin":
            run_cmd(["brew", "install", "--cask", "ollama"])
        else:
            print("⚠️ Automatic Ollama install only supported on macOS")
    # Vosk model
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
import sounddevice as sd
import numpy as np

# Load Vosk model
vosk_model_
