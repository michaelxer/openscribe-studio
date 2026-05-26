# OpenScribe Studio - Free Video, Audio, and YouTube Transcript Generator

OpenScribe Studio is a free, open-source desktop app for turning videos, audio files, and YouTube/video links into readable transcripts and subtitle files.

It is built for normal people first: creators, students, researchers, teachers, editors, marketers, writers, and anyone who needs a transcript without paying per minute to a cloud service.

OpenScribe Studio runs speech-to-text AI on your computer using Whisper through `faster-whisper`. Local files stay on your device. YouTube and other video links still need internet because the app must download the audio before it can transcribe it.

## What You Can Do With It

- Create transcripts from MP4, MP3, WAV, MOV, MKV, and many other media files.
- Paste YouTube or video links and turn them into transcript files.
- Export subtitles for video editing or upload: `SRT` and `VTT`.
- Save readable notes as `Markdown` or plain `TXT`.
- Save structured `JSON` for automation, search, datasets, or AI workflows.
- Translate speech into English using Whisper translation mode.
- Run locally with no per-minute transcription fee.
- Use CPU by default, or NVIDIA CUDA GPU if your computer supports it.

## Why Use OpenScribe Studio?

Many transcription tools are paid, online-only, or locked behind monthly plans. OpenScribe Studio is different:

- **Free and open source**: use it, study it, modify it, and share it.
- **Local-first**: your local files are processed on your computer.
- **Beginner-friendly**: a desktop interface, progress bar, ETA, and cancel button.
- **Useful outputs**: transcripts, subtitles, plain text, and JSON.
- **Good for AI work**: turn videos into clean text that can be used as research notes, knowledge bases, or training material for agents.

## Example Use Cases

OpenScribe Studio is useful when you want to:

- transcribe YouTube tutorials into study notes
- create subtitles for your own videos
- turn lectures, meetings, podcasts, webinars, or interviews into searchable text
- extract quotes and timestamps from long videos
- archive family recordings or voice notes
- create written summaries from course videos
- prepare source material for blogs, newsletters, and scripts
- build datasets from spoken content
- create training material for AI agents from video transcripts

One real workflow: download educational or strategy videos, extract transcripts, clean the text, then use those transcripts as source material for AI agents that need to learn a specific process, style, domain, or workflow.

## Download

Go to the latest release:

https://github.com/michaelxer/openscribe-studio/releases/latest

Download the file for your system:

- Windows: `OpenScribeStudio-windows-x64.zip`
- macOS: `OpenScribeStudio-macos.zip`

The Windows version is portable. Unzip it, open the folder, and run `OpenScribeStudio.exe`.

The macOS version is currently unsigned. It is useful for testing, but macOS may show a security warning until the app is signed and notarized with an Apple Developer account.

## Quick Start

1. Open OpenScribe Studio.
2. Add local video/audio files, add a folder, or paste one YouTube/video URL per line.
3. Choose an output folder.
4. Leave Language as `Auto detect` unless you already know the spoken language.
5. Start with these safe settings:

```text
Model: small
Device: cpu
Compute Type: int8
```

6. Select output formats such as `MD` and `SRT`.
7. Click `Start transcription`.

The app shows progress, elapsed time, estimated time remaining, current activity, and a Cancel button.

## Which Model Should I Choose?

If you are unsure, use `small`.

| Model | Best for | Notes |
| --- | --- | --- |
| `tiny` | Fast test runs | Lowest accuracy |
| `base` | Quick drafts | Better than tiny, still basic |
| `small` | Most people | Best default balance |
| `medium` | Better quality | Slower, uses more memory |
| `large-v3` | Best quality in this app | Slowest, best for difficult audio |
| `distil-large-v3` | Fast English transcription | Best for English, not ideal for translation |

Simple recommendation:

- Normal laptop or desktop: `small`, `cpu`, `int8`
- Weak computer: `base`, `cpu`, `int8`
- Important transcript: `medium` or `large-v3`
- NVIDIA GPU with CUDA working: `medium` or `large-v3`, `cuda`, `float16`
- English-only and speed matters: `distil-large-v3`

For more detail, read [USER_GUIDE.md](USER_GUIDE.md).

## Output Formats

| Format | Use it for |
| --- | --- |
| `MD` | Easy-to-read transcript with timestamps and metadata |
| `SRT` | Subtitles for YouTube, editors, and media players |
| `VTT` | Web subtitles |
| `TXT` | Simple plain text |
| `JSON` | Automation, datasets, search, and AI pipelines |

## Supported Files

Local files can be audio or video. Supported extensions include:

```text
3gp, aac, aiff, avi, asf, flac, flv, m4a, m4v, mkv, mov, mp3, mp4,
mpeg, mpg, m2ts, m2v, mts, mxf, oga, ogg, ogv, opus, ts, wav, webm, wma
```

## Privacy

OpenScribe Studio is local-first:

- Local files are transcribed on your computer.
- The selected Whisper model may be downloaded the first time you use it.
- YouTube/video URLs require internet because the audio must be downloaded.
- The app does not include a chatbot LLM.
- The app does not charge per minute.

## Install From Source

This option is for developers or advanced users.

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

On Windows:

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

For public distribution outside the App Store, macOS users get the best experience when the app is signed and notarized.

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

## Keywords

Free transcription software, free video transcript generator, YouTube transcript generator, audio to text app, video to text converter, free subtitle generator, SRT generator, VTT subtitle tool, Whisper desktop app, local speech-to-text, open-source transcription tool, podcast transcription, lecture transcription, meeting transcription, AI training transcript tool.

## Roadmap

- Automatic PC capability recommendation for model/device settings.
- Signed Windows installer.
- Signed and notarized macOS DMG.
- Better per-download progress reporting for every supported video site.
- Screenshots and short demo video.

## License

MIT. See [LICENSE](LICENSE).
