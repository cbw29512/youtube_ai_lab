"""Optional local Piper TTS integration test.

Skipped in normal CI. Set YOUTUBE_AI_LAB_RUN_LOCAL_TTS_TESTS=1 together with
PIPER_BIN and PIPER_MODEL when testing a trusted local Piper installation.
"""

import os
import subprocess

import pytest

PIPER_BIN = os.environ.get("PIPER_BIN", "")
PIPER_MODEL = os.environ.get("PIPER_MODEL", "")
RUN_LOCAL = os.environ.get("YOUTUBE_AI_LAB_RUN_LOCAL_TTS_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_LOCAL,
    reason="requires opt-in local Piper installation",
)


def test_piper_tts(tmp_path):
    assert PIPER_BIN, "PIPER_BIN is required for the opt-in Piper test"
    assert PIPER_MODEL, "PIPER_MODEL is required for the opt-in Piper test"
    assert os.path.isfile(PIPER_BIN)
    assert os.path.isfile(PIPER_MODEL)

    output_file = tmp_path / "test_output.wav"
    process = subprocess.run(
        [PIPER_BIN, "--model", PIPER_MODEL, "--output_file", str(output_file)],
        input=b"Hello from YouTube AI Lab.",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )

    assert process.returncode == 0, process.stderr.decode(errors="replace")
    assert output_file.exists()
    assert output_file.stat().st_size > 0
