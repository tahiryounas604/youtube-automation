"""Command-line interface for youtube-automation.

Subcommands: script, voice, thumb, meta, assemble, queue, upload, pipeline.
Run ``python -m youtube_automation --help`` for usage.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .metadata import generate_metadata
from .queue import Queue
from .script_builder import build_captions, build_script, load_outline
from .thumbnail import make_thumbnail
from .uploader import upload_video
from .video import assemble_video, make_slide_image
from .voiceover import generate_voiceover


def _write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    print(f"Wrote {path}")


def _cmd_script(args: argparse.Namespace) -> int:
    outline = load_outline(args.outline)
    script = build_script(
        outline["topic"],
        outline["sections"],
        style=outline.get("style", "educational"),
    )
    _write_json(args.output, script)
    print(f"Topic: {script['topic']}")
    print(f"Words: {script['word_count']} | "
          f"Est. duration: {script['estimated_duration_seconds']}s")
    return 0


def _cmd_voice(args: argparse.Namespace) -> int:
    with open(args.script, "r", encoding="utf-8") as fh:
        script = json.load(fh)
    result = generate_voiceover(
        script["narration"], args.output, model_path=args.model
    )
    print(f"Engine: {result['engine']} ({result['duration_seconds']}s)")
    print(result["note"])
    return 0


def _cmd_thumb(args: argparse.Namespace) -> int:
    result = make_thumbnail(args.title, args.output,
                            subtitle=args.subtitle, gradient=args.gradient)
    print(f"Thumbnail: {result['path']} {result['size']}")
    return 0


def _cmd_meta(args: argparse.Namespace) -> int:
    script = None
    if args.script:
        with open(args.script, "r", encoding="utf-8") as fh:
            script = json.load(fh)
    meta = generate_metadata(args.topic, script, channel_name=args.channel)
    _write_json(args.output, meta)
    print(f"Title: {meta['title']}")
    print(f"Tags ({len(meta['tags'])}): {', '.join(meta['tags'])}")
    return 0


def _cmd_assemble(args: argparse.Namespace) -> int:
    captions = None
    if args.captions:
        with open(args.captions, "r", encoding="utf-8") as fh:
            captions = json.load(fh)
    result = assemble_video(
        args.slides, args.output, audio_path=args.audio,
        captions=captions, slide_duration=args.slide_duration,
    )
    print(f"Video: {result['path']} {result['width']}x{result['height']} "
          f"({result['duration_seconds']:.2f}s)")
    return 0


def _cmd_queue(args: argparse.Namespace) -> int:
    queue = Queue(args.queue)
    if args.action == "add":
        entry = queue.add(args.topic, args.video, args.when)
        print(f"Queued {entry['id']}: {entry['topic']} @ {entry['scheduled_at']}")
    elif args.action == "list":
        for entry in queue.list_all(status=args.status):
            print(f"{entry['id']} [{entry['status']}] {entry['scheduled_at']} "
                  f"{entry['topic']} -> {entry['video_path']}")
    elif args.action == "due":
        for entry in queue.due(now=args.now):
            print(f"{entry['id']} DUE {entry['scheduled_at']} {entry['topic']}")
    elif args.action == "done":
        queue.update_status(args.id, "done", note=args.note or "")
        print(f"{args.id} marked done")
    elif args.action == "failed":
        queue.update_status(args.id, "failed", note=args.note or "")
        print(f"{args.id} marked failed")
    elif args.action == "remove":
        print("Removed" if queue.remove(args.id) else "Not found")
    return 0


def _cmd_upload(args: argparse.Namespace) -> int:
    result = upload_video(
        args.video, args.title, args.description,
        tags=args.tags, privacy_status=args.privacy,
        credentials_path=args.credentials, token_path=args.token,
        thumbnail_path=args.thumbnail,
    )
    print(f"Uploaded: {result['url']}")
    return 0


def _cmd_pipeline(args: argparse.Namespace) -> int:
    """End to end: outline -> script -> voice -> slides -> video -> thumb -> meta."""
    os.makedirs(args.outdir, exist_ok=True)
    outline = load_outline(args.outline)
    script = build_script(outline["topic"], outline["sections"],
                          style=outline.get("style", "educational"))
    script_path = os.path.join(args.outdir, "script.json")
    _write_json(script_path, script)

    audio_path = os.path.join(args.outdir, "voiceover.wav")
    voice = generate_voiceover(script["narration"], audio_path, model_path=args.model)
    print(f"Voiceover: {voice['engine']} ({voice['duration_seconds']}s)")
    print(voice["note"])

    captions = build_captions(script["narration"])
    captions_path = os.path.join(args.outdir, "captions.json")
    _write_json(captions_path, {"captions": captions})

    slide_paths = []
    for i, section in enumerate(script["sections"]):
        slide = os.path.join(args.outdir, f"slide_{i + 1}.png")
        make_slide_image(section["heading"], slide, body=script["topic"])
        slide_paths.append(slide)

    video_path = os.path.join(args.outdir, "video.mp4")
    video = assemble_video(slide_paths, video_path, audio_path=audio_path,
                           captions=captions)
    print(f"Video: {video['path']} {video['width']}x{video['height']} "
          f"({video['duration_seconds']:.2f}s)")

    thumb_path = os.path.join(args.outdir, "thumbnail.png")
    make_thumbnail(script["topic"], thumb_path, subtitle="Explained Simply")

    meta = generate_metadata(script["topic"], script, channel_name=args.channel)
    meta_path = os.path.join(args.outdir, "metadata.json")
    _write_json(meta_path, meta)

    if args.schedule:
        queue = Queue(args.queue)
        entry = queue.add(script["topic"], video_path, args.schedule,
                          metadata_path=meta_path)
        print(f"Queued {entry['id']} for {args.schedule}")
    print(f"Done. Outputs in {args.outdir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="youtube-automation",
        description="Faceless YouTube channel pipeline: script, voice, video, SEO, upload.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("script", help="Build a narration script from an outline JSON.")
    p.add_argument("outline", help="Outline JSON file (topic + sections).")
    p.add_argument("-o", "--output", default="script.json")
    p.set_defaults(func=_cmd_script)

    p = sub.add_parser("voice", help="Generate a voiceover WAV from a script JSON.")
    p.add_argument("script", help="Script JSON file (from `script`).")
    p.add_argument("-o", "--output", default="voiceover.wav")
    p.add_argument("--model", default=None, help="Piper voice model (.onnx).")
    p.set_defaults(func=_cmd_voice)

    p = sub.add_parser("thumb", help="Generate a 1280x720 thumbnail PNG.")
    p.add_argument("title")
    p.add_argument("-o", "--output", default="thumbnail.png")
    p.add_argument("--subtitle", default=None)
    p.add_argument("--gradient", default="dark",
                   choices=["dark", "ocean", "ember", "forest"])
    p.set_defaults(func=_cmd_thumb)

    p = sub.add_parser("meta", help="Generate title/description/tags.")
    p.add_argument("topic")
    p.add_argument("--script", default=None, help="Script JSON for better tags.")
    p.add_argument("--channel", default=None)
    p.add_argument("-o", "--output", default="metadata.json")
    p.set_defaults(func=_cmd_meta)

    p = sub.add_parser("assemble", help="Assemble slides + audio into an MP4.")
    p.add_argument("slides", nargs="+", help="Slide image files (PNG/JPG).")
    p.add_argument("-o", "--output", default="video.mp4")
    p.add_argument("--audio", default=None, help="Voiceover WAV.")
    p.add_argument("--captions", default=None, help="Captions JSON file.")
    p.add_argument("--slide-duration", type=float, default=5.0)
    p.set_defaults(func=_cmd_assemble)

    p = sub.add_parser("queue", help="Scheduling queue (JSON file).")
    p.add_argument("--queue", default="queue.json")
    p.add_argument("action", choices=["add", "list", "due", "done", "failed", "remove"])
    p.add_argument("--topic", default=None)
    p.add_argument("--video", default=None)
    p.add_argument("--when", default=None, help="ISO-8601 scheduled time.")
    p.add_argument("--id", default=None)
    p.add_argument("--status", default=None)
    p.add_argument("--now", default=None)
    p.add_argument("--note", default=None)
    p.set_defaults(func=_cmd_queue)

    p = sub.add_parser("upload", help="Upload a video via YouTube Data API v3.")
    p.add_argument("video")
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--tags", nargs="*", default=[])
    p.add_argument("--privacy", default="private",
                   choices=["private", "unlisted", "public"])
    p.add_argument("--credentials", default="client_secrets.json")
    p.add_argument("--token", default="token.json")
    p.add_argument("--thumbnail", default=None)
    p.set_defaults(func=_cmd_upload)

    p = sub.add_parser("pipeline", help="Run the full pipeline from an outline JSON.")
    p.add_argument("outline")
    p.add_argument("-o", "--outdir", default="output")
    p.add_argument("--model", default=None, help="Piper voice model (.onnx).")
    p.add_argument("--channel", default=None)
    p.add_argument("--schedule", default=None, help="ISO-8601 time to queue the video.")
    p.add_argument("--queue", default="queue.json")
    p.set_defaults(func=_cmd_pipeline)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError, KeyError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
