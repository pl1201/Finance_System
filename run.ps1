# Market Structure Lab — script khởi động cho Windows / PowerShell.
#
#   .\run.ps1            : cài môi trường nếu chưa có, rồi chạy app
#   .\run.ps1 -Setup     : chỉ cài môi trường
#   .\run.ps1 -Test      : chạy bộ test
#   .\run.ps1 -Port 8100 : đổi cổng
#
# Chỉ cần MỘT tiến trình: backend FastAPI phục vụ luôn giao diện tĩnh.

param(
    [switch]$Setup,
    [switch]$Test,
    [int]$Port = 8099,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "[1/3] Chua co moi truong ao. Dang tao .venv ..." -ForegroundColor Cyan
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) { & py -3 -m venv .venv } else { & python -m venv .venv }
    if (-not (Test-Path $python)) { throw "Khong tao duoc .venv. Kiem tra Python 3.10+ da cai chua." }
}

if ($Setup -or -not (Test-Path (Join-Path $PSScriptRoot ".venv\Lib\site-packages\fastapi"))) {
    Write-Host "[2/3] Cai dependency ..." -ForegroundColor Cyan
    & $python -m pip install --upgrade pip
    & $python -m pip install -r requirements.txt
}

$env:PYTHONPATH = $PSScriptRoot

if ($Test) {
    Write-Host "Chay bo test ..." -ForegroundColor Cyan
    & $python -m pytest -q
    exit $LASTEXITCODE
}

if ($Setup) {
    Write-Host "Da cai xong moi truong. Chay lai '.\run.ps1' de mo app." -ForegroundColor Green
    exit 0
}

$url = "http://127.0.0.1:$Port/"
Write-Host "[3/3] Khoi dong Market Structure Lab tai $url" -ForegroundColor Green
Write-Host "      Nhan Ctrl+C de dung." -ForegroundColor DarkGray

if (-not $NoBrowser) {
    Start-Job -ScriptBlock {
        param($u)
        Start-Sleep -Seconds 2
        Start-Process $u
    } -ArgumentList $url | Out-Null
}

& $python -m uvicorn backend.app.main:app --host 127.0.0.1 --port $Port
