#requires -Version 5.1
# Exercise the real build script's interpreter detection without installing or compiling.
param(
    [Parameter(Mandatory = $true)]
    [string]$SupportedPython,
    [Parameter(Mandatory = $true)]
    [string]$UnsupportedPython
)
$ErrorActionPreference = 'Stop'
$OriginalPath = $env:PATH
$OriginalVirtualEnv = $env:VIRTUAL_ENV
$OriginalPythonHome = $env:PYTHONHOME
$OriginalPythonPath = $env:PYTHONPATH
$Fixture = Join-Path ([System.IO.Path]::GetTempPath()) ('smi2ass bootstrap ' + [guid]::NewGuid())
$BuildScript = Join-Path $Fixture 'build.ps1'
$Marker = Join-Path $Fixture 'bootstrap.json'

function Test-Bootstrap {
    <#
    .SYNOPSIS
    Run a cleanup-only build and check the selected interpreter or rejection message.
    .PARAMETER Name
    Description of the regression case.
    .PARAMETER ExpectedPython
    Exact interpreter that must run the harmless cleanup fixture.
    .PARAMETER Python
    Optional explicit interpreter passed to the build script.
    .PARAMETER FailurePattern
    Expected rejection text; rejected cases must never reach cleanup.
    .PARAMETER BuildProbe
    Reach the first build command using a local pip stub that records its interpreter.
    #>
    param([string]$Name, [string]$ExpectedPython, [string]$Python, [string]$FailurePattern, [switch]$BuildProbe)
    if (Test-Path -LiteralPath $Marker) { Remove-Item -LiteralPath $Marker }
    $options = @{ CleanOnly = $true }
    if ($BuildProbe) { $options = @{} }
    if ($Python) { $options.Python = $Python }
    $failure = $null
    $location = (Get-Location).Path
    try {
        & $BuildScript @options
    } catch {
        $failure = $_.Exception.Message
    }
    if ($FailurePattern) {
        if (!$failure -or $failure -notmatch $FailurePattern -or $failure -notmatch '-Python') {
            throw "$Name did not report the expected interpreter error: $failure"
        }
        if (Test-Path -LiteralPath $Marker) { throw "$Name unexpectedly reached cleanup." }
    } else {
        if ($BuildProbe) {
            if (!$failure -or $failure -notmatch 'Build step failed \(exit code 73\)') {
                throw "$Name did not reach the isolated pip stub: $failure"
            }
        } elseif ($failure) { throw "$Name failed: $failure" }
        $result = Get-Content -LiteralPath $Marker -Raw | ConvertFrom-Json
        if ($result.version[0] -ne 3 -or $result.version[1] -ne 14 -or $result.executable -ne $ExpectedPython) {
            throw "$Name selected the wrong interpreter: $($result.executable)"
        }
    }
    if ((Get-Location).Path -ne $location -or $env:PYTHONHOME -ne 'fixture-pythonhome' -or $env:PYTHONPATH -ne 'fixture-pythonpath') {
        throw "$Name did not restore the caller's location and Python environment variables."
    }
    Write-Host "PASS: $Name"
}

try {
    New-Item -ItemType Directory -Path (Join-Path $Fixture 'scripts') -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path (Split-Path $PSScriptRoot -Parent) 'build.ps1') -Destination $BuildScript
    # These real venvs reproduce PATH precedence and an explicit path containing spaces.
    $OlderVenv = Join-Path $Fixture '.venv'
    $SupportedVenv = Join-Path $Fixture 'Python 314'
    & $UnsupportedPython -I -m venv --without-pip $OlderVenv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python 3.13 fixture.' }
    & $SupportedPython -I -m venv --without-pip $SupportedVenv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python 3.14 fixture.' }
    $OlderScripts = Join-Path $OlderVenv 'Scripts'
    $SupportedScripts = Join-Path $SupportedVenv 'Scripts'
    $SupportedExecutable = Join-Path $SupportedScripts 'python.exe'
    @'
import json
import pathlib
import sys
pathlib.Path('bootstrap.json').write_text(json.dumps({'version': list(sys.version_info[:2]), 'executable': sys.executable}))
'@ | Set-Content -LiteralPath (Join-Path $Fixture 'scripts\clean_project.py') -Encoding ASCII

    $env:VIRTUAL_ENV = $OlderVenv
    $env:PYTHONHOME = 'fixture-pythonhome'
    $env:PYTHONPATH = 'fixture-pythonpath'
    # Restrict PATH so no system launcher can conceal a detection regression.
    $env:PATH = "$OlderScripts;$SupportedScripts"
    Test-Bootstrap -Name 'Older active venv does not hide Python 3.14 on PATH' -ExpectedPython $SupportedExecutable
    $env:PATH = $OlderScripts
    Test-Bootstrap -Name 'Unsupported PATH interpreter has actionable diagnostics' -FailurePattern 'Python 3\.13'
    Test-Bootstrap -Name 'Explicit interpreter outside PATH with spaces' -ExpectedPython $SupportedExecutable -Python $SupportedExecutable

    # With no suitable PATH entry, a valid existing build environment can bootstrap itself.
    $env:PYTHONHOME = $null
    $env:PYTHONPATH = $null
    & $SupportedPython -I -m venv --without-pip (Join-Path $Fixture '.build-venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the existing build environment fixture.' }
    $env:PYTHONHOME = 'fixture-pythonhome'
    $env:PYTHONPATH = 'fixture-pythonpath'
    Test-Bootstrap -Name 'Existing Python 3.14 build environment is reusable' -ExpectedPython (Join-Path $Fixture '.build-venv\Scripts\python.exe')
    Test-Bootstrap -Name 'Explicit unsupported interpreter is rejected' -Python (Join-Path $OlderScripts 'python.exe') -FailurePattern 'Python 3\.13'
    Test-Bootstrap -Name 'Missing explicit executable is reported' -Python (Join-Path $Fixture 'missing.exe') -FailurePattern 'executable not found'

    # Stop at the first dependency command while recording the actual build interpreter.
    # This fixture never installs packages or invokes the compiler.
    $PipStub = Join-Path $Fixture '.build-venv\Lib\site-packages\pip'
    New-Item -ItemType Directory -Path $PipStub -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $PipStub '__init__.py') -Value '' -Encoding ASCII
    $StubCode = Get-Content -LiteralPath (Join-Path $Fixture 'scripts\clean_project.py') -Raw
    ($StubCode + "`nsys.exit(73)`n") | Set-Content -LiteralPath (Join-Path $PipStub '__main__.py') -Encoding ASCII
    Test-Bootstrap -Name 'Explicit matching installation reuses the build interpreter' -Python $SupportedExecutable -BuildProbe -ExpectedPython (Join-Path $Fixture '.build-venv\Scripts\python.exe')

    # A copied real installation has the same version but a distinct base directory.
    $AlternateInstallation = Join-Path $Fixture 'Alternate Python 314'
    Copy-Item -LiteralPath (Split-Path $SupportedPython -Parent) -Destination $AlternateInstallation -Recurse
    Test-Bootstrap -Name 'Explicit different installation cannot reuse the build environment' -Python (Join-Path $AlternateInstallation 'python.exe') -BuildProbe -FailurePattern 'different Python installation'
} finally {
    $env:PATH = $OriginalPath
    $env:VIRTUAL_ENV = $OriginalVirtualEnv
    $env:PYTHONHOME = $OriginalPythonHome
    $env:PYTHONPATH = $OriginalPythonPath
    if (Test-Path -LiteralPath $Fixture) { Remove-Item -LiteralPath $Fixture -Recurse -Force }
}

# Expected rejection probes leave a nonzero native exit code; all assertions passed here.
exit 0
