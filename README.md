# OpenScribe Studio

Local-first desktop transcription for video files, audio files, and YouTube/video links.

OpenScribe Studio is a portfolio-ready, open-source desktop app built around `faster-whisper`, `yt-dlp`, and `ffmpeg`. It helps creators, researchers, editors, and students turn media into Markdown transcripts, subtitles, plain text, or structured JSON without sending local files to a cloud transcription API.

## Highlights

- Desktop UI for Windows, with macOS packaging support in progress.
- Local media files, folders, and pasted YouTube/video URLs.
- Whisper model choices from fast drafts to higher-accuracy transcripts.
- CPU and NVIDIA CUDA options.
- Job progress with percentage, elapsed time, ETA, and current activity.
- Cancel button for stopping long jobs.
- GitHub update check that opens the latest release page.
- Markdown, SRT, VTT, TXT, and JSON outputs.
- Optional speech-to-English translation.
- Optional cookies file for protected videos.
- Portable Windows build script.

## Screenshots

Add screenshots here after building a release:

```text
docs/screenshots/openscribe-studio-main.png
```

## Recommended Settings

For most users:

```text
Model: small
Device: cpu
Compute Type: int8
```

For better quality:

```text
Model: medium or large-v3
Device: cuda
Compute Type: float16
```

CUDA requires a compatible NVIDIA GPU and the CUDA/cuDNN runtime expected by `faster-whisper` and CTranslate2. If CUDA is not set up correctly, use `cpu` + `int8`.

See [USER_GUIDE.md](USER_GUIDE.md) for a non-technical guide to models, performance settings, output formats, YouTube links, and progress behavior.

## Install From Source

Requirements:

- Python 3.10 or newer
- `ffmpeg`
- Windows, macOS, or Linux with Tk support

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the desktop app:

```powershell
python transcript_app.py
```

On Windows you can also use:

```powershell
.\run_app.ps1
```

## Build Windows Portable App

```powershell
.\build_windows_portable.ps1
```

The portable build is created at:

```text
dist\OpenScribeStudio\OpenScribeStudio.exe
```

The build uses `imageio-ffmpeg`, which normally bundles an ffmpeg binary. You can also place `ffmpeg.exe` in either location before building:

```text
ffmpeg.exe
vendor\ffmpeg\bin\ffmpeg.exe
```

## Build macOS App

On macOS:

```bash
chmod +x build_macos_app.sh
./build_macos_app.sh
```

The app bundle is created at:

```text
dist/OpenScribeStudio.app
```

For public distribution outside the App Store, macOS users get the best experience when the app is signed and notarized with an Apple Developer account. Unsigned builds are useful for testing but will show security warnings.

## Command-Line Examples

Transcribe one local video:

```powershell
python transcript_tool.py --input "D:\Videos\meeting.mp4"
```

Transcribe every supported media file in a folder:

```powershell
python transcript_tool.py --input "D:\Videos" --model medium --formats md srt json
```

Transcribe YouTube links from a text file:

```powershell
python transcript_tool.py --urls-file urls.txt --output-dir transcripts
```

Transcribe Indonesian audio and translate it to English:

```powershell
python transcript_tool.py --input video.mp4 --language id --translate --formats md srt
```

Use a larger model for better accuracy:

```powershell
python transcript_tool.py --input video.mp4 --model large-v3
```

## Supported Local Formats

```text
3gp, aac, aiff, avi, asf, flac, flv, m4a, m4v, mkv, mov, mp3, mp4,
mpeg, mpg, m2ts, m2v, mts, mxf, oga, ogg, ogv, opus, ts, wav, webm, wma
```

## Outputs

- `MD`: readable transcript with timestamps and metadata
- `SRT`: subtitles for editors, YouTube, and media players
- `VTT`: web subtitles
- `TXT`: plain transcript text
- `JSON`: structured transcript data

## Roadmap

- Automatic PC capability recommendation for model/device settings.
- Signed Windows installer.
- Signed and notarized macOS DMG.
- Better per-download progress reporting for every supported video site.

## License

MIT. See [LICENSE](LICENSE).
