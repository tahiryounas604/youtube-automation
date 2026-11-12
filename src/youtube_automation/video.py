"""Video assembly with ffmpeg.

Slides (PIL images or user photos) become a 1280x720 video with a
Ken Burns slow-zoom (``zoompan``), burned-in captions (``drawtext``),
and the voiceover track mixed in. Slide durations are derived from the
audio length when audio is given, so picture and sound stay in sync.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1280, 720
FPS = 30

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _check_tool(name: str) -> str:
    import shutil

    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required tool '{name}' not found on PATH. Install ffmpeg.")
    return path


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed (exit %d):\n%s" % (proc.returncode, proc.stderr.strip()[-2000:])
        )
    return proc


def probe_duration_seconds(path: str) -> float:
    """Media duration in seconds via ffprobe."""
    _check_tool("ffprobe")
    proc = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", path],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("ffprobe failed on %s: %s" % (path, proc.stderr.strip()[-500:]))
    return float(json.loads(proc.stdout)["format"]["duration"])


def probe_video(path: str) -> dict:
    """Width, height and duration of a video file via ffprobe."""
    _check_tool("ffprobe")
    proc = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-show_format", path],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("ffprobe failed on %s: %s" % (path, proc.stderr.strip()[-500:]))
    data = json.loads(proc.stdout)
    stream = next(s for s in data["streams"] if s["codec_type"] == "video")
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration_seconds": float(data["format"]["duration"]),
    }


def make_slide_image(
    heading: str,
    output_path: str,
    body: str | None = None,
    bg_color: tuple[int, int, int] = (18, 18, 28),
    accent: tuple[int, int, int] = (255, 176, 0),
) -> str:
    """Render a 1280x720 title slide with Pillow. Returns *output_path*."""
    img = Image.new("RGB", (WIDTH, HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, WIDTH, 14], fill=accent)
    draw.rectangle([0, HEIGHT - 14, WIDTH, HEIGHT], fill=accent)
    try:
        title_font = ImageFont.truetype(FONT_BOLD, 72)
        body_font = ImageFont.truetype(FONT_REGULAR, 40)
    except OSError:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    # Simple word wrap for the heading.
    words = heading.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = (current + " " + word).strip()
        if draw.textlength(trial, font=title_font) <= WIDTH - 160:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    lines = lines[:3]

    line_h = 90
    y = (HEIGHT - line_h * len(lines)) // 2 - (50 if body else 0)
    for line in lines:
        draw.text((80, y), line, font=title_font, fill=(255, 255, 255))
        y += line_h
    if body:
        draw.text((80, y + 20), body, font=body_font, fill=(200, 200, 200))
    img.save(output_path, "PNG")
    return output_path


def assemble_video(
    slide_paths: list[str],
    output_path: str,
    audio_path: str | None = None,
    captions: list[dict] | None = None,
    slide_duration: float = 5.0,
    fps: int = FPS,
) -> dict:
    """Assemble slides + optional audio + captions into an MP4.

    Each slide gets a slow Ken Burns zoom (``zoompan``). When
    *audio_path* is given, the total slide time is stretched to match
    the audio length. *captions* is a list of ``{"start", "end",
    "text"}`` dicts burned in with drawtext. Returns ``{"path",
    "duration_seconds", "width", "height"}`` (verified with ffprobe).
    """
    _check_tool("ffmpeg")
    if not slide_paths:
        raise ValueError("at least one slide image is required")
    for path in slide_paths:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"slide image not found: {path}")
    if audio_path and not os.path.isfile(audio_path):
        raise FileNotFoundError(f"audio file not found: {audio_path}")
    if slide_duration <= 0:
        raise ValueError("slide_duration must be positive")

    if audio_path:
        total = probe_duration_seconds(audio_path)
        per_slide = total / len(slide_paths)
    else:
        per_slide = slide_duration
        total = per_slide * len(slide_paths)
    frames_per_slide = max(1, int(round(per_slide * fps)))

    cmd: list[str] = ["ffmpeg", "-y"]
    for slide in slide_paths:
        cmd += ["-i", slide]
    if audio_path:
        cmd += ["-i", audio_path]

    # Ken Burns zoompan per slide (input is a single still frame).
    filter_parts: list[str] = []
    for i in range(len(slide_paths)):
        filter_parts.append(
            f"[{i}:v]scale={WIDTH * 2}:{HEIGHT * 2},"
            f"zoompan=z='min(zoom+0.0008,1.12)':d={frames_per_slide}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={WIDTH}x{HEIGHT}:fps={fps},"
            f"format=yuv420p[v{i}]"
        )
    concat_inputs = "".join(f"[v{i}]" for i in range(len(slide_paths)))
    filter_parts.append(f"{concat_inputs}concat=n={len(slide_paths)}:v=1:a=0,format=yuv420p[v]")

    # Burned-in captions via drawtext + per-caption text files (avoids
    # shell/filter escaping problems with arbitrary caption text).
    last_label = "v"
    with tempfile.TemporaryDirectory(prefix="ytcap_") as tmpdir:
        for j, cap in enumerate(captions or []):
            text_path = os.path.join(tmpdir, f"cap{j}.txt")
            with open(text_path, "w", encoding="utf-8") as fh:
                fh.write(cap["text"])
            out_label = f"vc{j}"
            filter_parts.append(
                f"[{last_label}]drawtext=fontfile={FONT_REGULAR}:"
                f"textfile='{text_path}':fontsize=40:fontcolor=white:"
                f"borderw=2:bordercolor=black:x=(w-text_w)/2:y=h-110:"
                f"enable='between(t,{float(cap['start']):.2f},{float(cap['end']):.2f})'"
                f"[{out_label}]"
            )
            last_label = out_label

        filtergraph = ";".join(filter_parts)
        cmd += ["-filter_complex", filtergraph, "-map", f"[{last_label}]"]
        if audio_path:
            cmd += ["-map", f"{len(slide_paths)}:a", "-c:a", "aac", "-shortest"]
        cmd += [
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps),
            "-movflags", "+faststart", output_path,
        ]
        _run(cmd)

    info = probe_video(output_path)
    return {"path": output_path, **info}
