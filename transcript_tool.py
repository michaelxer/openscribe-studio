#!/usr/bin/env python3
"""Transcribe local media files and batches of video URLs.

Requires:
  - ffmpeg on PATH
  - Python packages from requirements.txt
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Event
from typing import Callable, Iterable


MEDIA_EXTENSIONS = {
    ".3gp",
    ".aac",
    ".aiff",
    ".avi",
    ".asf",
    ".flac",
    ".flv",
    ".m4a",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".m2ts",
    ".m2v",
    ".mts",
    ".mxf",
    ".oga",
    ".ogg",
    ".ogv",
    ".opus",
    ".ts",
    ".wav",
    ".webm",
    ".wma",
}


@dataclass
class TranscriptSegment:
    index: int
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    source: str
    title: str
    language: str | None
    language_probability: float | None
    duration_seconds: float | None
    task: str
    model: str
    segments: list[TranscriptSegment]


ProgressCallback = Callable[[float | None, str], None]


class TranscriptionCancelled(RuntimeError):
    """Raised when the user asks to stop the active job."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe local video/audio files and YouTube URL batches.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i",
        "--input",
        nargs="*",
        default=[],
        help="Local media file(s) or folder(s). Folders are scanned recursively.",
    )
    parser.add_argument(
        "-u",
        "--url",
        nargs="*",
        default=[],
        help="Video URL(s), including YouTube links.",
    )
    parser.add_argument(
        "--urls-file",
        help="Text file containing one video URL per line. Blank lines and # comments are ignored.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="transcripts",
        help="Folder for transcript files.",
    )
    parser.add_argument(
        "--model",
        default="small",
        choices=[
            "tiny",
            "base",
            "small",
            "medium",
            "large-v1",
            "large-v2",
            "large-v3",
            "distil-large-v2",
            "distil-large-v3",
        ],
        help="Whisper model size. Larger models are slower but more accurate.",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Source language code like en, id, ja, es. Omit for automatic detection.",
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Translate speech to English instead of transcribing in the original language.",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["md"],
        choices=["md", "txt", "srt", "vtt", "json"],
        help="Output formats to write.",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["auto", "cpu", "cuda"],
        help="Where to run the model.",
    )
    parser.add_argument(
        "--compute-type",
        default="int8",
        help="faster-whisper compute type, for example auto, int8, float16, float32.",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam size for decoding.",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep extracted/downloaded WAV files beside transcripts.",
    )
    parser.add_argument(
        "--cookies",
        help="Optional browser cookie export file for yt-dlp when a site requires login.",
    )
    return parser.parse_args()


def require_ffmpeg() -> None:
    if get_ffmpeg_executable():
        return
    raise SystemExit(
        "ffmpeg was not found.\n"
        "For the portable app, place ffmpeg.exe beside the app or in vendor\\ffmpeg\\bin.\n"
        "Or install it globally, then open a new terminal:\n"
        "  Windows: winget install Gyan.FFmpeg\n"
        "  macOS:   brew install ffmpeg\n"
        "  Linux:   sudo apt install ffmpeg"
    )


def get_app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def create_temp_dir(prefix: str = "run-") -> tempfile.TemporaryDirectory:
    temp_root = get_app_base_dir() / "temp_files"
    temp_root.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(prefix=prefix, dir=temp_root)


def get_ffmpeg_executable() -> str | None:
    executable_name = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"
    base_dir = get_app_base_dir()
    candidates = [
        base_dir / executable_name,
        base_dir / "ffmpeg" / "bin" / executable_name,
        base_dir / "vendor" / "ffmpeg" / "bin" / executable_name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    return shutil.which("ffmpeg")


def import_transcriber():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit(
            "Missing Python dependency: faster-whisper\n"
            "Install dependencies with:\n"
            "  python -m pip install -r requirements.txt"
        ) from exc
    return WhisperModel


def import_ytdlp():
    try:
        import yt_dlp
    except ImportError as exc:
        raise SystemExit(
            "Missing Python dependency: yt-dlp\n"
            "Install dependencies with:\n"
            "  python -m pip install -r requirements.txt"
        ) from exc
    return yt_dlp


def load_urls(args: argparse.Namespace) -> list[str]:
    urls = list(args.url)
    if args.urls_file:
        urls_path = Path(args.urls_file)
        if not urls_path.exists():
            raise SystemExit(f"URL file does not exist: {urls_path}")
        for raw_line in urls_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return dedupe(urls)


def discover_local_media(paths: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if not path.exists():
            raise SystemExit(f"Input path does not exist: {path}")
        if path.is_dir():
            for candidate in path.rglob("*"):
                if candidate.is_file() and candidate.suffix.lower() in MEDIA_EXTENSIONS:
                    files.append(candidate)
        elif path.suffix.lower() in MEDIA_EXTENSIONS:
            files.append(path)
        else:
            print(f"Skipping unsupported file: {path}", file=sys.stderr)
    return dedupe_paths(files)


def dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def dedupe_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            result.append(path)
            seen.add(resolved)
    return result


def safe_stem(value: str, fallback: str = "transcript") -> str:
    cleaned = re.sub(r"[^\w\s.-]+", "", value, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned[:120].strip(" .")
    return cleaned or fallback


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def check_cancelled(cancel_event: Event | None) -> None:
    if cancel_event and cancel_event.is_set():
        raise TranscriptionCancelled("Transcription cancelled.")


def extract_audio(source: Path, destination: Path, cancel_event: Event | None = None) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = get_ffmpeg_executable()
    if not ffmpeg:
        require_ffmpeg()
        ffmpeg = "ffmpeg"
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    process = subprocess.Popen(command)
    try:
        while process.poll() is None:
            check_cancelled(cancel_event)
            try:
                process.wait(timeout=0.25)
            except subprocess.TimeoutExpired:
                pass
    except TranscriptionCancelled:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
        raise
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command)
    return destination


def download_audio(
    url: str,
    audio_dir: Path,
    cookies: str | None,
    progress_callback: ProgressCallback | None = None,
    cancel_event: Event | None = None,
) -> tuple[Path, str]:
    yt_dlp = import_ytdlp()
    audio_dir.mkdir(parents=True, exist_ok=True)

    def progress_hook(status: dict) -> None:
        check_cancelled(cancel_event)
        if not progress_callback:
            return
        downloaded = status.get("downloaded_bytes") or 0
        total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
        if status.get("status") == "downloading" and total:
            progress_callback(min(downloaded / total, 1.0), "Downloading audio")
        elif status.get("status") == "finished":
            progress_callback(1.0, "Converting downloaded audio")
        else:
            progress_callback(None, "Downloading audio")

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(audio_dir / "%(title).120s [%(id)s].%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": False,
        "progress_hooks": [progress_hook],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }
        ],
    }
    if cookies:
        options["cookiefile"] = cookies
    ffmpeg = get_ffmpeg_executable()
    if ffmpeg:
        options["ffmpeg_location"] = ffmpeg

    with yt_dlp.YoutubeDL(options) as ydl:
        check_cancelled(cancel_event)
        info = ydl.extract_info(url, download=True)

    check_cancelled(cancel_event)
    title = info.get("title") or info.get("id") or "downloaded-video"
    requested = info.get("requested_downloads") or []
    for item in requested:
        filepath = item.get("filepath")
        if filepath:
            return Path(filepath), title

    filename = ydl.prepare_filename(info)
    wav_path = Path(filename).with_suffix(".wav")
    if wav_path.exists():
        return wav_path, title
    raise RuntimeError(f"Could not locate downloaded audio for: {url}")


def transcribe_audio(
    model,
    audio_path: Path,
    source: str,
    title: str,
    args: argparse.Namespace,
    progress_callback: ProgressCallback | None = None,
    cancel_event: Event | None = None,
) -> TranscriptResult:
    task = "translate" if args.translate else "transcribe"
    check_cancelled(cancel_event)
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=args.language,
        task=task,
        beam_size=args.beam_size,
        vad_filter=True,
    )
    duration = getattr(info, "duration", None)
    segments = []
    for index, segment in enumerate(segments_iter, start=1):
        check_cancelled(cancel_event)
        segments.append(
            TranscriptSegment(
                index=index,
                start=float(segment.start),
                end=float(segment.end),
                text=segment.text.strip(),
            )
        )
        if progress_callback:
            if duration:
                fraction = min(max(float(segment.end) / float(duration), 0.0), 1.0)
                progress_callback(fraction, f"Transcribing audio ({format_short_time(segment.end)} / {format_short_time(duration)})")
            else:
                progress_callback(None, f"Transcribing audio ({index} segments)")
    if progress_callback:
        progress_callback(1.0, "Transcription complete")
    return TranscriptResult(
        source=source,
        title=title,
        language=getattr(info, "language", None),
        language_probability=getattr(info, "language_probability", None),
        duration_seconds=duration,
        task=task,
        model=args.model,
        segments=segments,
    )


def write_outputs(result: TranscriptResult, output_dir: Path, formats: Iterable[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / safe_stem(result.title)
    if "md" in formats:
        write_markdown(unique_path(base.with_suffix(".md")), result)
    if "txt" in formats:
        write_text(unique_path(base.with_suffix(".txt")), result)
    if "srt" in formats:
        write_srt(unique_path(base.with_suffix(".srt")), result)
    if "vtt" in formats:
        write_vtt(unique_path(base.with_suffix(".vtt")), result)
    if "json" in formats:
        write_json(unique_path(base.with_suffix(".json")), result)


def write_markdown(path: Path, result: TranscriptResult) -> None:
    probability = (
        f"{result.language_probability:.2%}"
        if result.language_probability is not None
        else "unknown"
    )
    lines = [
        f"# {result.title}",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Source | {escape_markdown_table(result.source)} |",
        f"| Language | {escape_markdown_table(result.language or 'unknown')} |",
        f"| Language confidence | {probability} |",
        f"| Task | {result.task} |",
        f"| Model | {result.model} |",
        "",
        "## Transcript",
        "",
    ]
    for segment in result.segments:
        lines.extend(
            [
                f"### {format_vtt_time(segment.start)} - {format_vtt_time(segment.end)}",
                "",
                segment.text,
                "",
            ]
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def escape_markdown_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def write_text(path: Path, result: TranscriptResult) -> None:
    header = [
        f"Title: {result.title}",
        f"Source: {result.source}",
        f"Language: {result.language or 'unknown'}",
        f"Task: {result.task}",
        "",
    ]
    body = [segment.text for segment in result.segments]
    path.write_text("\n".join(header + body) + "\n", encoding="utf-8")


def write_srt(path: Path, result: TranscriptResult) -> None:
    blocks = []
    for segment in result.segments:
        blocks.append(
            "\n".join(
                [
                    str(segment.index),
                    f"{format_srt_time(segment.start)} --> {format_srt_time(segment.end)}",
                    segment.text,
                ]
            )
        )
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def write_vtt(path: Path, result: TranscriptResult) -> None:
    blocks = ["WEBVTT", ""]
    for segment in result.segments:
        blocks.append(
            "\n".join(
                [
                    f"{format_vtt_time(segment.start)} --> {format_vtt_time(segment.end)}",
                    segment.text,
                    "",
                ]
            )
        )
    path.write_text("\n".join(blocks), encoding="utf-8")


def write_json(path: Path, result: TranscriptResult) -> None:
    payload = asdict(result)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def format_srt_time(seconds: float) -> str:
    hours, remainder = divmod(max(seconds, 0), 3600)
    minutes, remainder = divmod(remainder, 60)
    whole_seconds = int(remainder)
    milliseconds = int(round((remainder - whole_seconds) * 1000))
    if milliseconds == 1000:
        whole_seconds += 1
        milliseconds = 0
    return f"{int(hours):02}:{int(minutes):02}:{whole_seconds:02},{milliseconds:03}"


def format_vtt_time(seconds: float) -> str:
    return format_srt_time(seconds).replace(",", ".")


def format_short_time(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:d}:{seconds:02d}"


def run() -> int:
    args = parse_args()
    local_files = discover_local_media(args.input)
    urls = load_urls(args)
    if not local_files and not urls:
        print("No inputs provided. Use --input, --url, or --urls-file.", file=sys.stderr)
        return 2

    require_ffmpeg()
    WhisperModel = import_transcriber()
    output_dir = Path(args.output_dir)
    audio_dir = output_dir / "_audio"
    temp_dir_manager = create_temp_dir(prefix="transcript-tool-")
    temp_dir = Path(temp_dir_manager.name)

    print(f"Loading Whisper model: {args.model}")
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    try:
        jobs: list[tuple[Path, str, str]] = []
        for local_file in local_files:
            stem = safe_stem(local_file.stem)
            audio_path = unique_path((audio_dir if args.keep_audio else temp_dir) / f"{stem}.wav")
            print(f"Extracting audio: {local_file}")
            jobs.append((extract_audio(local_file, audio_path), str(local_file), local_file.stem))

        for url in urls:
            print(f"Downloading audio: {url}")
            audio_path, title = download_audio(url, audio_dir if args.keep_audio else temp_dir, args.cookies)
            jobs.append((audio_path, url, title))

        for audio_path, source, title in jobs:
            print(f"Transcribing: {title}")
            result = transcribe_audio(model, audio_path, source, title, args)
            write_outputs(result, output_dir, args.formats)
            language = result.language or "unknown"
            print(f"Done: {title} ({language}, {len(result.segments)} segments)")
    finally:
        if not args.keep_audio:
            temp_dir_manager.cleanup()

    print(f"Transcripts saved in: {output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
