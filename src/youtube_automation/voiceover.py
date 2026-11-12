"""Voiceover: Piper TTS when available, honest silent track otherwise.

If the ``piper`` binary is installed and a voice model (``.onnx``) is
given, narration is synthesised with Piper. Otherwise a *timed silent
WAV* is generated with the Python standard library: exactly as long as
the narration would take to speak at the given pace. The returned info
dict always states which engine was used — a silent track is never
presented as real speech.
"""

from __future__ import annotations

import shutil
import subprocess
import wave

from .script_builder import DEFAULT_WPM, estimate_duration_seconds

SAMPLE_RATE = 22050


def piper_available() -> bool:
    """True when a ``piper`` executable is on PATH."""
    return shutil.which("piper") is not None


def _write_silence_wav(path: str, duration_seconds: float) -> None:
    """Write a mono 16-bit silent WAV of *duration_seconds* (stdlib only)."""
    frames = max(1, int(duration_seconds * SAMPLE_RATE))
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(b"\x00\x00" * frames)


def wav_duration_seconds(path: str) -> float:
    """Duration of a WAV file in seconds (via the stdlib wave module)."""
    with wave.open(path, "rb") as wav:
        return round(wav.getnframes() / wav.getframerate(), 2)


def generate_voiceover(
    text: str,
    output_path: str,
    wpm: int = DEFAULT_WPM,
    model_path: str | None = None,
    piper_binary: str | None = None,
) -> dict:
    """Generate a voiceover WAV for *text*.

    Uses Piper TTS when the binary is available and *model_path* points
    at a ``.onnx`` voice model; otherwise generates a timed silent track.
    Returns ``{"engine", "path", "duration_seconds", "note"}`` where
    engine is ``"piper"`` or ``"silent"``.
    """
    text = text.strip()
    if not text:
        raise ValueError("text must not be empty")
    duration = estimate_duration_seconds(text, wpm=wpm)

    binary = piper_binary or shutil.which("piper")
    if binary and model_path:
        cmd = [binary, "--model", model_path, "--output_file", output_path]
        proc = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError(
                "Piper TTS failed: " + proc.stderr.decode("utf-8", "replace").strip()
            )
        return {
            "engine": "piper",
            "path": output_path,
            "duration_seconds": wav_duration_seconds(output_path),
            "note": f"Synthesised with Piper using model {model_path}.",
        }

    _write_silence_wav(output_path, duration)
    reason = (
        "Piper TTS is not installed."
        if not binary
        else "No Piper voice model was provided (--model)."
    )
    return {
        "engine": "silent",
        "path": output_path,
        "duration_seconds": wav_duration_seconds(output_path),
        "note": (
            f"{reason} Generated a timed silent track of {duration}s instead "
            "(same length the narration would take to speak). Install Piper "
            "(https://github.com/rhasspy/piper) and pass --model <voice.onnx> "
            "for real speech."
        ),
    }
