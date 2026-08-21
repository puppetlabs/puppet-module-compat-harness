# AGENTS Guide

This file is for coding agents working in this repository.

## Scope

- Use this guide for automated edits related to module intake, CI behavior, and compatibility test execution.
- Keep user-facing documentation in `README.md` and contributor process in `CONTRIBUTING.md`.

## Project Purpose (read first)

This harness exists to answer one question per module: **does it work with Puppet Core?** To
find out, the runner deliberately **swaps OpenVox for Puppet Core** and runs the module's own
tests — `lib/module_tester/bootstrap.rb` comments out the module's runtime gem declarations and
pins `gem 'puppet', '= <version>'` from the Puppet Core source.

Because of this, a module declaring **`openvox` (not `puppet`) in `metadata.json`/`Gemfile` is
the NORMAL, expected input** — most modern Vox Pupuli modules do, since their upstream CI
targets OpenVox. An `openvox` declaration is **not** an "OpenVox-only" incompatibility, and it
must **not** be pre-emptively marked incompatible.

- A missing `puppet` requirement in `metadata.json` surfaces only as a **metadata warning**
  (`conditionally_compatible` under the default `warn` mode — see `lib/module_tester/metadata.rb`
  and `lib/module_tester/classifier.rb`). It is **never** a blocking failure or an exclusion.
- A module is **genuinely OpenVox-only** (→ use the `mark-incompatible` skill) only when it
  cannot produce a *usable* result on Puppet Core, i.e. one of:
  - it has a **hard runtime check that refuses non-OpenVox** distributions (e.g. `puppet-choria`
    raising "Choria only supports OpenVox"), or
  - its **purpose is to install/bootstrap OpenVox packages**, so even a passing test describes no
    valid Puppet Core use case (e.g. `puppet-openvox_bootstrap`).
- Merely declaring `openvox` in metadata/Gemfile, when the provider/manifests otherwise run under
  Puppet Core, is **not** sufficient to mark incompatible. When in doubt, add the module and let a
  run produce the evidence — a warning is a pass (green), only failures are red.

## Primary Files

- `config/modules.json`: module definitions used by local runs and CI matrix generation.
- `config/modules.schema.json`: schema for module config validation.
- `config/beaker/setfiles/`: Beaker host definition files (one per acceptance target, e.g. `el9.yml`).
- `scripts/validate_modules_config.py`: local schema validation helper.
- `.github/workflows/compatibility-runner-puppet8.yml` / `compatibility-runner-puppet9.yml`: CI pipeline and matrix execution, one self-contained caller per Puppet major (see `docs/puppet-core-9-dual-major-support.md` §4). They are deliberate near-copies — a diff between them should show only the profile name, concurrency-group suffix, `puppet-major` input, and cron hour; anything else is drift. Shared prepare/publish logic lives in `.github/actions/prepare-test-matrix` and `.github/actions/publish-compatibility-results` — see that doc's §12 for why these are composite actions, not a reusable workflow.
- `profiles/puppet_profiles.json`: profile constraints used by the runner.
- `docs/architecture-flow.md`: end-to-end architecture diagram and stage reference. Must be kept in sync with runner logic, classification rules, and CI workflow changes.

## Module Addition Workflow (Agent)

0. A request may arrive as a GitHub issue URL instead of a repo name (the `add-module` skill
   handles crawling it for the target repo/ref — see `.claude/skills/add-module/SKILL.md`).
   Resolve it to a concrete repo/ref before starting step 1; do not guess the target repo from
   the issue title alone if the body is ambiguous.
1. Inspect the target module repository first (do not skip this step). If the module is not present locally, agents MUST fetch and analyze the remote repository (e.g., via GitHub API or by cloning/downloading the repo) to discover acceptance tests and other required files. Acceptance test discovery must NOT be limited to the local workspace.
2. Add a module object under `modules` in `config/modules.json`.
3. **Insert Vox Pupuli modules first and alternative maintainers second.** Keep all `voxpupuli/*` entries grouped at the top and sorted alphabetically by repo name (the segment after the final `/`, lowercase, case-insensitive). Keep all non-`voxpupuli` entries grouped at the bottom and sorted alphabetically by explicit `id`. This preserves a clean primary Vox Pupuli block while keeping alternative maintainer jobs easy to identify in the GitHub Actions UI.
4. Set `repo` (required) and `acceptance` (required — see below), optionally `ref`, `id`, `os`, and `prereqs`.
5. Default behavior when omitted:
   - `ref`: treated as `main` by runner logic.
   - `os`: defaults to `ubuntu-latest` in workflow behavior.
  - `id`: derived from repo name for `voxpupuli/*` entries when omitted.
6. Validate against schema before proposing completion.
7. Do **not** hand-edit [Available Acceptance Tests](./docs/available-acceptance-tests.md) — it is auto-generated from `config/modules.json` by `scripts/render_acceptance_audit.py` (CI regenerates and commits it). The module's `acceptance` block (status + reason) is the source of truth for that audit, so getting the disposition right in step 4 above is what populates the doc. You may run `python scripts/render_acceptance_audit.py` locally to preview the result.

### Acceptance disposition (required)

Every module must declare an `acceptance` block with an explicit `status` — this is what lets the status ledger and dashboard distinguish "no acceptance tests exist" from "tests exist but the harness can't run them." Choose the status from what you found inspecting the upstream repo:

- **`running`** — the repo has acceptance tests and we run them in CI. Set `"enabled": true` and provide `targets`. (`enabled` must be `true` iff `status` is `running`.)
  ```json
  "acceptance": { "enabled": true, "status": "running", "targets": [ { "name": "el9", "setfile": "el9" } ] }
  ```
- **`blocked`** — acceptance tests exist upstream but cannot run in this harness due to a hard technical limitation (kernel params, multi-container topology, non-Docker OS, etc.). Set `"enabled": false` and a `reason`. Blocked modules are automatically excluded from the generated `KNOWN_COMPATIBLE.md` (they have not had all available tests exercised) — setting the `status` correctly is what drives that; do not hand-edit `KNOWN_COMPATIBLE.md`, it is generated.
- **`pending`** — acceptance tests exist upstream but are not yet wired into the harness (e.g. Windows-only targets we don't have runners for). Set `"enabled": false` and a `reason`.
- **`none`** — the upstream repo has no acceptance tests. Unit coverage alone is full coverage. Set `"enabled": false`; no `reason` needed.
  ```json
  "acceptance": { "enabled": false, "status": "none" }
  ```

`blocked` and `pending` require a `reason`, which is the source of truth for the acceptance-test audit. When a module is `blocked`/`pending`, add its reason here rather than only in prose docs.

### Deprecation flag

If the upstream module is no longer maintained (deprecated/archived by its maintainer or on the Forge), set `"deprecated": true` on the module entry. This is **orthogonal to compatibility** — a deprecated module can still be fully compatible and remains in the test matrix; the flag only drives a ⚠️ badge and a "Deprecated" count in `STATUS.md`. Omit the field (or set `false`) for maintained modules. Do not hand-edit `STATUS.md`.

### Ordering Rule

- Primary block: all `voxpupuli/*` entries, sorted by the last path segment of `repo` (for example `puppet-archive` from `https://github.com/voxpupuli/puppet-archive`), compared case-insensitively.
- Secondary block: all non-`voxpupuli` entries, sorted by explicit `id`, compared case-insensitively.
- Every non-`voxpupuli` entry must set `id` explicitly.
- This applies to every entry — new additions, reorderings, duplicate-maintainer support, and cleanup edits.
- If you discover existing entries out of order during an edit, fix the order in the same change.
- When adding an alternative-maintainer version of a module already present from Vox Pupuli or another maintainer, append it to the non-`voxpupuli` block with a disambiguating `id` that clearly identifies the maintainer.

## Decision Rules

- Set `os` only when a module truly requires a specific runner image.
- Use `windows-latest` for Windows-only modules/providers.
- Use `macos-latest` only when explicitly required.
- Omit `os` for general modules to keep Ubuntu as default.
- Do not guess system package prerequisites.
- Determine `prereqs` from repository evidence before finalizing a module addition.
- Omit `id` for `voxpupuli/*` entries unless stable custom naming is needed in artifacts/reporting.
- Set explicit `id` for every non-`voxpupuli` entry. Use a maintainer-qualified value so matrix job names remain unambiguous when duplicate module names exist across maintainers.
- Set `docker_mode` to `systemd` on acceptance targets only when the module's acceptance tests assert service running/enabled state via systemd (e.g. `is_expected.to be_running`, `is_expected.to be_enabled`). Evidence: check `spec/acceptance/` for `be_running` or `be_enabled` matchers on Service resources.
- Default `docker_mode` is `sshd` — faster, more portable, and avoids privileged containers. Only escalate to `systemd` when tests require it.

## Mandatory Prereq Discovery


Before proposing a new module entry, agents must fetch and analyze the target repository at the selected `ref` (or default branch if `ref` is omitted). This includes searching for acceptance tests (e.g., files under `spec/acceptance/` or similar) in the remote repository if not present locally. Agents must not assume the absence of acceptance tests based solely on the local workspace contents.

Minimum files/signals to inspect:

- `Gemfile` and `Gemfile.lock`
- `Rakefile` and custom rake tasks used by validate/spec/test
- `metadata.json`
- `.fixtures.yml` or `.sync.yml` (if present)
- `spec/spec_helper.rb`, `spec/spec_helper_local.rb`, and unit/integration specs under `spec/`
- acceptance helpers/assets under `spec/acceptance/` or `acceptance/`
- Any scripts invoked by tests (for example in `script/`, `tasks/`, or CI config)

What to extract:

- Native/system tools and libraries required by tests or providers.
- OS-specific requirements (Linux/macOS/Windows) that imply package-manager entries.
- Commands in specs/rake tasks that call external binaries.

How to write `prereqs`:

- Add only package-manager keys supported by schema (`apt`, `dnf`, `yum`, `apk`, `brew`, `choco`, `pacman`).
- Include only non-empty unique package names.
- If repo evidence shows no system prereqs, `prereqs` may be omitted.
- If evidence is inconclusive, run a scoped CI attempt and derive prereqs from failure logs before finalizing.

Evidence requirement in agent response:

- Summarize which repository files were inspected.
- State why `prereqs` were added or omitted.
- Call out any assumptions and required follow-up if evidence was partial.

## Validation Checklist

Run:

```bash
python -m pip install jsonschema
python scripts/validate_modules_config.py --config config/modules.json --schema config/modules.schema.json
```

Expected result:

```text
OK: config/modules.json is valid against config/modules.schema.json
```

Also confirm:

- No duplicate `id` values.
- No unexpected module keys outside schema.
- Package lists in `prereqs` are non-empty strings without duplicates.

## Quick CI Scope Test

When you need a narrow CI run, use workflow input `modules_json` with only new or changed entries, for example:

```json
[{"repo":"https://github.com/voxpupuli/puppet-windowsfeature","ref":"master","os":"windows-latest"}]
```

## CI Behavior Notes

- Workflow validates `config/modules.json` before matrix fan-out.
- Matrix `runs-on` follows per-module `os` when set; otherwise Ubuntu default applies.
- Cross-platform prereqs are installed by package-manager keys in `prereqs` (such as `apt`, `choco`, `brew`).
- Acceptance jobs always run on `ubuntu-latest`; the SUT is a Docker container controlled by `BEAKER_SETFILE`.
- When `PUPPET_CORE_API_KEY` is set, the runner uses a **two-stage isolation model**:
  1. **Build stage** (`build_sut_image`): runs `docker build` with the API key passed as a build arg. Puppet Core agent is installed and credentials are scrubbed from repo config files in the same Dockerfile layer so they never persist in the image.
  2. **Test stage** (`acceptance`): runs untrusted module test code (Beaker/rspec) with **no secrets in the environment**. The runner strips `PUPPET_CORE_API_KEY`, `PASSWORD`, `USERNAME`, and `BUNDLE_RUBYGEMS___PUPPETCORE__PUPPET__COM` from the env before invoking tests. The setfile references the pre-built local image tag — no credentials are embedded in the setfile.
- This design ensures third-party module test code cannot exfiltrate the API key.
- Without an API key, acceptance falls back to the public FOSS puppet-agent from `yum.puppet.com` (capped at 8.10.0).

## Beaker Setfiles

- Each acceptance target in `config/modules.json` references a `setfile` by name (filename stem).
- Corresponding YAML files live under `config/beaker/setfiles/` (e.g. `el9` → `config/beaker/setfiles/el9.yml`).
- The setfile defines the Docker image and platform for the Beaker SUT.
- At runtime, the runner builds a Docker image from the base setfile parameters (image, platform, docker_image_commands) plus Puppet Core install steps, then writes a clean setfile to `workspace/.beaker-setfiles/` that references the locally-built image tag.
- The rewritten setfile contains no secrets — only the image tag and platform metadata.
- When adding a new target OS, create the setfile first, then reference it in `modules.json`.

## Architecture Diagram Maintenance

`docs/architecture-flow.md` contains a Mermaid flow diagram and supporting reference tables that describe the end-to-end pipeline. Agents must update this file when making changes to any of the following areas:

| Area changed | What to update in `architecture-flow.md` |
|---|---|
| Runner pipeline stages (`lib/module_tester/runner.rb`) | Shared pipeline stage list; diagram node labels and order |
| Bootstrap logic or Gemfile patching (`lib/module_tester/bootstrap.rb`) | Gem swap branch in diagram; Bootstrap row in stage table; Gemfile conflict override in classification table |
| Classifier state logic or precedence (`lib/module_tester/classifier.rb`) | Classification precedence list; outcome state table |
| Downgrade override rules (`lib/module_tester/adapters.rb`) | Downgrade overrides table — add, remove, or update trigger conditions and reclassification outcome |
| Guardrails checks (`lib/module_tester/guardrails.rb`) | Guardrails row in stage table |
| Acceptance adapter or Docker isolation model (`lib/module_tester/adapters.rb`, `lib/module_tester/docker.rb`) | Two-Stage Docker Isolation Model section; Docker Container Modes table; S1/S2S/S2D node labels in diagram; FOSS fallback description |
| CI workflow (`.github/workflows/compatibility-runner-puppet8.yml`, `compatibility-runner-puppet9.yml`, `.github/actions/prepare-test-matrix/action.yml`, `.github/actions/publish-compatibility-results/action.yml`) | CI: Prepare section; diagram CI subgraph |
| Reporting outputs (`lib/module_tester/reporting.rb`) | Reporting section |

### Rules for diagram edits

- Use `<br/>` for line breaks inside Mermaid node labels — **not** `\n`.
- Do not remove `classDef` declarations or the `class`/`style` assignments at the bottom of the diagram block; they encode deliberate visual highlights for `modules.json` (datasource), gem swap (gemswap), and Docker isolation (isolation/TwoStage).
- If a new architectural concept warrants a highlight, add a new `classDef` and apply it consistently.
- Keep the diagram and the prose tables in sync — if the diagram changes, the corresponding prose section must also change.

## Editing Expectations for Agents

- Keep README user-focused and free from agent-operational instructions.
- Keep CONTRIBUTING focused on contributor process and schema rules.
- Put agent-specific process updates in this file.

## Adding New Incompatibilities

Before ruling a module incompatible, re-read **Project Purpose** above. In particular, an
`openvox`-in-`metadata.json` declaration (with no `puppet` requirement) is a *warning*, not an
incompatibility — do not mark such a module incompatible on that basis alone. Reserve
"OpenVox-only" for the two genuine cases named there (hard runtime refusal of non-OpenVox, or a
module whose purpose is installing OpenVox).

When a module is determined to be incompatible:

1. Add an entry to the table in [KNOWN_INCOMPATIBLE.md](KNOWN_INCOMPATIBLE.md) with module name, Puppet Core version tested, status, and detailed reason
2. Remove the module from `config/modules.json` so it is no longer included in test runs
3. Include migration path guidance if applicable