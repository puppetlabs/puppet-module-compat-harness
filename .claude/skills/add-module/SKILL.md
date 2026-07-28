---
name: add-module
description: Add a new Puppet module to the compatibility harness. Use whenever the user asks to add, onboard, or intake one or more modules into the test matrix — e.g. "add voxpupuli/puppet-foo", "onboard saz/puppet-bar", "put these modules in the harness" — or hands you a GitHub issue URL requesting a module addition (e.g. "handle https://github.com/puppetlabs/puppet-module-compat-harness/issues/9"). Handles GitHub issue intake, upstream repo inspection, acceptance disposition, prereq discovery, docker_mode, ordering, and schema validation for config/modules.json.
---

# Add a module to the compatibility harness

Onboard one or more Puppet modules into `config/modules.json` following the rules in
[AGENTS.md](../../../AGENTS.md). **AGENTS.md is authoritative** — this skill is the
operational checklist; read AGENTS.md's "Module Addition Workflow", "Mandatory Prereq
Discovery", and "Ordering Rule" sections if any step is ambiguous.

## Before you start

Identify the target repo and ref before anything else.

- **Direct input** (`saz/puppet-timezone`, a full repo URL, a module name): expand shorthand
  to a full `https://github.com/...` URL.
- **GitHub issue URL** (e.g. `https://github.com/puppetlabs/puppet-module-compat-harness/issues/9`):
  treat it as a module-request ticket and crawl it first — see
  [Accepting a GitHub issue as input](#accepting-a-github-issue-as-input) below — then
  continue here with the repo/ref it resolves to.

If no ref is given, note that the runner treats a missing `ref` as `main` — but many modules
default to `master`, so **verify the default branch** during inspection and set `ref`
explicitly when it isn't `main`.

## Accepting a GitHub issue as input

These request issues aren't backed by a strict issue template (free-form body text), so treat
this as extraction, not form-parsing.

1. **Fetch the issue.** Prefer `gh issue view <number> --repo <owner>/<repo> --json
   title,body,url,labels` when the `gh` CLI is available and authenticated; otherwise fetch the
   issue URL directly (e.g. via WebFetch) and extract the same fields (title, body, labels).
2. **Extract the target module repo from the body.** Look for, in priority order:
   - A `github.com/...` link that is **not** this harness repo itself — that's the module's
     upstream repo and becomes `repo`. If it's shorthand in prose (e.g. "add saz/puppet-timezone")
     instead of a link, expand it the same way as direct input above.
   - A Puppet Forge link (`forge.puppet.com/modules/<owner>/<name>`) — useful to confirm the
     module name/id and maintainer, but the GitHub link is the source of truth for `repo`.
   - Any explicit ref/branch mentioned in prose; otherwise fall through to the default-branch
     verification below.
3. **Resolve ambiguity, don't guess.** If the body only has a Forge link (no GitHub link), open
   the Forge page and follow its "Repository"/"Project Homepage" link to find the source repo.
   If the module still can't be pinned to one repo, ask the user rather than assuming.
4. Proceed to Step 1 below using the resolved repo/ref.
5. Reference the originating issue number in your final report (Step 5) so the user can
   cross-link it (e.g. "resolves the request in #9"). Don't comment on or close the issue
   yourself — that's a shared-state action outside this skill's scope unless the user asks.

## Step 1 — Inspect the upstream repo (never skip)

You MUST fetch and analyze the remote repository, not the local workspace. Use the GitHub
API / WebFetch / a shallow clone. At the target ref, inspect at minimum:

- `metadata.json` — Puppet version requirement, dependencies, maintainer, deprecation status.
  Note: many modern modules declare an `openvox` requirement instead of `puppet`. That is
  **expected and fine** — this harness swaps OpenVox for Puppet Core (see AGENTS.md "Project
  Purpose"). A missing `puppet` requirement is only a metadata *warning*, never a reason to
  refuse the module.
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
added/omitted, any assumptions, and required follow-up if evidence was partial. If the input
was a GitHub issue, include a cross-link back to it (e.g. "resolves #9").

## Notes

- Don't add anything listed in `KNOWN_INCOMPATIBLE.md` without new evidence.
- If inspection reveals the module is genuinely incompatible (legacy toolchain, dead deps, or
  *genuinely* OpenVox-only), stop and use the `mark-incompatible` skill instead of adding it.
  **"Genuinely OpenVox-only" is narrow** — see AGENTS.md "Project Purpose". A module that merely
  declares `openvox` in `metadata.json`/`Gemfile` is a normal input (the harness swaps in Puppet
  Core); that alone is a *warning*, not an incompatibility. Reserve mark-incompatible for a hard
  runtime refusal of non-OpenVox (e.g. `puppet-choria`) or a module whose purpose is installing
  OpenVox (e.g. `puppet-openvox_bootstrap`). When unsure, add it and let a run produce evidence.
- For a narrow CI verification run, use the workflow `modules_json` input with just the new
  entry (see AGENTS.md "Quick CI Scope Test").
