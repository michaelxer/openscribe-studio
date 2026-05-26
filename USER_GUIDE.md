# OpenScribe Studio User Guide

This guide explains the choices in the desktop app: model size, performance mode, output formats, YouTube links, and what to expect while a job is running.

## Quick Start

1. Add local video/audio files, add a folder, or paste one video URL per line.
2. Choose an output folder.
3. Leave Language as `Auto detect` unless you already know the spoken language.
4. Start with Model `small`, Device `cpu`, and Compute Type `int8`.
5. Select the output formats you need.
6. Click `Start transcription`.

For most Windows users, `small` + `cpu` + `int8` is the safest first run. After confirming the app works, try a bigger model or GPU settings for better quality or speed.

## What Happens During A Job

The app processes each source in this order:

1. Check `ffmpeg`.
2. Find local media files, or read each pasted URL.
3. Download URL audio with `yt-dlp` when using YouTube or another video site.
4. Convert/extract the audio to a 16 kHz WAV file.
5. Load the selected Whisper model.
6. Transcribe or translate the audio.
7. Write the selected output files.

The first run with a new model can take longer because the model must be downloaded and cached.

## Activity And Progress

The progress band above Activity shows:

- current phase
- percentage complete
- elapsed time
- estimated time remaining
- current file, URL, or transcript title

The Activity box below it shows the detailed event log, such as loading the model, downloading audio, extracting audio, transcribing, and saving files.

The percentage is an estimate across the whole job. During transcription, it uses the audio timestamp reported by Whisper segments. ETA becomes more useful after the job has been running long enough to measure speed.

Expected waiting time depends on:

- video length
- model size
- CPU or GPU speed
- whether this is the first model download
- YouTube download speed
- audio quality and amount of speech

As a rough rule, short clips with `small` on CPU may finish in minutes. Long videos with `medium` or `large-v3` on CPU can take much longer. For long videos, GPU can help a lot when CUDA is correctly installed.

## Cancel A Job

Click `Cancel` to stop the active job. The app stops as soon as the current step allows it.

Cancellation is fastest while extracting audio or while Whisper is producing transcript segments. Some operations, such as model loading or a video site's download handshake, may need a little time before they can stop.

## Model Choices

Larger models are usually more accurate, especially for noisy audio, accents, mixed speakers, and non-English speech. They are also slower and use more memory.

| Model | Best for | Tradeoff |
| --- | --- | --- |
| `tiny` | Fast testing, very weak PCs, quick previews | Lowest accuracy |
| `base` | Faster drafts and simple clear speech | Still misses more words than `small` |
| `small` | Recommended default for most users | Good balance of speed and quality |
| `medium` | Better quality for important transcripts | Slower, more memory |
| `large-v3` | Best quality among the app's standard Whisper options | Slowest and most demanding |
| `distil-large-v3` | Fast English speech recognition with near-large quality | Best for English; not the safest choice for multilingual transcription or translation |

Recommended choices:

- Use `small` first if you are unsure.
- Use `medium` for better quality when the audio is important.
- Use `large-v3` for best quality, especially multilingual or difficult audio, if your PC can handle it.
- Use `distil-large-v3` for English speech when speed matters.
- Avoid `tiny` and `base` for final subtitles unless speed matters more than accuracy.

## Language

`Auto detect` is convenient and usually works well. Manually selecting the language can improve results when:

- the clip is short
- the speaker starts with music or silence
- there are multiple languages nearby
- auto detection picks the wrong language

If you enable `Translate speech to English`, the app asks Whisper to translate the spoken audio into English instead of writing the original language.

For translation, prefer `medium` or `large-v3`. Do not rely on `distil-large-v3` for translation.

## Performance Settings

The Performance row has two choices:

- Device: `auto`, `cpu`, or `cuda`
- Compute Type: `auto`, `int8`, `float16`, or `float32`

### Device

| Device | Meaning | When to choose it |
| --- | --- | --- |
| `cpu` | Run on the processor | Safest default for most Windows PCs |
| `cuda` | Run on an NVIDIA GPU | Best speed if NVIDIA CUDA/cuDNN is installed correctly |
| `auto` | Let faster-whisper choose | Useful for advanced users, but less predictable |

This app does not use AMD, Intel, or Apple GPU acceleration through the `cuda` option. CUDA is for NVIDIA GPUs.

If CUDA fails because the runtime is missing or incomplete, the desktop app tries to retry on `cpu` with `int8`.

### Compute Type

| Compute Type | Best use | Notes |
| --- | --- | --- |
| `int8` | CPU default, low memory | Best reliability on normal Windows PCs |
| `float16` | NVIDIA GPU default | Fast and accurate on CUDA GPUs |
| `float32` | Compatibility/testing | More memory and usually slower |
| `auto` | Let the backend choose | Can be useful, but harder to explain to non-technical users |

Recommended combinations:

| User / PC | Model | Device | Compute Type |
| --- | --- | --- | --- |
| Unsure, normal laptop/desktop | `small` | `cpu` | `int8` |
| Weak PC, quick draft | `base` or `tiny` | `cpu` | `int8` |
| Better quality on CPU | `medium` | `cpu` | `int8` |
| NVIDIA GPU installed and CUDA works | `medium` or `large-v3` | `cuda` | `float16` |
| NVIDIA GPU with limited VRAM | `small` or `medium` | `cuda` | `int8` |
| English transcript, faster than large | `distil-large-v3` | `cuda` or `cpu` | `float16` on CUDA, `int8` on CPU |

## Output Formats

| Format | Use it for |
| --- | --- |
| `MD` | Human-readable transcript with timestamps and metadata |
| `SRT` | Subtitles for video editors, YouTube, and media players |
| `VTT` | Web subtitles |
| `TXT` | Plain text transcript |
| `JSON` | Structured data for developers or later processing |

The app writes files into the selected output folder. If a filename already exists, it creates a numbered filename instead of replacing the old file.

## YouTube And Video URLs

Paste one URL per line. The app uses `yt-dlp` to download audio first, then transcribes the downloaded audio.

Use a cookies file only for videos that require login or age/session access. A cookies file should come from a browser session where you are allowed to view the video.

Make sure you have the right to download and transcribe the content, and follow the site's terms.

## Keep Extracted Audio

When `Keep extracted audio` is off, temporary audio is cleaned up after a successful run.

When it is on, WAV files are saved under `_audio` in the output folder. This is useful for debugging bad transcripts or reusing the extracted audio.

## Troubleshooting

### The transcript is inaccurate

- Try `medium` or `large-v3`.
- Manually choose the spoken language.
- Use better source audio when possible.
- Avoid `tiny` and `base` for final output.

### It is too slow

- Try `small` instead of `medium` or `large-v3`.
- Use `distil-large-v3` for English speech.
- Use an NVIDIA GPU with `cuda` + `float16` if CUDA/cuDNN is installed.
- Use `cpu` + `int8` for reliable CPU runs.

### CUDA does not work

- Confirm the PC has an NVIDIA GPU.
- Install/update the NVIDIA driver.
- Install the CUDA/cuDNN runtime required by faster-whisper/CTranslate2.
- If unsure, switch back to `cpu` + `int8`.

### YouTube download fails

- Check the URL in a browser.
- Try a public video first.
- For protected videos, provide a cookies file.
- Update `yt-dlp` if running from source.

## References

- OpenAI Whisper model sizes and memory notes: https://github.com/openai/whisper#available-models-and-languages
- Faster-Whisper usage examples for CPU/GPU compute types: https://github.com/SYSTRAN/faster-whisper
- Distil-Whisper `distil-large-v3` model card: https://huggingface.co/distil-whisper/distil-large-v3
