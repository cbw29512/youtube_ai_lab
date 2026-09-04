"""Optional local Ollama integration tests.

These tests are skipped in normal CI. Set YOUTUBE_AI_LAB_RUN_LOCAL_AI_TESTS=1
when a trusted local Ollama service is available.
"""

import os

import pytest
import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b-instruct-q4_0")
RUN_LOCAL = os.environ.get("YOUTUBE_AI_LAB_RUN_LOCAL_AI_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_LOCAL,
    reason="requires opt-in local Ollama service",
)


def test_ollama_connection():
    response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
    response.raise_for_status()
    payload = response.json()
    assert isinstance(payload.get("models", []), list)


def test_ollama_generate():
    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": "Write a short title about testing AI limits.",
            "stream": False,
        },
        timeout=30,
    )
    response.raise_for_status()
    generated = response.json().get("response", "").strip()
    assert generated
