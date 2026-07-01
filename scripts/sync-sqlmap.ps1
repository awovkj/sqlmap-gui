param(
    [string]$Source = "C:\Users\31373\Downloads\sqlmap-master"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$target = Join-Path $repoRoot "vendor\sqlmap"
$targetParent = Split-Path -Parent $target

if (-not (Test-Path -LiteralPath $Source)) {
    throw "sqlmap source not found: $Source"
}

$resolvedRepo = (Resolve-Path -LiteralPath $repoRoot).Path
New-Item -ItemType Directory -Force -Path $targetParent | Out-Null

if (Test-Path -LiteralPath $target) {
    $resolvedTarget = (Resolve-Path -LiteralPath $target).Path
    if (-not $resolvedTarget.StartsWith($resolvedRepo, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove target outside repository: $resolvedTarget"
    }
    Remove-Item -LiteralPath $target -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $target | Out-Null

$sourcePath = (Resolve-Path -LiteralPath $Source).Path
$excludeDirectories = @(".git", "__pycache__")
$excludeExtensions = @(".pyc", ".pyo")

Get-ChildItem -LiteralPath $sourcePath -Force -Recurse | ForEach-Object {
    $relative = $_.FullName.Substring($sourcePath.Length).TrimStart("\", "/")
    $parts = $relative -split "[\\/]"
    foreach ($part in $parts) {
        if ($excludeDirectories -contains $part) {
            return
        }
    }
    if (-not $_.PSIsContainer -and ($excludeExtensions -contains $_.Extension.ToLowerInvariant())) {
        return
    }

    $destination = Join-Path $target $relative
    if ($_.PSIsContainer) {
        New-Item -ItemType Directory -Force -Path $destination | Out-Null
    } else {
        $destinationParent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $target "sqlmap.py"))) {
    throw "Sync failed: vendor\sqlmap\sqlmap.py was not created"
}

Write-Host "Synced sqlmap source to $target"
