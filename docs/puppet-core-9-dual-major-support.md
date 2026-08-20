# Design: Dual-Major Compatibility Testing (Puppet Core 8 + 9)

**Status:** Proposed — not yet implemented
**Author:** (harness maintainers, via planning discussion with Claude Code)
**Date:** 2026-08-11

**Builds on:** [`docs/lean-testing-and-status-ledger-design.md`](lean-testing-and-status-ledger-design.md)
(ledger, lean matrix, `KNOWN_COMPATIBLE.md` generation). This document extends that
design to a second dimension — Puppet major version — rather than replacing it.
Section references like "§4.2 of the lean-testing design" point back there.

---

## 1. Motivation

Puppet Core 9 is about to ship. The harness currently tests exactly one Puppet
major at a time (two profiles, both major 8: `8-latest-maintained`,
`8-previous-maintained`). We need to validate every active module against **both**
Puppet Core 8 and Puppet Core 9 going forward, and expect real divergence: some
modules will pass on 8 and fail on 9 (or vice versa, though that direction is
less likely in practice).

This is not additive to the existing design — it breaks an assumption baked into
four layers:

1. **`status/ledger.json`** stores one flat `unit`/`acceptance` block per module,
   keyed only by module id. [`update_ledger.py`](../scripts/update_ledger.py)
   groups incoming rows `by_id.setdefault(row['id'], [])` and does a flat
   `entry['unit'] = {...}` assignment — a second major's result **silently
   overwrites** the first's. This is the central bug this design fixes.
2. **CI workflow** takes a single `profile` dispatch input and runs one fleet-wide
   pass per trigger.
3. **Artifact/output naming** (`compatibility-${module.id}-unit`,
   `o/${module.id}`) has no major/profile dimension, so two jobs for the same
   module under two majors would collide on artifact name within one workflow run.
4. **Dashboard rendering** (`STATUS.md`, `KNOWN_COMPATIBLE.md`) assumes one
   `puppet_core_version` per module — it cannot express "compatible on 8, not on
   9" today.

### Non-goals

- **Not pinning actual Puppet Core 9 version numbers here.** `profiles/puppet_profiles.json`
  gets new `9-*` profile entries once real version numbers are available; this
  design only fixes the *shape* of the pipeline around them.
- **Not changing the per-module runner pipeline**, beyond one narrow, now-confirmed
  exception (§8): the harness's hardcoded Ruby pin must move from 3.2 to 3.4.
  `lib/module_tester/runner.rb`, `bootstrap.rb`, `metadata.rb`, `guardrails.rb`, and
  `classifier.rb` are otherwise already generic and profile-driven (they read
  `puppet_core_version`, `facter_version`, `puppet_major`, `gem_source_mode` off
  whichever profile object is passed in) and need no further changes.
- **Not making Ruby version vary per major/profile.** An earlier version of this
  plan assumed `ruby_version` might need to differ between the 8-series and
  9-series profiles (each profile entry already carries the field). Confirmed via
  the private gem source (§8): Ruby 3.4 satisfies both majors' `puppet` gemspec
  constraints simultaneously, so this stays a single shared harness-wide pin, not
  a per-profile/per-major fan-out.
- **Not splitting `profiles/puppet_profiles.json` per major.** Considered and
  rejected — see §5.2.

---

## 2. The three framing questions, answered

**Is "compatible on 8, failing on 9" a single pass/fail verdict?**
No. Track compatibility **per major, independently**, all the way through the
ledger and dashboard. There is no combined verdict — a module's Puppet 8 status
and Puppet 9 status are reported side by side, never collapsed into one.

**One workflow run per trigger, or two?**
**Two thin trigger workflows, one shared reusable pipeline.** See §4. This gives
Puppet 8 and Puppet 9 independent run history, independent status visibility, and
independent failure blast radius (a Puppet 9 regression does not turn the Puppet 8
run red) — without duplicating the actual pipeline logic, which lives once in a
reusable workflow.

**Will they collide writing to the same file?**
Yes, under the *current* ledger schema — and that was true even within a single
run once profile/major becomes another axis, not just across two separately
triggered runs. The fix (per-major ledger keys, §3) removes the collision at its
root; a shared `concurrency:` group on just the publish step (§4.3) removes the
remaining cross-run git-push race.

---

## 3. Ledger schema v2 — per-major nesting

Extends §4.2 of the lean-testing design. Each module entry gains a
`puppet_majors` map; everything that varies by major moves under it. Everything
that does **not** vary by major (repo location, disposition, deprecation) stays
at the module level, because those are config-driven facts about the module, not
outcomes of a test run.

```jsonc
{
  "schema_version": 2,
  "modules": {
    "puppet-nginx": {
      "repo": "https://github.com/voxpupuli/puppet-nginx",
      "ref": "master",
      "disposition": "active",
      "deprecated": false,
      "acceptance_configured": true,
      "acceptance_status": "running",

      "puppet_majors": {
        "8": {
          "puppet_core_version": "8.20.0",
          "unit": {
            "class": "clean",
            "compatibility_state": "compatible",
            "tested_at": "2026-08-10T02:11:00Z",
            "last_run_id": "1234567890",
            "last_harness_sha": "26086a7"
          },
          "acceptance": {
            "class": "clean",
            "targets": { "el9": "clean" },
            "tested_at": "2026-08-10T02:19:00Z"
          },
          "metadata_status": "supported",
          "dependency_status": "none",
          "documentation_status": "none",
          "coverage_state": "unit+acceptance"
        },
        "9": {
          "puppet_core_version": "9.0.0",
          "unit": {
            "class": "failure",
            "compatibility_state": "not_compatible",
            "tested_at": "2026-08-10T02:31:00Z",
            "last_run_id": "1234567999",
            "last_harness_sha": "26086a7"
          },
          "metadata_status": "unsupported_by_metadata",
          "coverage_state": "unit-failing"
        }
      }
    }
  }
}
```

### 3.1 `update_ledger.py` changes

- **Group incoming rows by `(module_id, puppet_major)`**, not `module_id` alone.
  `upsert_results` writes into `entry['puppet_majors'][major]['unit']` /
  `['acceptance']` instead of the flat top-level fields.
- `coverage_state` / `is_fully_compatible` (currently module-level functions in
  `render_status_dashboard.py`) become **per-major** functions, evaluated once
  per `puppet_majors[major]` entry.
- `disposition`, `deprecated`, `acceptance_configured`, `acceptance_status` stay
  module-level, reconciled against `config/modules.json` + `KNOWN_*` exactly as
  today (§4.4 of the lean-testing design) — these describe whether/how the
  module is tested at all, not a per-major outcome.
- **Migration:** bump `schema_version` to `2`; write a one-time migration script
  that lifts every existing entry's flat `unit`/`acceptance`/`puppet_core_version`
  into `puppet_majors["8"]` (today's data is implicitly all major 8), so
  accumulated `tested_at` history and staleness tracking survive the schema
  change instead of resetting.

### 3.2 Where the `puppet_major` value comes from

`profiles/puppet_profiles.json` entries already carry a `puppet_major` field
(`"puppet_major": 8`) — no profile schema change needed beyond adding the new
`9-*` profile entries once real version numbers exist.
[`classify_module_result.py`](../scripts/classify_module_result.py) already
resolves `puppet_core_version` from the profile name (`resolve_puppet_version`);
extend it to resolve and stamp `puppet_major` the same way, so it lands in
`module-status.json` and `update_ledger.py` never has to parse a major out of a
profile-name string.

---

## 4. CI topology — two thin trigger workflows, one reusable pipeline

### 4.1 Structure

- **`.github/workflows/_compatibility-runner-reusable.yml`** (new) — a
  `workflow_call`-triggered workflow containing today's `prepare` →
  `test_unit`/`test_acceptance` → `publish` job graph, parameterized by which
  profile(s) to test (input, e.g. `profiles: '["9-latest-maintained"]'`) and which
  major it represents (input, e.g. `major: "9"`, threaded into `detect_changes.py`
  and `build_matrix.rb`). This is where essentially all existing pipeline logic
  continues to live — **exactly once**.
- **`.github/workflows/compatibility-runner-puppet8.yml`** (new, thin) — its own
  `schedule`/`workflow_dispatch` triggers, calls the reusable workflow with
  `profiles: ["8-latest-maintained", "8-previous-maintained"]`, `major: "8"`,
  `secrets: inherit`.
- **`.github/workflows/compatibility-runner-puppet9.yml`** (new, thin) — same
  shape, `profiles: ["9-latest-maintained", ...]`, `major: "9"`.
- `.github/workflows/compatibility-runner.yml` (current single file) is retired /
  replaced by the three files above.

Each caller file is on the order of the trigger block plus one job that does
`uses: ./.github/workflows/_compatibility-runner-reusable.yml`. **No pipeline
logic is duplicated** — the two files exist only to get independent triggers,
independent Actions-tab history/status badges, independent manual-dispatch forms
(each pre-scoped to the right profile choices), and independent concurrency
groups, without conditional branching on `github.event.schedule` cron strings
inside one shared file. (A single-file alternative was considered and rejected —
see §4.4.)

### 4.2 Concurrency

- **Test-phase jobs**: each caller uses its own concurrency group
  (`compat-8-${{ github.ref }}` / `compat-9-${{ github.ref }}`), so a Puppet 8 run
  and a Puppet 9 run proceed **in parallel** — no 2x wall-clock penalty from
  serializing unrelated majors.
- **Publish job** (ledger merge + commit + push): both callers pass the **same**
  concurrency group name into the reusable workflow's publish job (e.g.
  `compat-ledger-${{ github.ref }}`) via a job-level `concurrency:` block. This
  serializes only the ledger-write-and-push step across both workflows — the
  actual piece that would otherwise race on `git push status/ledger.json`.

### 4.3 Artifact naming

Because Puppet 8 and Puppet 9 now run as **separate workflow runs**, GitHub
Actions artifact names (which are unique per-run, not per-repo) no longer need a
cross-major suffix to avoid collision — that concern from earlier drafts of this
plan is resolved for free by the topology change. A profile-in-name suffix is
still needed **within** a major's own run if that major ever has multiple
profiles active at once (e.g. `9-latest-maintained` and `9-previous-maintained`
both in the same matrix) — same reason `8-latest-maintained`/`8-previous-maintained`
would need it if they ever ran in one matrix together, which they don't today
(only one profile runs per invocation currently).

### 4.4 Alternative considered and rejected: one file, two schedules

A single workflow file with two `schedule:` cron entries, branching on
`github.event.schedule` to pick the profile set, was considered. Rejected because:

- Actions-tab history and status badges are organized by workflow file — one file
  means both majors' runs interleave in one history list and share one badge;
  telling them apart requires opening each run.
- `workflow_dispatch` would need a "which major" selector instead of two
  pre-scoped dispatch forms — easier to fat-finger a manual run against the wrong
  profile set.
- Branching on the literal cron string is implicit and fragile (a cron typo
  silently breaks the routing with no error).
- The concurrency-group name would need to be a conditional expression
  distinguishing "scheduled-8" from "scheduled-9" from "dispatch-either," which is
  exactly the kind of logic that's easy to get subtly wrong.

None of these costs buy anything, since the reusable-workflow split already
eliminates the pipeline-duplication concern that would otherwise justify
minimizing file count.

---

## 5. Lean matrix — keeping leanness independent per major

This is the requirement that most directly needs validating: **a Puppet 9 run
failing modules must not cause Puppet 8 to lose its leanness, and vice versa.**

### 5.1 Per-major ledger reads

`detect_changes.py` (§3 of the lean-testing design) must read the **caller's own
major's slice** of the ledger for every per-module decision:

- `coverage_state` → `modules[id].puppet_majors[major].coverage_state`, not a
  module-level field.
- `last_tested` (staleness) → `tested_at` fields under
  `puppet_majors[major].unit` / `.acceptance`, not top-level.

With this, the Puppet 9 caller's `NOT_GREEN_STATES` check only ever sees major
9's own coverage state — a module failing on 9 keeps getting re-included on every
9 run regardless of how green it is on 8, and once it goes green on 9 (and isn't
stale, and has no upstream commit), it drops out of the 9 matrix on its own. The
Puppet 8 caller never sees major 9's state at all, so it keeps getting leaner on
its own track no matter what happens on 9. This is the core mechanism; everything
else in this section is about not accidentally undermining it.

Module-level signals — staleness *policy* (the `STALE_DAYS` threshold itself),
and upstream-commit detection on the module's own repo/ref — are correctly
**shared** across majors: a module's own upstream activity is a legitimate reason
to retest it on both majors independently, and both callers already do that
independently since they run `detect_changes.py` separately.

### 5.2 `profiles/puppet_profiles.json` stays a single shared file

An earlier draft of this plan proposed splitting the profiles file per major, to
stop a Puppet-9-only version bump from tripping `run_all=true` on the Puppet 8
workflow too (via the `profiles` entry in `detect_changes.py`'s material-path
list). **Rejected**: in practice, 8.x and 9.x profile bumps land together far
more often than not (paired releases), so both workflows correctly needing a full
run when the shared profile file changes is the expected behavior, not a defect.
Splitting the file would add a file to keep in sync for a benefit that mostly
doesn't materialize. `profiles/puppet_profiles.json` is unchanged in structure —
it just gains `9-*` entries alongside the existing `8-*` ones.

### 5.3 The real remaining leak: `.github/` material-path matching

Once the reusable-workflow split (§4) exists, `.github/workflows/` contains three
files: the shared reusable workflow and **two major-specific thin caller files**.
`detect_changes.py`'s current `harness_changed()` check matches the whole
`.github` directory as one material path — so editing *only*
`compatibility-runner-puppet9.yml` (a cron tweak, an input default change) would
still register as "`.github` changed" and force `run_all=true` on the **Puppet 8**
workflow too, even though nothing Puppet-8-relevant changed.

Unlike the profiles case, this doesn't get an "usually released together"
exemption — CI/workflow-maintenance edits to one caller happen independently of
the other far more often than a coordinated major-version release does. Left
unfixed, this would be the single most likely way for the "Puppet 8 should get
leaner and leaner" requirement to silently break in practice.

**Fix:** stop matching `.github` as one blanket path. Each caller passes
`detect_changes.py` an explicit material-path list scoped to itself:

- Shared, included by both: `.github/actions/`, the reusable workflow file
  itself, plus `lib/`, `bin/`, `scripts/`, `Gemfile`, `Gemfile.lock` (these are
  shared, parameterized code executed by both majors' pipelines — a change here
  legitimately warrants retesting both, so keeping them coarse/shared is correct,
  not a leak; the leak only happens where genuinely major-dedicated *files*
  exist).
- Caller-specific: its own thin wrapper file (`compatibility-runner-puppet8.yml`
  for the 8 caller, `compatibility-runner-puppet9.yml` for the 9 caller) —
  explicitly **excluding** the sibling major's wrapper file.

---

## 6. Dashboard — per-major columns, one file

Per team decision: `KNOWN_COMPATIBLE.md` stays a **single file** (preserves
existing external links) with a **column per major** — a module can show ✅ on 8
and ❌ on 9 in the same row. `render_status_dashboard.py`'s `is_fully_compatible`
becomes a per-major predicate, evaluated once per `puppet_majors[major]` entry;
the compatible-list row includes the result for every tested major side by side.

`STATUS.md` needs the same per-major treatment for its summary counts and full
module table — a per-major summary block (unit pass/fail/pending counts,
acceptance pass/fail/blocked counts, fully-compatible count) plus a combined
module table with a column pair (unit, acceptance) per major, rather than one
wide table that conflates both.

---

## 7. `KNOWN_INCOMPATIBLE.md` policy for per-major incompatibility

Today, "incompatible" is version-agnostic in effect: a module found incompatible
gets added to `KNOWN_INCOMPATIBLE.md` and **removed from `config/modules.json`**
entirely (per `AGENTS.md`'s existing rule), which stops it from being tested at
all, on any major. Once two majors are tested, that's too blunt — a module can
be genuinely incompatible on 9 while remaining fully compatible and actively
tested on 8, and removing it from `modules.json` would wrongly kill its Puppet 8
coverage too.

**Policy:** a module is only added to `KNOWN_INCOMPATIBLE.md` and removed from
`config/modules.json` when it is incompatible on the **gating/primary major
(Puppet 8)**, or incompatible on **every actively tested major**. A 9-only
incompatibility is **not** a `KNOWN_INCOMPATIBLE.md` event — the module stays in
`config/modules.json` and continues being tested on both majors (so a future fix
is caught automatically); its Puppet-9 failure is simply visible as a red cell in
the per-major `STATUS.md`/`KNOWN_COMPATIBLE.md` columns from §6, with no special
casing needed. `KNOWN_INCOMPATIBLE.md`'s existing free-text "Puppet Core Tested"
column is sufficient to record which major(s) were involved when a module *is*
fully removed — no schema change needed there.

This also means the `mark-incompatible` skill and the corresponding `AGENTS.md`
section need a documentation update (not a schema change): "incompatible" as an
action (remove from matrix) now means "incompatible on the gating major or on
every tested major," not just "incompatible on whichever major I happened to
test."

---

## 8. Open risks to spike before implementation

- **Ruby/bundler version fit — RESOLVED 2026-08-20.** Queried the private gem
  source's compact-index endpoint directly
  (`GET /info/puppet` on `rubygems-puppetcore.puppet.com`, Basic auth
  `forge-key:$PUPPET_CORE_API_KEY`) for the actual `required_ruby_version`
  constraints:
  - `puppet 9.0.0`: `ruby: >= 3.4.0, < 5`
  - `puppet 8.20.0` / `8.19.0`: `ruby: >= 3.1.0, < 4`
  - `facter` requirement is `< 5, >= 4.3.0` for **both** majors — unaffected.

  **Ruby 3.4 satisfies both majors' constraints simultaneously** — no per-major
  Ruby split is needed. Fix: bump the harness's single Ruby pin from 3.2 to 3.4
  harness-wide (`.ruby-version`, the hardcoded `ruby-version: '3.2'` in
  `.github/actions/run-module-test/action.yml`, and the `SUPPORTED_RUBY_MAJOR`/
  `SUPPORTED_RUBY_MINOR` guard in `runner.rb`).

  This is a larger touch point than the original design assumed, for a reason
  worth recording: `gem_source_mode == 'private'` (true for every profile today)
  makes `adapters.rb` **bypass PDK entirely** in favor of the raw
  `bundle`/`rake` path, because PDK would re-resolve against its own vendored
  FOSS Puppet and silently ignore the `Gemfile.puppetcore` overlay pin. That
  means the harness's own host Ruby — not just the Docker SUT's Ruby — is the
  Ruby that resolves and loads the `puppet` gem via Bundler. And
  `runner.rb`'s `run_module` calls `@bootstrap.run` (the step that does this
  resolution) **unconditionally, before the unit/acceptance branch** — so this
  applies to acceptance-mode runs too, not just unit, even though the actual
  `puppet apply` for acceptance happens against a separately-installed
  puppet-agent inside the Docker SUT with its own embedded Ruby, independent of
  the host.

  **Still open, unresolved by the gemspec check above** (needs the actual spike
  run, not just a version-string lookup): whether bundler 2.5.22 behaves
  correctly under Ruby 3.4, and whether `bootstrap.rb`'s split-Gemfile
  `json '< 2.7.0'` pin — explicitly justified in-code as a Ruby-3.2-era
  workaround for a facterdb/json-2.7 parsing bug — still installs and behaves
  correctly under 3.4. Plan: bump the three files above on a branch and dispatch
  the *existing* workflow against the *existing* `8-latest-maintained` profile
  (no 9-profile yet) for one already-green module, to isolate "did the Ruby bump
  alone regress anything" before adding any Puppet-9-specific config.
- **FOSS acceptance fallback may not exist for 9 yet.** Without
  `PUPPET_CORE_API_KEY`, acceptance falls back to the public FOSS puppet-agent
  from `yum.puppet.com`, capped at 8.10.0 today. Confirm whether a FOSS Puppet 9
  agent package exists at all before assuming the no-API-key acceptance path can
  represent major 9 in any form.
- **Expected metadata-warning volume increase.** Most modules' `metadata.json`
  declares a Puppet requirement range like `>= 7.0.0 < 9.0.0`, which will
  legitimately fail the `< 9.0.0` upper bound under a 9 profile. `lib/module_tester/metadata.rb`
  already handles this generically (`unsupported_by_metadata` → a warning, not a
  failure, under the default `warn` mode per `classifier.rb`) — no code change
  needed, but expect a real spike in metadata-warning counts on the Puppet 9
  dashboard immediately after rollout. This is expected signal, not a harness bug.

---

## 9. Rollout phasing

Reworked 2026-08-20 into steps **A–E**, each a separate branch/PR merged only
after its own gate passes. The gate is always a real dispatch of the Puppet 8
path on GitHub Actions — never just a local script run or a gemspec lookup —
so `main` stays green throughout and no step is built on an unvalidated prior
one. If a gate fails, only that step's branch needs rework; nothing downstream
has been started yet. See §12 for live status.

**Step A — Ruby 3.4 bump (harness-wide, shared infra)**
- Change: `.ruby-version` (3.2→3.4), the hardcoded `ruby-version: '3.2'` in
  `.github/actions/run-module-test/action.yml` (→ `'3.4'`), `runner.rb`'s
  `SUPPORTED_RUBY_MAJOR`/`SUPPORTED_RUBY_MINOR` guard (→ `3`/`4`). No profile,
  schema, or workflow-topology changes — isolates Ruby-version risk alone.
- Gate: dispatch the *existing* `compatibility-runner.yml` for the **full
  module suite** on both `8-latest-maintained` and `8-previous-maintained`;
  diff module-by-module against the pre-change green baseline. Confirms
  bundler 2.5.22 and the `bootstrap.rb` `json '< 2.7.0'` pin (§8's remaining
  unverified risk) still behave correctly under 3.4.

**Step B — Ledger schema v2 + all its readers, as one atomic unit**
- Change: `puppet_majors` migration script, `update_ledger.py` (key by
  `(id, major)`, write into `puppet_majors[major]`), `detect_changes.py` (read
  `puppet_majors["8"]` slice instead of module-level fields),
  `render_status_dashboard.py` (per-major `is_fully_compatible`, per-major
  columns). These four must land together — splitting them leaves the
  publish job reading a schema shape its own dashboard renderer doesn't
  understand yet, breaking `STATUS.md`/`KNOWN_COMPATIBLE.md` on the very next
  run.
- Gate: run the migration script against the real `status/ledger.json` and
  diff dashboard output locally first (should be equivalent to today, modulo
  the new column, since only major `"8"` exists so far). Then dispatch the
  existing workflow for the full suite on GitHub and confirm the ledger
  commits correctly and `STATUS.md`/`KNOWN_COMPATIBLE.md` render with no
  regressions.

**Step C — CI topology: reusable workflow + Puppet-8 thin caller**
- Change: new `.github/workflows/_compatibility-runner-reusable.yml` (§4.1),
  new `.github/workflows/compatibility-runner-puppet8.yml` (the only active
  caller at this point), scoped material-path lists (§5.3). Old
  `compatibility-runner.yml` stays in place until the gate below passes, then
  is retired.
- Gate: dispatch the full suite through the **new** `compatibility-runner-
  puppet8.yml` caller and confirm byte-for-byte parity with Step B's
  baseline (same pass/fail/warn per module, ledger/dashboard unchanged).
  Highest structural risk of the five steps, since it replaces the pipeline's
  entry point — don't delete the old workflow file until this run is clean.

**Step D — Add Puppet 9: profile entry + thin caller**
- Change: `profiles/puppet_profiles.json` gets `9-latest-maintained` (real
  `puppet_core_version`/`facter_version` pinned per §8's gem-source query —
  re-check for a newer 9.x at implementation time the same way 8.21.0 was
  found), new `.github/workflows/compatibility-runner-puppet9.yml` caller,
  `major` param wired through `detect_changes.py`/`build_matrix.rb` (§3.2,
  §5.1), shared publish concurrency group (§4.2).
- Gate: dispatch the new Puppet-9 caller for the full suite — expect real
  failures/warnings, that's signal not a bug (§8's metadata-warning note) —
  **and** re-dispatch the Puppet-8 caller in the same round, to prove the two
  majors' lean-matrix/ledger state stay fully independent (§5's core
  requirement: a Puppet 9 regression must not touch Puppet 8's leanness or
  status).

**Step E — `KNOWN_INCOMPATIBLE.md` policy + docs**
- Change: `AGENTS.md`, the `mark-incompatible` skill (§7's removal-criteria
  update), `docs/architecture-flow.md` (CI + reporting sections per the
  existing "Architecture Diagram Maintenance" table). Doc/policy-only, no CI
  risk, no dispatch gate needed — just consistency with the shipped behavior
  from Steps A–D.

---

## 10. New / changed files

| File | Change |
|---|---|
| `.ruby-version` | **3.2 → 3.4**, harness-wide (§8) — one shared pin, not per-major. |
| `.github/actions/run-module-test/action.yml` | `ruby-version: '3.2'` → `'3.4'` in the `ruby/setup-ruby@v1` step (§8). |
| `lib/module_tester/runner.rb` | `SUPPORTED_RUBY_MAJOR`/`SUPPORTED_RUBY_MINOR` guard → `3`/`4` (§8). |
| `status/ledger.json` schema | **v2.** `puppet_majors["8"\|"9"]` nesting per module; migration script to lift existing flat entries. |
| `scripts/update_ledger.py` | Group by `(id, major)`; write into `puppet_majors[major]`; per-major `coverage_state`. |
| `scripts/classify_module_result.py` | Resolve and stamp `puppet_major` from the profile (mirrors existing `puppet_core_version` resolution). |
| `scripts/render_status_dashboard.py` | Per-major `is_fully_compatible`; per-major columns in `STATUS.md` and `KNOWN_COMPATIBLE.md`. |
| `scripts/detect_changes.py` | Accept a `major` parameter; scope all ledger reads to `puppet_majors[major]`; accept a caller-scoped material-path list (shared paths + own wrapper file only). |
| `scripts/build_matrix.rb` | Parameterize by the caller's profile set (no cross-major fan-out needed — each caller already only tests its own major). |
| `.github/workflows/_compatibility-runner-reusable.yml` | **New.** Holds the full `prepare`/`test_unit`/`test_acceptance`/`publish` job graph, parameterized by `profiles` + `major` inputs. |
| `.github/workflows/compatibility-runner-puppet8.yml` | **New, thin.** Triggers + call into the reusable workflow with the 8-series profiles. |
| `.github/workflows/compatibility-runner-puppet9.yml` | **New, thin.** Same shape, 9-series profiles. |
| `.github/workflows/compatibility-runner.yml` | Retired, replaced by the three files above. |
| `profiles/puppet_profiles.json` | Add `9-latest-maintained` (+ `previous`) entries. No structural change — `puppet_major` field already exists. |
| `KNOWN_INCOMPATIBLE.md` / `AGENTS.md` / `mark-incompatible` skill | Policy update: removal from `modules.json` requires incompatibility on the gating major or all tested majors, not any single major. |
| `docs/architecture-flow.md` | Update CI + reporting sections per existing maintenance rule. |

---

## 11. Edge cases & decisions

- **A module never tested on 9 yet, but green on 8** → not "fully compatible" on
  9 (never-tested is not green) and is force-included on the next Puppet 9 run —
  same not-green re-inclusion rule as the lean-testing design, just scoped to
  major 9's slice of the ledger.
- **A module incompatible on 9 only** → stays in `config/modules.json`, keeps
  running on both majors, never enters `KNOWN_INCOMPATIBLE.md` (§7).
- **A module incompatible on 8 (the gating major)** → removed from
  `config/modules.json` per the existing rule — this also stops its Puppet 9
  testing, which is accepted (no value in tracking Puppet 9 compatibility for a
  module the harness has fully retired).
- **Shared profile file bump affecting both majors' `run_all`** → accepted
  behavior, not a leak (§5.2).
- **`.github` wrapper-file edits leaking across majors** → fixed by scoping the
  material-path list per caller (§5.3), not by splitting further config.
- **Ledger write collision** → fixed structurally by per-major keys (§3) plus a
  shared concurrency group on just the publish job (§4.2) — not by serializing
  the entire pipeline across majors.

---

## 12. Implementation progress tracker

Living status for §9's Steps A–E. Update this table (and add a dated note
under it) whenever a step's gate passes, fails, or its scope changes — this is
the section a new session should read first to know exactly where things stand
before touching any code.

| Step | Description | Status | Notes |
|---|---|---|---|
| A | Ruby 3.4 bump, harness-wide | Not started | Blocked on nothing — ready to start once the full-suite Puppet 8 baseline (below) is green. |
| B | Ledger schema v2 + readers | Not started | Depends on A's gate passing. |
| C | Reusable workflow + Puppet-8 caller | Not started | Depends on B's gate passing. |
| D | Puppet 9 profile + caller | Not started | Depends on C's gate passing. Re-query the private gem source for the latest 9.x at start of this step — don't assume 9.0.0 is still current. |
| E | `KNOWN_INCOMPATIBLE.md` policy + docs | Not started | Depends on D shipping (describes D's shipped behavior). |

**Baseline context (as of 2026-08-20):**
- `profiles/puppet_profiles.json`: `8-latest-maintained` = Puppet 8.21.0 / facter 4.21.0; `8-previous-maintained` = Puppet 8.20.0 / facter 4.20.0 (bumped in a prior session alongside the Puppet 9 investigation — a new Puppet 8.x point release shipped alongside Puppet 9).
- A full-suite run against these two 8-profiles was in progress (to confirm a clean green baseline) at the time Step A was scoped — check its result before starting Step A; Step A's own gate is a diff against this baseline, so it needs to exist and be green first.
- §8's gemspec query (private source, `GET /info/puppet`, Basic auth `forge-key:<key>`) found: `puppet 9.0.0` requires `ruby >= 3.4.0, < 5`; `puppet 8.20.0`/`8.19.0` (checked before the 8.21.0 bump) require `ruby >= 3.1.0, < 4`; facter requirement (`>= 4.3.0, < 5`) is identical across both majors. Ruby 3.4 satisfies both — confirmed no per-major Ruby split is needed. **Not yet re-verified against 8.21.0** — cheap to double check when Step A starts, using the same `/info/puppet` query, filtering for `^8.21.0 `.
