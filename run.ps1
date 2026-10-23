Set-Location $PSScriptRoot
if (-not (Test-Path .\.venv\Scripts\python.exe)) {
    py -3.12 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}
.\.venv\Scripts\python.exe -m hearthline
