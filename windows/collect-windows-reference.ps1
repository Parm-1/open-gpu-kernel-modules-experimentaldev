param(
    [Parameter(Mandatory = $false)]
    [string]$OutputDirectory = (Join-Path $PWD ("artifacts\windows-reference-" + (Get-Date -Format "yyyyMMddTHHmmss")))
)

$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

function Save-Json([string]$Name, $Value) {
    $Value | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $OutputDirectory $Name)
}
function Get-HardwareId([string]$InstanceName) {
    if (-not $InstanceName) { return $null }
    $parts = $InstanceName -split '\\'
    if ($parts.Count -ge 2) { return "$($parts[0])\$($parts[1])" }
    return $parts[0]
}

$computer = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, SystemType
$os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture
$gpus = Get-CimInstance Win32_VideoController | ForEach-Object {
    [ordered]@{
        Name = $_.Name
        DriverVersion = $_.DriverVersion
        VideoProcessor = $_.VideoProcessor
        AdapterRAM = $_.AdapterRAM
        HardwareId = Get-HardwareId $_.PNPDeviceID
    }
}
$monitors = Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorBasicDisplayParams -ErrorAction SilentlyContinue | ForEach-Object {
    [ordered]@{
        HardwareId = Get-HardwareId $_.InstanceName
        MaxHorizontalImageSize = $_.MaxHorizontalImageSize
        MaxVerticalImageSize = $_.MaxVerticalImageSize
        VideoInputType = $_.VideoInputType
    }
}
Save-Json "system.json" ([ordered]@{schema_version=1;collected_at=(Get-Date).ToString("o");computer=$computer;os=$os;gpus=$gpus;monitors=$monitors})

$browserPaths = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
)
$browserVersions = foreach ($path in $browserPaths | Select-Object -Unique) {
    if (Test-Path $path) { $item=Get-Item $path; [ordered]@{path=$path;version=$item.VersionInfo.FileVersion} }
}
Save-Json "browser-versions.json" $browserVersions

$dxdiag = Join-Path $OutputDirectory "dxdiag.txt"
Start-Process -FilePath "dxdiag.exe" -ArgumentList @("/whql:off", "/t", $dxdiag) -Wait -NoNewWindow
if (Test-Path $dxdiag) {
    $text = Get-Content -Raw $dxdiag
    $text = $text -replace '(?im)^\s*Machine name:.*$', '      Machine name: <redacted>'
    Set-Content -Encoding UTF8 $dxdiag $text
}

@"
This collector records public OS, GPU, display, browser, and dxdiag metadata.
Review before publishing. It does not collect DRM licenses, CDM memory, keys,
device certificates, account data, or media samples.

Run the EME probe separately and save its JSON output in this directory.
"@ | Set-Content -Encoding UTF8 (Join-Path $OutputDirectory "README.txt")

Get-ChildItem -File -Recurse $OutputDirectory | ForEach-Object {
    $hash=Get-FileHash -Algorithm SHA256 $_.FullName
    "{0}  {1}" -f $hash.Hash.ToLowerInvariant(),$_.FullName.Substring($OutputDirectory.Length+1)
} | Set-Content -Encoding UTF8 (Join-Path $OutputDirectory "artifacts.sha256")
Write-Host "Windows reference written to $OutputDirectory"
