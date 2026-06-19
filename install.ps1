$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Add-PathIfExists {
    param([string]$Path)

    if ((Test-Path $Path) -and (($env:Path -split [IO.Path]::PathSeparator) -notcontains $Path)) {
        $env:Path = "$Path$([IO.Path]::PathSeparator)$env:Path"
    }
}

Add-PathIfExists "$HOME\.local\bin"
Add-PathIfExists "$HOME\.cargo\bin"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    Add-PathIfExists "$HOME\.local\bin"
    Add-PathIfExists "$HOME\.cargo\bin"
}

Set-Location $ProjectRoot

Write-Host "Installing Python 3.14 if needed..."
uv python install 3.14

Write-Host "Installing Satisfactory Recipes dependencies..."
uv sync

$LauncherPath = Join-Path $ProjectRoot "run-gui.ps1"
$Launcher = @'
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

uv run sat-rec gui
'@

Set-Content -Path $LauncherPath -Value $Launcher -Encoding UTF8

Write-Host ""
Write-Host "Install complete."
Write-Host "Launch the GUI with:"
Write-Host "  powershell -ExecutionPolicy ByPass -File `"$LauncherPath`""
