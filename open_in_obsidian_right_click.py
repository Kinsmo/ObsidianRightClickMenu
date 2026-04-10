"""
Add a Windows Explorer right-click menu item:

    Right click inside a folder -> Open in Obsidian

Run:
    python open_in_obsidian_right_click.py

Remove:
    python open_in_obsidian_right_click.py --remove

This script uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import textwrap
import winreg


MENU_NAME = "Open in Obsidian"
REGISTRY_KEY = r"Software\Classes\Directory\Background\shell\OpenInObsidian"

# Change this default if your machine uses a different path.
DEFAULT_OBSIDIAN_EXE = r"D:\ProgramFiles\Obsidian\Obsidian.exe"


POWERSHELL_HELPER_TEMPLATE = r"""
param(
    [Parameter(Mandatory = $true)]
    [string]$FolderPath
)

$ErrorActionPreference = 'Stop'

$obsidianExe = __OBSIDIAN_EXE__
$obsidianConfigDir = Join-Path $env:APPDATA 'obsidian'
$obsidianConfigPath = Join-Path $obsidianConfigDir 'obsidian.json'
$templateVaultConfigDir = __TEMPLATE_OBSIDIAN_DIR__

if (-not (Test-Path -LiteralPath $obsidianExe -PathType Leaf)) {
    throw "Obsidian.exe was not found at $obsidianExe"
}

$resolvedFolder = (Resolve-Path -LiteralPath $FolderPath).ProviderPath
if (-not (Test-Path -LiteralPath $resolvedFolder -PathType Container)) {
    throw "Folder was not found: $resolvedFolder"
}

$targetVaultConfigDir = Join-Path $resolvedFolder '.obsidian'
if (Test-Path -LiteralPath $targetVaultConfigDir -PathType Leaf) {
    throw "A file named .obsidian already exists in $resolvedFolder. It must be a directory."
}

if (-not (Test-Path -LiteralPath $targetVaultConfigDir -PathType Container)) {
    if (Test-Path -LiteralPath $templateVaultConfigDir -PathType Container) {
        Copy-Item -LiteralPath $templateVaultConfigDir -Destination $targetVaultConfigDir -Recurse -Force
    } else {
        New-Item -ItemType Directory -Path $targetVaultConfigDir -Force | Out-Null
    }
}

if (-not (Test-Path -LiteralPath $obsidianConfigDir -PathType Container)) {
    New-Item -ItemType Directory -Path $obsidianConfigDir -Force | Out-Null
}

function Stop-Obsidian {
    $processes = @(Get-Process -Name Obsidian -ErrorAction SilentlyContinue)
    if ($processes.Count -eq 0) {
        return
    }

    foreach ($process in $processes) {
        if ($process.MainWindowHandle -ne 0) {
            [void]$process.CloseMainWindow()
        }
    }

    $deadline = (Get-Date).AddSeconds(12)
    do {
        Start-Sleep -Milliseconds 250
        $processes = @(Get-Process -Name Obsidian -ErrorAction SilentlyContinue)
    } while ($processes.Count -gt 0 -and (Get-Date) -lt $deadline)

    foreach ($process in $processes) {
        Stop-Process -Id $process.Id -Force
    }
}

function New-StableVaultId {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $normalized = $Path.TrimEnd('\').ToLowerInvariant()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($normalized)
    $hash = [System.Security.Cryptography.SHA1]::Create().ComputeHash($bytes)
    return (($hash[0..7] | ForEach-Object { $_.ToString('x2') }) -join '')
}

function Read-ObsidianConfig {
    if (-not (Test-Path -LiteralPath $obsidianConfigPath -PathType Leaf)) {
        return [ordered]@{ vaults = [ordered]@{} }
    }

    $raw = Get-Content -LiteralPath $obsidianConfigPath -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return [ordered]@{ vaults = [ordered]@{} }
    }

    $parsed = $raw | ConvertFrom-Json
    $config = [ordered]@{}
    foreach ($property in $parsed.PSObject.Properties) {
        if ($property.Name -ne 'vaults') {
            $config[$property.Name] = $property.Value
        }
    }

    $vaults = [ordered]@{}
    if ($parsed.PSObject.Properties.Name -contains 'vaults') {
        foreach ($vault in $parsed.vaults.PSObject.Properties) {
            $vaults[$vault.Name] = [ordered]@{
                path = [string]$vault.Value.path
                ts   = [int64]$vault.Value.ts
                open = $false
            }
        }
    }

    $config['vaults'] = $vaults
    return $config
}

function Write-ObsidianConfig {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.IDictionary]$Config
    )

    if (Test-Path -LiteralPath $obsidianConfigPath -PathType Leaf) {
        Copy-Item -LiteralPath $obsidianConfigPath -Destination "$obsidianConfigPath.bak" -Force
    }

    $json = $Config | ConvertTo-Json -Depth 20
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($obsidianConfigPath, $json, $utf8NoBom)
}

Stop-Obsidian

$config = Read-ObsidianConfig
$vaultId = $null
foreach ($vault in $config['vaults'].GetEnumerator()) {
    if ([string]::Equals($vault.Value.path, $resolvedFolder, [System.StringComparison]::OrdinalIgnoreCase)) {
        $vaultId = $vault.Key
        break
    }
}

if (-not $vaultId) {
    $vaultId = New-StableVaultId -Path $resolvedFolder
    $counter = 1
    while ($config['vaults'].Contains($vaultId) -and -not [string]::Equals($config['vaults'][$vaultId].path, $resolvedFolder, [System.StringComparison]::OrdinalIgnoreCase)) {
        $vaultId = New-StableVaultId -Path "$resolvedFolder#$counter"
        $counter++
    }
}

$config['vaults'][$vaultId] = [ordered]@{
    path = $resolvedFolder
    ts   = [int64]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
    open = $true
}

Write-ObsidianConfig -Config $config
Start-Process -FilePath $obsidianExe
""".lstrip()


def ps_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def common_obsidian_paths() -> list[Path]:
    paths: list[Path] = [Path(DEFAULT_OBSIDIAN_EXE)]

    local_app_data = os.environ.get("LOCALAPPDATA")
    program_files = os.environ.get("ProgramFiles")
    program_files_x86 = os.environ.get("ProgramFiles(x86)")

    if local_app_data:
        paths.append(Path(local_app_data) / "Programs" / "Obsidian" / "Obsidian.exe")
        paths.append(Path(local_app_data) / "Obsidian" / "Obsidian.exe")
    if program_files:
        paths.append(Path(program_files) / "Obsidian" / "Obsidian.exe")
    if program_files_x86:
        paths.append(Path(program_files_x86) / "Obsidian" / "Obsidian.exe")

    return paths


def find_obsidian_exe(explicit_path: str | None) -> Path:
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if path.is_file():
            return path
        raise FileNotFoundError(f"Obsidian.exe was not found: {path}")

    for path in common_obsidian_paths():
        if path.is_file():
            return path

    raise FileNotFoundError(
        "Could not find Obsidian.exe. Run again with "
        "--obsidian-exe \"C:\\Path\\To\\Obsidian.exe\"."
    )


def choose_template_dir(explicit_path: str | None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser()

    repo_template = Path(__file__).resolve().parent / ".obsidian"
    if repo_template.is_dir():
        return repo_template

    return repo_template


def helper_install_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise EnvironmentError("LOCALAPPDATA is not set.")
    return Path(local_app_data) / "ObsidianRightClickMenu"


def write_helper_script(obsidian_exe: Path, template_dir: Path) -> Path:
    install_dir = helper_install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)

    helper_path = install_dir / "OpenFolderAsObsidianVault.ps1"
    helper_text = POWERSHELL_HELPER_TEMPLATE
    helper_text = helper_text.replace("__OBSIDIAN_EXE__", ps_single_quoted(str(obsidian_exe)))
    helper_text = helper_text.replace("__TEMPLATE_OBSIDIAN_DIR__", ps_single_quoted(str(template_dir)))
    helper_path.write_text(helper_text, encoding="utf-8")
    return helper_path


def set_context_menu(helper_path: Path, obsidian_exe: Path, menu_name: str) -> None:
    command = (
        'powershell.exe -NoProfile -ExecutionPolicy Bypass '
        f'-File "{helper_path}" "%V"'
    )

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, menu_name)
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(obsidian_exe))

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY + r"\command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)


def remove_context_menu() -> None:
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY + r"\command")
    except FileNotFoundError:
        pass

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
    except FileNotFoundError:
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add 'Open in Obsidian' to the Windows folder background right-click menu."
    )
    parser.add_argument(
        "--obsidian-exe",
        help="Full path to Obsidian.exe. Auto-detected when omitted.",
    )
    parser.add_argument(
        "--template-dir",
        help=(
            "Path to a template .obsidian directory. Defaults to the "
            "bundled .obsidian directory next to this script."
        ),
    )
    parser.add_argument(
        "--menu-name",
        default=MENU_NAME,
        help=f'Context menu label. Default: "{MENU_NAME}".',
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove the right-click menu item.",
    )
    return parser.parse_args()


def main() -> int:
    if os.name != "nt":
        print("This script only works on Windows.", file=sys.stderr)
        return 1

    args = parse_args()

    try:
        if args.remove:
            remove_context_menu()
            print("Removed the 'Open in Obsidian' right-click menu item.")
            return 0

        obsidian_exe = find_obsidian_exe(args.obsidian_exe)
        template_dir = choose_template_dir(args.template_dir)
        helper_path = write_helper_script(obsidian_exe, template_dir)
        set_context_menu(helper_path, obsidian_exe, args.menu_name)

        print("Done. The right-click menu item has been added.")
        print(f"Menu name: {args.menu_name}")
        print(f"Obsidian.exe: {obsidian_exe}")
        print(f"Template .obsidian: {template_dir}")
        print(f"Helper script: {helper_path}")
        print("")
        print("Use it by right-clicking inside a folder and choosing 'Open in Obsidian'.")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
