#!/usr/bin/env python3
"""Desktop UI for OpenScribe Studio."""

from __future__ import annotations

import os
import platform
import json
import queue
import re
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from transcript_tool import (
    MEDIA_EXTENSIONS,
    TranscriptionCancelled,
    check_cancelled,
    create_temp_dir,
    discover_local_media,
    download_audio,
    extract_audio,
    format_short_time,
    get_app_base_dir,
    get_ffmpeg_executable,
    import_transcriber,
    require_ffmpeg,
    safe_stem,
    transcribe_audio,
    unique_path,
    write_outputs,
)

APP_NAME = "OpenScribe Studio"
APP_VERSION = "0.2.0"
APP_TAGLINE = "Local-first video and audio transcription"
GITHUB_URL = "https://github.com/michaelxer/openscribe-studio"
LATEST_RELEASE_API = "https://api.github.com/repos/michaelxer/openscribe-studio/releases/latest"


LANGUAGES = {
    "Auto detect": None,
    "English (en)": "en",
    "Indonesian (id)": "id",
    "Malay (ms)": "ms",
    "Filipino / Tagalog (tl)": "tl",
    "Chinese (zh)": "zh",
    "Japanese (ja)": "ja",
    "Korean (ko)": "ko",
    "Thai (th)": "th",
    "Vietnamese (vi)": "vi",
    "Hindi (hi)": "hi",
    "Arabic (ar)": "ar",
    "Spanish (es)": "es",
    "Portuguese (pt)": "pt",
    "French (fr)": "fr",
    "German (de)": "de",
    "Italian (it)": "it",
    "Dutch (nl)": "nl",
    "Turkish (tr)": "tr",
    "Russian (ru)": "ru",
}


MODELS = [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3",
    "distil-large-v3",
]


APP_BG = "#0b1120"
PANEL_BG = "#111827"
FIELD_BG = "#0f172a"
SURFACE_BG = "#1f2937"
BORDER = "#334155"
TEXT = "#e5e7eb"
MUTED = "#94a3b8"
ACCENT = "#38bdf8"
ACCENT_DARK = "#0284c7"
SELECT_TEXT = "#06121f"

CUDA_RUNTIME_HINTS = (
    "cublas",
    "cudnn",
    "cuda",
    "cufft",
    "curand",
)


class TranscriptApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1240x860")
        self.minsize(1080, 760)

        self.message_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.running = False
        self.cancel_event = threading.Event()
        self.job_started_at: float | None = None

        self.output_dir = tk.StringVar(value=str(Path.cwd() / "transcripts"))
        self.model = tk.StringVar(value="small")
        self.language = tk.StringVar(value="Auto detect")
        self.device = tk.StringVar(value="cpu")
        self.compute_type = tk.StringVar(value="int8")
        self.translate = tk.BooleanVar(value=False)
        self.keep_audio = tk.BooleanVar(value=False)
        self.cookies = tk.StringVar(value="")
        self.progress = tk.DoubleVar(value=0)
        self.progress_text = tk.StringVar(value="Idle - 0%")
        self.progress_detail = tk.StringVar(value="Ready to transcribe.")
        self.progress_meta = tk.StringVar(value="ETA --")
        self.status = tk.StringVar(value=self.ffmpeg_status_text())
        self.format_vars = {
            "md": tk.BooleanVar(value=True),
            "srt": tk.BooleanVar(value=True),
            "json": tk.BooleanVar(value=False),
            "txt": tk.BooleanVar(value=False),
            "vtt": tk.BooleanVar(value=False),
        }

        self.configure(bg=APP_BG)
        self.option_add("*TCombobox*Listbox.background", FIELD_BG)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.option_add("*TCombobox*Listbox.selectForeground", SELECT_TEXT)
        self.create_styles()
        self.create_widgets()
        self.after(120, self.poll_queue)

    def create_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            ".",
            font=("Segoe UI", 10),
            background=APP_BG,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=SURFACE_BG,
            darkcolor=APP_BG,
        )
        style.configure("TFrame", background=APP_BG)
        style.configure("Panel.TFrame", background=PANEL_BG, relief="solid", borderwidth=1, bordercolor=BORDER)
        style.configure("TLabel", background=APP_BG, foreground=TEXT)
        style.configure("Panel.TLabel", background=PANEL_BG, foreground=TEXT)
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 18), background=APP_BG, foreground=TEXT)
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), background=APP_BG, foreground=MUTED)
        style.configure("Muted.TLabel", foreground=MUTED, background=APP_BG)
        style.configure("PanelMuted.TLabel", foreground=MUTED, background=PANEL_BG)
        style.configure("ProgressTitle.TLabel", font=("Segoe UI Semibold", 11), background=PANEL_BG, foreground=TEXT)
        style.configure(
            "TButton",
            padding=(12, 7),
            background=SURFACE_BG,
            foreground=TEXT,
            bordercolor=BORDER,
            focuscolor=BORDER,
        )
        style.map(
            "TButton",
            background=[("active", "#263548"), ("disabled", "#172033")],
            foreground=[("disabled", "#64748b")],
        )
        style.configure("Accent.TButton", padding=(16, 9), background=ACCENT_DARK, foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#0369a1"), ("disabled", "#164e63")])
        style.configure("Danger.TButton", padding=(16, 9), background="#7f1d1d", foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#991b1b"), ("disabled", "#3f1f24")])
        style.configure(
            "TEntry",
            fieldbackground=FIELD_BG,
            foreground=TEXT,
            insertcolor=TEXT,
            bordercolor=BORDER,
            lightcolor=SURFACE_BG,
            darkcolor=APP_BG,
        )
        style.configure(
            "TCombobox",
            fieldbackground=FIELD_BG,
            background=SURFACE_BG,
            foreground=TEXT,
            arrowcolor=TEXT,
            bordercolor=BORDER,
            lightcolor=SURFACE_BG,
            darkcolor=APP_BG,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", FIELD_BG)],
            foreground=[("readonly", TEXT)],
            selectbackground=[("readonly", FIELD_BG)],
            selectforeground=[("readonly", TEXT)],
        )
        style.configure("TCheckbutton", background=PANEL_BG, foreground=TEXT, focuscolor=BORDER)
        style.map(
            "TCheckbutton",
            background=[("active", PANEL_BG), ("disabled", PANEL_BG)],
            foreground=[("disabled", "#64748b"), ("active", TEXT)],
        )
        style.configure("Horizontal.TProgressbar", troughcolor=FIELD_BG, background=ACCENT, bordercolor=BORDER)

    def create_widgets(self) -> None:
        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        root.rowconfigure(2, weight=0)
        root.rowconfigure(3, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        brand = ttk.Frame(header)
        brand.pack(side="left")
        ttk.Label(brand, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(brand, text=APP_TAGLINE, style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))
        ttk.Label(
            header,
            textvariable=self.status,
            style="Muted.TLabel",
        ).pack(side="right", padx=(12, 0))
        ttk.Button(header, text="Project", command=lambda: webbrowser.open(GITHUB_URL)).pack(side="right", padx=(8, 0))
        ttk.Button(header, text="Updates", command=self.check_for_updates).pack(side="right", padx=(8, 0))
        ttk.Button(header, text="Guide", command=self.open_user_guide).pack(side="right")

        body = ttk.Frame(root)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=3, uniform="body")
        body.columnconfigure(1, weight=2, uniform="body")
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, style="Panel.TFrame", padding=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(1, weight=1)
        left.rowconfigure(4, weight=1)
        left.columnconfigure(0, weight=1)

        right = ttk.Frame(body, style="Panel.TFrame", padding=14)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right.columnconfigure(1, weight=1)

        self.create_source_panel(left)
        self.create_settings_panel(right)
        self.create_progress_panel(root)
        self.create_log_panel(root)

    def create_source_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Local files and folders", style="Panel.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.local_list = tk.Listbox(
            parent,
            height=8,
            activestyle="none",
            selectmode="extended",
            bg=FIELD_BG,
            fg=TEXT,
            selectbackground=ACCENT,
            selectforeground=SELECT_TEXT,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            relief="flat",
        )
        self.local_list.grid(row=1, column=0, sticky="nsew", pady=(8, 10))

        file_buttons = ttk.Frame(parent, style="Panel.TFrame")
        file_buttons.grid(row=2, column=0, sticky="ew", pady=(0, 18))
        ttk.Button(file_buttons, text="Add files", command=self.add_files).pack(side="left")
        ttk.Button(file_buttons, text="Add folder", command=self.add_folder).pack(side="left", padx=8)
        ttk.Button(file_buttons, text="Remove", command=self.remove_selected_files).pack(side="left")
        ttk.Button(file_buttons, text="Clear", command=self.clear_files).pack(side="left", padx=8)

        ttk.Label(parent, text="YouTube or video URLs", style="Panel.TLabel").grid(
            row=3, column=0, sticky="w"
        )
        self.url_text = tk.Text(
            parent,
            height=8,
            wrap="none",
            bg=FIELD_BG,
            fg=TEXT,
            insertbackground=TEXT,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            relief="flat",
            font=("Consolas", 10),
        )
        self.url_text.grid(row=4, column=0, sticky="nsew", pady=(8, 10))

        url_buttons = ttk.Frame(parent, style="Panel.TFrame")
        url_buttons.grid(row=5, column=0, sticky="ew")
        ttk.Button(url_buttons, text="Load URL file", command=self.load_url_file).pack(side="left")
        ttk.Button(url_buttons, text="Clear URLs", command=lambda: self.url_text.delete("1.0", "end")).pack(
            side="left", padx=8
        )

    def create_settings_panel(self, parent: ttk.Frame) -> None:
        row = 0
        ttk.Label(parent, text="Output folder", style="Panel.TLabel").grid(row=row, column=0, sticky="w")
        output = ttk.Entry(parent, textvariable=self.output_dir)
        output.grid(row=row + 1, column=0, columnspan=2, sticky="ew", pady=(8, 8))
        ttk.Button(parent, text="Browse", command=self.choose_output_dir).grid(
            row=row + 1, column=2, sticky="ew", padx=(8, 0), pady=(8, 8)
        )

        row += 2
        ttk.Label(parent, text="Language", style="Panel.TLabel").grid(
            row=row, column=0, sticky="w", pady=(8, 4)
        )
        language = ttk.Combobox(
            parent,
            textvariable=self.language,
            values=list(LANGUAGES.keys()),
            state="readonly",
        )
        language.grid(row=row + 1, column=0, columnspan=3, sticky="ew")

        row += 2
        ttk.Label(parent, text="Model", style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=(12, 4))
        ttk.Combobox(parent, textvariable=self.model, values=MODELS, state="readonly").grid(
            row=row + 1, column=0, columnspan=3, sticky="ew"
        )

        row += 2
        ttk.Label(parent, text="Performance", style="Panel.TLabel").grid(
            row=row, column=0, sticky="w", pady=(12, 4)
        )
        ttk.Combobox(parent, textvariable=self.device, values=["auto", "cpu", "cuda"], state="readonly").grid(
            row=row + 1, column=0, sticky="ew"
        )
        ttk.Combobox(
            parent,
            textvariable=self.compute_type,
            values=["auto", "int8", "float16", "float32"],
            state="readonly",
        ).grid(row=row + 1, column=1, columnspan=2, sticky="ew", padx=(8, 0))

        row += 2
        ttk.Label(parent, text="Outputs", style="Panel.TLabel").grid(
            row=row, column=0, sticky="w", pady=(12, 4)
        )
        format_frame = ttk.Frame(parent, style="Panel.TFrame")
        format_frame.grid(row=row + 1, column=0, columnspan=3, sticky="ew")
        for index, (format_name, variable) in enumerate(self.format_vars.items()):
            ttk.Checkbutton(format_frame, text=format_name.upper(), variable=variable).grid(
                row=index // 3, column=index % 3, sticky="w", padx=(0, 16), pady=2
            )

        row += 2
        ttk.Checkbutton(
            parent,
            text="Translate speech to English",
            variable=self.translate,
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(12, 2))
        ttk.Checkbutton(parent, text="Keep extracted audio", variable=self.keep_audio).grid(
            row=row + 1, column=0, columnspan=3, sticky="w", pady=2
        )

        row += 2
        ttk.Label(parent, text="Cookies file for protected videos", style="Panel.TLabel").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(12, 4)
        )
        ttk.Entry(parent, textvariable=self.cookies).grid(row=row + 1, column=0, columnspan=2, sticky="ew")
        ttk.Button(parent, text="Browse", command=self.choose_cookies).grid(
            row=row + 1, column=2, sticky="ew", padx=(8, 0)
        )

        self.start_button = ttk.Button(parent, text="Start transcription", style="Accent.TButton", command=self.start)
        self.start_button.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(22, 0))
        self.cancel_button = ttk.Button(
            parent,
            text="Cancel",
            style="Danger.TButton",
            command=self.cancel,
            state="disabled",
        )
        self.cancel_button.grid(row=row, column=2, sticky="ew", padx=(8, 0), pady=(22, 0))
        ttk.Button(parent, text="Open output folder", command=self.open_output_folder).grid(
            row=row + 1, column=0, columnspan=3, sticky="ew", pady=(8, 0)
        )

    def create_progress_panel(self, parent: ttk.Frame) -> None:
        progress_frame = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        progress_frame.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.columnconfigure(1, weight=0)
        ttk.Label(progress_frame, textvariable=self.progress_text, style="ProgressTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(progress_frame, textvariable=self.progress_meta, style="PanelMuted.TLabel").grid(
            row=0, column=1, sticky="e"
        )
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress, maximum=100)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 6))
        ttk.Label(progress_frame, textvariable=self.progress_detail, style="PanelMuted.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w"
        )

    def create_log_panel(self, parent: ttk.Frame) -> None:
        log_frame = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(14, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)
        ttk.Label(log_frame, text="Activity", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.log_text = tk.Text(
            log_frame,
            height=7,
            bg="#050816",
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            wrap="word",
            font=("Consolas", 10),
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.log("Ready. Add local media files, paste URLs, then start transcription.")

    def add_files(self) -> None:
        extensions = " ".join(f"*{ext}" for ext in sorted(MEDIA_EXTENSIONS))
        paths = filedialog.askopenfilenames(
            title="Choose video or audio files",
            filetypes=[("Media files", extensions), ("All files", "*.*")],
        )
        self.add_local_paths(paths)

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose folder with media files")
        if folder:
            self.add_local_paths([folder])

    def add_local_paths(self, paths: tuple[str, ...] | list[str]) -> None:
        existing = set(self.local_list.get(0, "end"))
        for path in paths:
            if path not in existing:
                self.local_list.insert("end", path)
                existing.add(path)

    def remove_selected_files(self) -> None:
        for index in reversed(self.local_list.curselection()):
            self.local_list.delete(index)

    def clear_files(self) -> None:
        self.local_list.delete(0, "end")

    def load_url_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose URL list",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        content = Path(path).read_text(encoding="utf-8")
        if self.url_text.get("1.0", "end").strip():
            self.url_text.insert("end", "\n")
        self.url_text.insert("end", content.strip() + "\n")

    def choose_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="Choose output folder")
        if folder:
            self.output_dir.set(folder)

    def choose_cookies(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose cookies.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.cookies.set(path)

    def open_output_folder(self) -> None:
        folder = Path(self.output_dir.get()).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        if platform.system() == "Windows":
            os.startfile(folder)
        elif platform.system() == "Darwin":
            os.system(f'open "{folder}"')
        else:
            webbrowser.open(folder.as_uri())

    def open_user_guide(self) -> None:
        app_base = get_app_base_dir()
        guide_candidates = [
            app_base / "USER_GUIDE.md",
            app_base.parent / "Resources" / "USER_GUIDE.md",
            Path(__file__).resolve().with_name("USER_GUIDE.md"),
        ]
        guide_path = next((path for path in guide_candidates if path.exists()), guide_candidates[0])
        if guide_path.exists():
            if platform.system() == "Windows":
                os.startfile(guide_path)
            elif platform.system() == "Darwin":
                os.system(f'open "{guide_path}"')
            else:
                webbrowser.open(guide_path.as_uri())
        else:
            webbrowser.open(GITHUB_URL)

    def check_for_updates(self) -> None:
        self.log("Checking GitHub for updates...")
        thread = threading.Thread(target=self.update_check_worker, daemon=True)
        thread.start()

    def update_check_worker(self) -> None:
        try:
            request = urllib.request.Request(
                LATEST_RELEASE_API,
                headers={"Accept": "application/vnd.github+json", "User-Agent": APP_NAME},
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
            latest = str(payload.get("tag_name") or "").lstrip("v")
            release_url = str(payload.get("html_url") or GITHUB_URL)
            if latest and version_tuple(latest) > version_tuple(APP_VERSION):
                self.post("update_available", {"version": latest, "url": release_url})
            else:
                self.post("log", f"{APP_NAME} is up to date.")
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
            self.post("log", f"Could not check updates: {exc}")

    def start(self) -> None:
        if self.running:
            return

        local_inputs = list(self.local_list.get(0, "end"))
        urls = self.parse_urls()
        formats = [name for name, variable in self.format_vars.items() if variable.get()]
        if not formats:
            formats = ["md"]
            self.format_vars["md"].set(True)
        if not local_inputs and not urls:
            messagebox.showwarning("No sources", "Add local files/folders or paste at least one video URL.")
            return

        self.running = True
        self.cancel_event.clear()
        self.job_started_at = time.monotonic()
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.set(0)
        self.progress_text.set("Starting - 0%")
        self.progress_detail.set("Preparing job...")
        self.progress_meta.set("ETA calculating")
        self.log("Starting job...")

        thread = threading.Thread(
            target=self.worker,
            args=(local_inputs, urls, formats),
            daemon=True,
        )
        thread.start()

    def cancel(self) -> None:
        if not self.running:
            return
        self.cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.progress_detail.set("Cancel requested. Stopping as soon as the active step allows.")
        self.log("Cancel requested. Waiting for the active step to stop...")

    def parse_urls(self) -> list[str]:
        urls = []
        for raw_line in self.url_text.get("1.0", "end").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
        seen = set()
        return [url for url in urls if not (url in seen or seen.add(url))]

    def worker(self, local_inputs: list[str], urls: list[str], formats: list[str]) -> None:
        try:
            require_ffmpeg()
            WhisperModel = import_transcriber()
            local_files = discover_local_media(local_inputs)
            if not local_files and not urls:
                raise RuntimeError("No supported media files or URLs were found.")

            output_dir = Path(self.output_dir.get()).expanduser()
            output_dir.mkdir(parents=True, exist_ok=True)
            audio_dir = output_dir / "_audio"
            language_code = LANGUAGES.get(self.language.get())
            cookies = self.cookies.get().strip() or None
            args = SimpleNamespace(
                model=self.model.get(),
                language=language_code,
                translate=self.translate.get(),
                formats=formats,
                device=self.device.get(),
                compute_type=self.compute_type.get(),
                beam_size=5,
                keep_audio=self.keep_audio.get(),
                cookies=cookies,
            )

            total = len(local_files) + len(urls)
            done = 0
            self.post_progress(0, "Loading model", f"Loading Whisper model: {args.model}")
            self.post("log", f"Loading Whisper model: {args.model}")
            model = self.load_model(WhisperModel, args)

            temp_dir_manager = create_temp_dir(prefix="transcript-studio-")
            temp_dir = Path(temp_dir_manager.name)
            try:
                for local_file in local_files:
                    check_cancelled(self.cancel_event)
                    stem = safe_stem(local_file.stem)
                    audio_path = unique_path((audio_dir if args.keep_audio else temp_dir) / f"{stem}.wav")
                    self.post_job_progress(done, total, 0.03, "Extracting audio", local_file.name)
                    self.post("log", f"Extracting audio: {local_file}")
                    extracted = extract_audio(local_file, audio_path, self.cancel_event)
                    model = self.process_with_fallback(
                        WhisperModel,
                        model,
                        extracted,
                        str(local_file),
                        local_file.stem,
                        output_dir,
                        args,
                        done,
                        total,
                    )
                    done += 1
                    self.post_job_progress(done, total, 0, "Completed source", local_file.name)

                for url in urls:
                    check_cancelled(self.cancel_event)
                    self.post("log", f"Downloading audio: {url}")
                    self.post_job_progress(done, total, 0.02, "Starting download", url)

                    def download_progress(fraction: float | None, phase: str, source_url: str = url) -> None:
                        job_fraction = 0.18 if fraction is None else 0.02 + min(max(fraction, 0.0), 1.0) * 0.18
                        self.post_job_progress(done, total, job_fraction, phase, source_url)

                    audio_path, title = download_audio(
                        url,
                        audio_dir if args.keep_audio else temp_dir,
                        cookies,
                        download_progress,
                        self.cancel_event,
                    )
                    model = self.process_with_fallback(
                        WhisperModel,
                        model,
                        audio_path,
                        url,
                        title,
                        output_dir,
                        args,
                        done,
                        total,
                    )
                    done += 1
                    self.post_job_progress(done, total, 0, "Completed source", title)
            finally:
                if not args.keep_audio:
                    temp_dir_manager.cleanup()

            self.post("done", True)
        except TranscriptionCancelled as exc:
            self.post("cancelled", str(exc))
        except BaseException as exc:
            self.post("error", str(exc))
            self.post("done", False)

    def load_model(self, WhisperModel, args):
        return WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    def process_with_fallback(
        self,
        WhisperModel,
        model,
        audio_path: Path,
        source: str,
        title: str,
        output_dir: Path,
        args,
        done: int,
        total: int,
    ):
        try:
            self.process_one(model, audio_path, source, title, output_dir, args, done, total)
            return model
        except RuntimeError as exc:
            if args.device != "auto" or not is_cuda_runtime_error(exc):
                raise
            self.post("log", "CUDA runtime is incomplete. Retrying this job on CPU with int8.")
            args.device = "cpu"
            args.compute_type = "int8"
            cpu_model = self.load_model(WhisperModel, args)
            self.process_one(cpu_model, audio_path, source, title, output_dir, args, done, total)
            return cpu_model

    def process_one(
        self,
        model,
        audio_path: Path,
        source: str,
        title: str,
        output_dir: Path,
        args,
        done: int,
        total: int,
    ) -> None:
        check_cancelled(self.cancel_event)
        self.post("log", f"Transcribing: {title}")
        self.post_job_progress(done, total, 0.22, "Transcribing", title)

        def transcribe_progress(fraction: float | None, phase: str) -> None:
            if fraction is None:
                job_fraction = 0.45
            else:
                job_fraction = 0.22 + min(max(fraction, 0.0), 1.0) * 0.70
            self.post_job_progress(done, total, job_fraction, phase, title)

        result = transcribe_audio(model, audio_path, source, title, args, transcribe_progress, self.cancel_event)
        check_cancelled(self.cancel_event)
        self.post_job_progress(done, total, 0.95, "Writing outputs", title)
        write_outputs(result, output_dir, args.formats)
        language = result.language or "unknown"
        self.post("log", f"Saved transcript for {title} ({language}, {len(result.segments)} segments)")

    def post_job_progress(self, done: int, total: int, job_fraction: float, phase: str, detail: str) -> None:
        total = max(total, 1)
        percent = min(max(((done + job_fraction) / total) * 100, 0), 100)
        self.post_progress(percent, phase, detail)

    def post_progress(self, percent: float, phase: str, detail: str) -> None:
        elapsed = 0.0 if self.job_started_at is None else time.monotonic() - self.job_started_at
        eta = "calculating"
        if percent > 1 and elapsed > 1:
            remaining = elapsed * (100 - percent) / percent
            eta = format_short_time(remaining)
        self.post(
            "progress_detail",
            {
                "percent": percent,
                "phase": phase,
                "detail": detail,
                "elapsed": format_short_time(elapsed),
                "eta": eta,
            },
        )

    def post(self, kind: str, payload: object) -> None:
        self.message_queue.put((kind, payload))

    def poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.message_queue.get_nowait()
                if kind == "log":
                    self.log(str(payload))
                elif kind == "error":
                    self.log(f"ERROR: {payload}")
                    messagebox.showerror("Transcription failed", str(payload))
                elif kind == "cancelled":
                    self.running = False
                    self.start_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    self.progress_detail.set(str(payload))
                    self.progress_meta.set("Cancelled")
                    self.log("Job cancelled.")
                elif kind == "progress":
                    self.progress.set(float(payload))
                elif kind == "progress_detail":
                    data = dict(payload)  # type: ignore[arg-type]
                    percent = float(data["percent"])
                    self.progress.set(percent)
                    self.progress_text.set(f"{data['phase']} - {percent:.0f}%")
                    self.progress_detail.set(str(data["detail"]))
                    self.progress_meta.set(f"Elapsed {data['elapsed']} | ETA {data['eta']}")
                elif kind == "update_available":
                    data = dict(payload)  # type: ignore[arg-type]
                    self.log(f"Update available: {data['version']}")
                    if messagebox.askyesno(
                        "Update available",
                        f"OpenScribe Studio {data['version']} is available. Open the release page?",
                    ):
                        webbrowser.open(str(data["url"]))
                elif kind == "done":
                    self.running = False
                    self.start_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    if payload:
                        self.progress.set(100)
                        self.progress_text.set("Complete - 100%")
                        self.progress_meta.set("ETA 0:00")
                        self.progress_detail.set("All transcripts were generated successfully.")
                        self.log("All jobs finished.")
                        messagebox.showinfo("Done", "Transcripts were generated successfully.")
        except queue.Empty:
            pass
        self.after(120, self.poll_queue)

    def log(self, message: str) -> None:
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def ffmpeg_status_text(self) -> str:
        ffmpeg = get_ffmpeg_executable()
        if ffmpeg:
            short = re.sub(r"^.*?([^\\/]+)$", r"\1", ffmpeg)
            return f"ffmpeg ready: {short}"
        return "ffmpeg not found"


def is_cuda_runtime_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    return any(hint in message for hint in CUDA_RUNTIME_HINTS)


def version_tuple(value: str) -> tuple[int, ...]:
    parts = []
    for part in re.split(r"[^0-9]+", value):
        if part:
            parts.append(int(part))
    return tuple(parts or [0])


if __name__ == "__main__":
    app = TranscriptApp()
    app.mainloop()
