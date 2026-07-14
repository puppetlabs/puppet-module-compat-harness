# Claude Code Guide

This project is a proof-of-concept external harness for testing community Puppet modules (primarily Vox Pupuli) against specific Puppet Core releases, via GitHub Actions — without modifying the source of any tested module.

## Key commands

```bash
# Install Ruby dependencies
bundle install

# Validate modules config
python scripts/validate_modules_config.py --config config/modules.json --schema config/modules.schema.json

# Run locally (replace values as needed)
ruby bin/puppet-module-tester \
  --modules-file config/modules.json \
  --profiles-file profiles/puppet_profiles.json \
  --profile 8-latest-maintained \
  --metadata-mode warn \
  --workspace-dir workspace \
  --output-dir results/local
```

## Tech stack

- **Ruby 3.2.x** — core runner (`lib/`, `bin/`, `scripts/*.rb`)
- **Python 3.8+** — validation and reporting scripts (`scripts/*.py`)
- **Bundler 2.5.22** — pinned per profile in `profiles/puppet_profiles.json`
- **PDK** (Puppet Development Kit) — primary test execution path; Rake is the fallback
- **Beaker** — acceptance testing framework (Docker-based SUT)
- **GitHub Actions** — CI/CD platform

## Project layout

```
bin/puppet-module-tester          # CLI entry point
lib/module_tester/
  runner.rb                       # Per-module pipeline (clone → discover → bootstrap → test → classify → report)
  bootstrap.rb                    # Gemfile normalization and patching
  adapters.rb                     # PDK/Rake/Beaker execution
  docker.rb                       # Docker image build for acceptance SUT
  guardrails.rb                   # Safety assertions (puppet gem version, OpenVox check)
  classifier.rb                   # Maps outcome to: pass, warning, fail, harness_error, not_compatible, inconclusive
  metadata.rb                     # metadata.json Puppet version validation
  reporting.rb                    # JSON + Markdown output
config/
  modules.json                    # Module definitions (primary intake file)
  modules.schema.json             # JSON Schema for modules.json
  beaker/setfiles/                # One YAML per acceptance target OS (el9, ubuntu24, debian12, …)
profiles/puppet_profiles.json     # Puppet Core version pins per profile
scripts/
  build_matrix.rb                 # Generates CI fan-out matrix
  validate_modules_config.py      # Schema validation
  classify_module_result.py       # Per-job status recording
  summarize_module_statuses.py    # Final aggregated report
  update_ledger.py                # Merge run results into status/ledger.json (upsert + reconcile)
  render_status_dashboard.py      # Render STATUS.md fleet dashboard from the ledger
  ledger_lib.py                   # Shared id-derivation + config/KNOWN_* parsing
status/ledger.json                # Persistent per-module status ledger (committed by CI)
STATUS.md                         # Generated fleet dashboard (do not hand-edit)
.github/
  workflows/compatibility-runner.yml   # Main CI pipeline
  actions/run-module-test/action.yml   # Composite action used per matrix job
docs/
  architecture-flow.md            # Mermaid diagram + stage reference (keep in sync with code)
  available-acceptance-tests.md   # Audit of which modules have acceptance tests
AGENTS.md                         # Operational rules for coding agents (module intake, CI rules, architecture maintenance)
CONTRIBUTING.md                   # Contributor process and schema rules
KNOWN_INCOMPATIBLE.md             # Modules tested and found incompatible with Puppet Core 8
KNOWN_DEPRECATED.md               # Archived/deprecated modules
```

## Architecture overview

The runner executes a sequential per-module pipeline:

1. **Clone** — git clone at pinned ref
2. **Discover** — detect PDK/Rake, find acceptance tests, read `metadata.json`
3. **Verify Auth** — confirm gem source is reachable
4. **Bootstrap** — normalize Gemfile puppet/facter pins, run `bundle install`; auto-patch and retry once on conflict
5. **Guardrails** — assert puppet gem version matches target, check for OpenVox
6. **Test** — PDK first, Rake fallback; acceptance tests run in Docker (two-stage isolation)
7. **Classify** — map stdout/exit code to a result state
8. **Report** — write `compatibility-report.json`, `compatibility-summary.md`, per-stage logs

### Two-stage Docker isolation (acceptance tests)

When `PUPPET_CORE_API_KEY` is set:
- **Stage 1 (build)**: Docker build with API key as a build arg; key is scrubbed from the image in the same layer.
- **Stage 2 (test)**: Beaker runs with API key and other secrets stripped from the environment. Untrusted module test code cannot exfiltrate the key.

Without an API key, acceptance falls back to FOSS puppet-agent (capped at 8.10.0).

## Configuration

**Local credentials** (never commit): `.puppet-module-tester.local.yml`
```yaml
puppet_core_api_key: "your-key"
puppet_core_source_url: "https://rubygems-puppetcore.puppet.com"
puppet_compat_metadata_mode: "warn"
puppet_compat_target: "8-latest-maintained"
```

**Key environment variables:**
- `PUPPET_CORE_API_KEY` — required for private Puppet Core artifacts
- `PUPPET_COMPAT_METADATA_MODE` — `warn` (default) or `fail`
- `PUPPET_SPLIT_SOURCES=true` — Puppet/Facter from private source; community gems from rubygems.org
- `PUPPET_ENFORCE_EXACT_PUPPET_VERSION=true`

## Agent operational rules

See **AGENTS.md** for the full set of rules governing module intake, ordering, prereq discovery, beaker setfile management, and architecture diagram maintenance. Key points:

- Vox Pupuli entries go first in `modules.json`, sorted alphabetically by repo name segment. Non-voxpupuli entries go second, sorted by explicit `id`.
- Every non-`voxpupuli` entry must have an explicit `id`.
- Before adding a module, fetch and analyze the remote repository to discover acceptance tests — do not assume absence from local workspace.
- Run schema validation after any `modules.json` edit.
- Update `docs/architecture-flow.md` when changing runner stages, classifier logic, Docker isolation model, or CI workflow.
- When a module is found incompatible: add to `KNOWN_INCOMPATIBLE.md`, remove from `modules.json`.

## Output locations

- Local runs: `results/local/`
- CI artifacts: downloaded to `results/github/` per module matrix entry
- Per-module: `compatibility-report.json`, `compatibility-summary.md`, `.stage-*.log`

## Known constraints

- Acceptance tests require Docker (Linux containers); acceptance always runs on `ubuntu-latest` in CI.
- Ruby 3.2.x required; 3.3+ is not supported.
- Windows local development requires long-path support and MSYS2/UCRT build tools (see `README_Windows.md`).
- Modules in `KNOWN_INCOMPATIBLE.md` are excluded from `modules.json` — do not re-add them without new evidence.
