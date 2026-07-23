---
name: add-module
description: Add a new Puppet module to the compatibility harness. Use whenever the user asks to add, onboard, or intake one or more modules into the test matrix — e.g. "add voxpupuli/puppet-foo", "onboard saz/puppet-bar", "put these modules in the harness". Handles upstream repo inspection, acceptance disposition, prereq discovery, docker_mode, ordering, and schema validation for config/modules.json.
---

# Add a module to the compatibility harness

Onboard one or more Puppet modules into `config/modules.json` following the rules in
[AGENTS.md](../../../AGENTS.md). **AGENTS.md is authoritative** — this skill is the
operational checklist; read AGENTS.md's "Module Addition Workflow", "Mandatory Prereq
Discovery", and "Ordering Rule" sections if any step is ambiguous.

## Before you start

Confirm the exact repo URL and ref. If the user gave a shorthand (`saz/puppet-timezone`),
expand it to a full `https://github.com/...` URL. If no ref is given, note that the runner
treats a missing `ref` as `main` — but many modules default to `master`, so **verify the
default branch** during inspection and set `ref` explicitly when it isn't `main`.

## Step 1 — Inspect the upstream repo (never skip)

You MUST fetch and analyze the remote repository, not the local workspace. Use the GitHub
API / WebFetch / a shallow clone. At the target ref, inspect at minimum:

- `metadata.json` — Puppet version requirement, dependencies, maintainer, deprecation status
- `Gemfile` / `Gemfile.lock` — legacy/incompatible pins
- `Rakefile`, `.fixtures.yml`, `spec/spec_helper.rb`
- `spec/acceptance/` **and** `acceptance/` — do acceptance tests exist?
- Any external binaries invoked by specs/rake tasks (implies `prereqs`)

Record which files you inspected — you'll summarize this in your final response (AGENTS.md
requires an evidence summary).

## Step 2 — Decide the fields

Build a module object. Required: `repo`, `acceptance`. Optional: `ref`, `id`, `os`,
`deprecated`, `prereqs`.

**Acceptance disposition** (`acceptance.status`, required — pick from what you found):

| status | enabled | needs | when |
|---|---|---|---|
| `running` | `true` | `targets[]` | acceptance tests exist AND run in this harness |
| `blocked` | `false` | `reason` | tests exist but a hard limitation stops them (kernel params, multi-container, non-Docker OS) |
| `pending` | `false` | `reason` | tests exist but not yet wired up (e.g. Windows-only targets) |
| `none` | `false` | — | no acceptance tests exist upstream |

Rules: `enabled` must be `true` **iff** `status` is `running`. `blocked`/`pending` MUST
have a `reason` (it's the source of truth for the generated acceptance audit). Do not
hand-edit `docs/available-acceptance-tests.md`, `KNOWN_COMPATIBLE.md`, or `STATUS.md` —
they are generated.

**Targets** (only for `running`): each is `{ "name": "el9", "setfile": "el9" }` where
`setfile` is a filename stem under `config/beaker/setfiles/`. If the OS you need has no
setfile yet, create it first. Set `docker_mode: "systemd"` on a target ONLY when acceptance
specs assert service state via systemd (`be_running` / `be_enabled` on Service resources);
default `sshd` otherwise.

**prereqs** — only from repo evidence. Supported keys: `apt`, `dnf`, `yum`, `apk`, `brew`,
`choco`, `pacman`. Non-empty, unique package names. Omit if no system prereqs found. If
evidence is inconclusive, run a scoped CI/local attempt and derive from failure logs before
finalizing. Do not guess.

**os** — omit for general modules (Ubuntu default). Set `windows-latest` for Windows-only,
`macos-latest` only when explicitly required.

**deprecated** — set `true` if upstream is archived/deprecated. Orthogonal to compatibility:
a deprecated module still stays in the matrix; the flag only drives a badge/count in STATUS.md.

**id** — omit for `voxpupuli/*` (derived from repo). REQUIRED and explicit for every
non-voxpupuli entry; use a maintainer-qualified value (e.g. `saz-timezone`) so job names stay
unambiguous.

## Step 3 — Insert in the correct order

Two blocks in `config/modules.json`:

1. **Primary** — all `voxpupuli/*` entries, sorted by the last path segment of `repo`
   (case-insensitive). e.g. `puppet-archive` from `.../voxpupuli/puppet-archive`.
2. **Secondary** — all non-`voxpupuli` entries, sorted by explicit `id` (case-insensitive).

If you spot existing entries out of order while editing, fix them in the same change.

## Step 4 — Validate

```bash
python scripts/validate_modules_config.py --config config/modules.json --schema config/modules.schema.json
```

Expect: `OK: config/modules.json is valid ...`. Also confirm no duplicate `id`s and no
prereq duplicates. Optionally preview the audit:

```bash
python scripts/render_acceptance_audit.py
```

## Step 5 — Report

Summarize: files inspected upstream, chosen `acceptance.status` + why, why `prereqs` were
added/omitted, any assumptions, and required follow-up if evidence was partial.

## Notes

- Don't add anything listed in `KNOWN_INCOMPATIBLE.md` without new evidence.
- If inspection reveals the module is incompatible (OpenVox-only, legacy toolchain, dead
  deps), stop and use the `mark-incompatible` skill instead of adding it.
- For a narrow CI verification run, use the workflow `modules_json` input with just the new
  entry (see AGENTS.md "Quick CI Scope Test").
