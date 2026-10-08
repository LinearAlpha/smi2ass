#requires -Version 5.1
# Build and verify Python distributions and selected Windows executables.
param(
    [ValidateSet('cli', 'gui', 'all')]
    [string]$Target = 'all'
)
$ErrorActionPreference = 'Stop'

if ([Environment]::OSVersion.Platform -ne 'Win32NT') {
    throw 'build.ps1 requires Windows x86-64. On Linux, use build.sh.'
}

function Invoke-BuildPython {
    & $script:BuildPython @args
    if ($LASTEXITCODE -ne 0) {
        throw "Build step failed (exit code ${LASTEXITCODE}): python $($args -join ' ')"
    }
}

$OriginalPythonHome = $env:PYTHONHOME
$OriginalPythonPath = $env:PYTHONPATH
Push-Location -LiteralPath $PSScriptRoot
try {
    $env:PYTHONHOME = $null
    $env:PYTHONPATH = $null
    # Single quotes inside the Python expression survive legacy PowerShell's
    # native argument handling as well as PowerShell 7's argument handling.
    $VersionCheck = "import platform, sys; sys.exit(0 if sys.version_info[:2] == (3, 14) and sys.maxsize > 2**32 and platform.machine().lower() in ('amd64', 'x86_64') else 1)"
    $BootstrapPython = $null
    $BootstrapArgs = @()
    foreach ($candidate in @(
        @{ Name = 'python'; Arguments = @() },
        @{ Name = 'py'; Arguments = @('-3.14') }
    )) {
        $command = Get-Command $candidate.Name -CommandType Application -ErrorAction SilentlyContinue
        if ($command) {
            $candidateArgs = $candidate.Arguments
            try {
                & $command.Source @candidateArgs -I -c $VersionCheck 2>$null
                if ($LASTEXITCODE -eq 0) {
                    $BootstrapPython = $command.Source
                    $BootstrapArgs = $candidateArgs
                    break
                }
            } catch {
                # Try the next launcher if this command cannot run Python 3.14.
            }
        }
    }
    if (!$BootstrapPython) {
        throw 'Install Python 3.14 x86-64 with python or py available on PATH, then rerun build.ps1.'
    }

    $script:BuildPython = Join-Path $PSScriptRoot '.build-venv\Scripts\python.exe'
    if (Test-Path -LiteralPath '.build-venv') {
        if (!(Test-Path -LiteralPath $script:BuildPython -PathType Leaf)) {
            throw 'The existing .build-venv is invalid. Rename or remove it and rerun build.ps1.'
        }
        & $script:BuildPython -I -c $VersionCheck
        if ($LASTEXITCODE -ne 0) {
            throw 'The existing .build-venv is not a Python 3.14 x86-64 environment. Rename or remove it and rerun build.ps1.'
        }
    } else {
        & $BootstrapPython @BootstrapArgs -I -m venv .build-venv
        if ($LASTEXITCODE -ne 0) {
            throw "Creating .build-venv failed (exit code ${LASTEXITCODE})."
        }
    }

    Invoke-BuildPython -I -m pip --isolated install -r requirements-build.txt
    $Project = if ($Target -eq 'cli') { '.' } else { '.[gui]' }
    Invoke-BuildPython -I -m pip --isolated install --force-reinstall $Project
    Invoke-BuildPython -I -m pip --isolated check
    # Remove only this project's old Python artifacts before building the new pair.
    if (Test-Path -LiteralPath 'dist') {
        Get-ChildItem -LiteralPath 'dist' -File |
            Where-Object { $_.Name -like 'smi2ass-*.whl' -or $_.Name -like 'smi2ass-*.tar.gz' } |
            Remove-Item -Force
    }
    Invoke-BuildPython -I -m build
    $artifacts = @(Get-ChildItem -LiteralPath 'dist' -File |
        Where-Object { $_.Extension -eq '.whl' -or $_.Name -like '*.tar.gz' } |
        ForEach-Object { $_.FullName })
    if ($artifacts.Count -ne 2) {
        throw 'Expected one wheel and one source distribution in dist.'
    }
    Invoke-BuildPython -I -m twine check --strict @artifacts
    $DistributionOptions = @()
    if ($Target -ne 'cli') { $DistributionOptions += '--gui' }
    Invoke-BuildPython -I scripts/check_distributions.py @DistributionOptions
    Invoke-BuildPython -I scripts/build_executable.py --target $Target
    Invoke-BuildPython -I scripts/package_assets.py --target $Target

    Write-Host "Build complete ($Target): wheel/source distributions in dist; executable ZIP/7z archives in release-assets."
} finally {
    $env:PYTHONHOME = $OriginalPythonHome
    $env:PYTHONPATH = $OriginalPythonPath
    Pop-Location
}

