$ErrorActionPreference = "Stop"
Set-Location -Path (Join-Path $PSScriptRoot "backend")
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
& $python -m uvicorn main:app --host 127.0.0.1 --port 8000
