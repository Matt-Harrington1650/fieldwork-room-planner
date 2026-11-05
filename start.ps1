$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$bundledPython = 'C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1026-487-0_26.1026.487.0_x64__3k8sg7r9htsxt\dependencies\python\python.exe'
if (Test-Path -LiteralPath '.venv\Scripts\python.exe') { $appPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe' }
elseif (Test-Path -LiteralPath $bundledPython) { $appPython = $bundledPython }
else { $appPython = 'python' }
Write-Host 'Fieldwork is starting at http://127.0.0.1:8765. Keep this window open; Ctrl+C stops the app.'
& $appPython backend/run.py
