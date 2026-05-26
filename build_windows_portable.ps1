$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    python -m venv .venv
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt pyinstaller

$AddBinary = @()
$FfmpegCandidates = @(
    (Join-Path $Root "ffmpeg.exe"),
    (Join-Path $Root "vendor\ffmpeg\bin\ffmpeg.exe")
)

foreach ($Candidate in $FfmpegCandidates) {
    if (Test-Path $Candidate) {
        $AddBinary += @("--add-binary", "$Candidate;.")
        break
    }
}

& $VenvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name "OpenScribeStudio" `
    --collect-all faster_whisper `
    --collect-all ctranslate2 `
    --collect-all av `
    --collect-all tokenizers `
    --collect-all huggingface_hub `
    --collect-all imageio_ffmpeg `
    --collect-all yt_dlp `
    @AddBinary `
    transcript_app.py

$DistApp = Join-Path $Root "dist\OpenScribeStudio"
Copy-Item -Path (Join-Path $Root "README.md") -Destination $DistApp -Force
Copy-Item -Path (Join-Path $Root "USER_GUIDE.md") -Destination $DistApp -Force
Copy-Item -Path (Join-Path $Root "urls.example.txt") -Destination $DistApp -Force

Write-Host ""
Write-Host "Portable app created:"
Write-Host "  $DistApp"
Write-Host ""
Write-Host "Run:"
Write-Host "  $DistApp\OpenScribeStudio.exe"
Write-Host ""
Write-Host "If ffmpeg was not bundled, place ffmpeg.exe beside the EXE or install ffmpeg globally."
