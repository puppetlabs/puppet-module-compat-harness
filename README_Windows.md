# Windows Local Setup Guide

This guide covers running the compatibility runner natively on Windows (no WSL).

## 1) Prerequisites

- RubyInstaller Ruby (x64 UCRT) installed (Ruby 3.2.x recommended)
- Git installed
- Python 3.8+ (for validation and reporting scripts)
- Administrative PowerShell access (for one-time long-path setting)
- **Acceptance tests require Docker** — see [Acceptance Tests](#8-acceptance-tests) below for Windows limitations

Validate basics:

```powershell
ruby -v
bundle -v
git --version
ridk version
python --version
```

## 2) Enable long paths (one-time)

Run in **Admin PowerShell**:

```powershell
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1
```

Reboot Windows after changing this setting.

Verify:

```powershell
(Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled).LongPathsEnabled
```

Expected: `1`

## 3) Install MSYS2/UCRT build dependencies

Run in VS Code terminal (or "Start Command Prompt with Ruby"):

```powershell
ridk install
ridk exec pacman -Syu --noconfirm
ridk exec pacman -Syu --noconfirm
ridk exec pacman -S --needed --noconfirm base-devel mingw-w64-ucrt-x86_64-toolchain mingw-w64-ucrt-x86_64-libffi mingw-w64-ucrt-x86_64-pkgconf
```

Verify `libffi`:

```powershell
ridk exec bash -lc "pkg-config --modversion libffi"
```

## 4) Set up Python virtual environment (optional, for validation scripts)

To run module configuration validation (`scripts/validate_modules_config.py`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip jsonschema
```

Deactivate the environment later with:

```powershell
deactivate
```

## 5) Configure local credentials

Copy the example configuration:

```powershell
Copy-Item .puppet-module-tester.local.yml.example .puppet-module-tester.local.yml
```

Edit `.puppet-module-tester.local.yml`:

```yaml
puppet_core_api_key: "<YOUR_API_KEY>"
puppet_core_source_url: "https://rubygems-puppetcore.puppet.com"
puppet_core_auth_header: "X-Api-Key"
puppet_compat_metadata_mode: "warn"
puppet_compat_target: "8-latest-maintained"
# Optional: override workspace and bundle paths (auto-defaults to C:/Temp if omitted)
# puppet_compat_workspace_dir: "C:/Temp/pmt-workspace"
# puppet_compat_bundle_path: "C:/Temp/pmt-bundle"
# puppet_compat_output_dir: "results/local"
```

Never commit this file.

**Note on paths:** Keep `puppet_compat_workspace_dir` and `puppet_compat_bundle_path` under a short root like `C:/Temp` to avoid deep-path failures in Ruby/Bundler toolchains.

## 6) Validate module configuration (optional)

To validate `config/modules.json` against the schema:

```powershell
# Activate Python venv first if created above
.\.venv\Scripts\Activate.ps1

python scripts/validate_modules_config.py --config config/modules.json --schema config/modules.schema.json
```

Expected output: `OK: config/modules.json is valid against config/modules.schema.json`

## 7) Run unit tests locally

From repo root:

```powershell
ruby scripts/run_local.rb
```

Reports are written to:

- `results/local/compatibility-report.json`
- `results/local/compatibility-summary.md`
- `results/local/artifacts/<module>/` — stage logs per module

## 8) Acceptance tests

Acceptance tests require Docker to build and run a Linux container with Beaker. **On Windows, this typically requires one of:**

- **WSL2 (Windows Subsystem for Linux 2)** with Docker Desktop configured for WSL2 backend
- **Hyper-V** with Docker Desktop
- A separate Linux VM with Docker accessible from Windows

To run acceptance tests (after Docker is configured):

```powershell
ruby scripts/run_local.rb --allow-acceptance
```

**Note:** Without Docker configured, the runner will skip acceptance tests and report them as inconclusive. Unit tests will still run.

## 9) If bootstrap fails

1. Clean the module bundle and rerun:

```powershell
Remove-Item -Recurse -Force C:\Temp\pmt-workspace -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force C:\Temp\pmt-bundle -ErrorAction SilentlyContinue
ruby scripts/run_local.rb
```

2. If native extension errors persist (for example `fiddle`/`libffi`), rerun package install step in section 3.
3. Confirm long paths are enabled and that runtime paths are short (`C:\Temp\...`) while keeping repo path reasonably short (for example `C:\GitHub\puppet-module-tester-poc`).

## Notes

- The runner uses split gem sources by default:
  - Puppet/Facter from `https://rubygems-puppetcore.puppet.com`
  - Vox/community test gems from `https://rubygems.org`
- Harness errors make the runner exit non-zero by design so failures are visible in CI.
