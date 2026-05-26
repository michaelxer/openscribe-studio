# Contributing

Thanks for improving OpenScribe Studio.

## Local Setup

```powershell
python -m pip install -r requirements.txt
python transcript_app.py
```

For command-line testing:

```powershell
python transcript_tool.py --help
```

## Development Notes

- Keep the app local-first and clear for non-technical users.
- Prefer conservative defaults: `small`, `cpu`, `int8`.
- Avoid silently downloading large models before the user starts a job.
- Keep UI copy short and practical.
- Do not commit generated build outputs from `build/`, `dist/`, `temp_files/`, or transcript output folders.

## Pull Requests

Please include:

- what changed
- why it changed
- how you tested it
- screenshots for UI changes when possible
