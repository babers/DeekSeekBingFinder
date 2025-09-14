param(
    [switch]$OneFile = $false,
    [string]$Python = "python"
)

# Build the application using PyInstaller
$ErrorActionPreference = 'Stop'

if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found in PATH. Pass -Python <path> if needed."
}

& $Python -m pip install --upgrade pip | Out-Null
& $Python -m pip install -r "$(Resolve-Path ..\requirements.txt)" | Out-Null
& $Python -m pip install pyinstaller | Out-Null

$root = Resolve-Path ".."
$outDir = Join-Path $root "dist"
$specDir = Join-Path $root "build"
$main = Join-Path $root "main.py"

if ($OneFile.IsPresent) {
    $onefileArg = "--onefile"
} else {
    $onefileArg = "--onedir"
}

# Add data files so resource_path finds them
$addData = @(
    "config.yaml;.",
    "README.md;."
)

$dataArgs = @()
foreach ($d in $addData) {
    $dataArgs += "--add-data `"$root\$d`""
}

$parts = @()
$parts += $Python
$parts += "-m"
$parts += "PyInstaller"
$parts += "--name"
$parts += "DeekSeekBingFinder"
$parts += "--noconfirm"
$parts += "--clean"
$parts += "--hidden-import"
$parts += "pkgutil"
$parts += $onefileArg
foreach ($a in $dataArgs) { $parts += $a }
$parts += $main

$cmd = ($parts -join ' ')

Write-Host "Running: $cmd"
Invoke-Expression $cmd

Write-Host "Build complete. Output at: $outDir"
