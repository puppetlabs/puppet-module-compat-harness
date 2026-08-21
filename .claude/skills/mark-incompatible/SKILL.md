---
name: mark-incompatible
description: Record a module as incompatible (or partially incompatible) with Puppet Core and remove it from the active test matrix. Use when the user says a module is incompatible, should be excluded, "doesn't work with Puppet Core", or when your own testing/inspection proves a module cannot pass. Also for genuinely OpenVox-only modules — but note that is narrow (a hard runtime refusal of non-OpenVox, or a module whose purpose is installing OpenVox); a module that merely declares openvox in metadata.json is a normal add-module input, not an incompatibility. Updates KNOWN_INCOMPATIBLE.md and config/modules.json per AGENTS.md.
---

# Mark a module incompatible

Record an incompatibility ruling per [AGENTS.md](../../../AGENTS.md) "Adding New
Incompatibilities". First decide **which** of three distinct outcomes applies — they are not
the same and are handled differently.

## Step 0 — Classify the outcome (do not conflate these)

- **Incompatible** — the module cannot produce a reliable *usable* pass on Puppet Core
  (genuinely OpenVox-only, dead legacy toolchain, unresolvable deps). → Document + **remove**
  from the matrix — but see "Which major(s)?" below first if the evidence is version-specific.
- **Partial** — core functionality works but a specific class/feature fails on Puppet Core
  (e.g. an mcollective/choria integration class). → Document as **Partial** and **keep** the
  module in `config/modules.json`; the harness tolerates the documented failure.
- **Deprecated but compatible** — upstream is archived/unmaintained but still passes. This is
  **NOT** an incompatibility. Do not use this skill — set `"deprecated": true` on the module
  entry in `modules.json` instead (it stays in the matrix). Deprecation is orthogonal to
  compatibility.

### Which major(s) is this incompatible on?

The harness now tests every module against multiple Puppet majors independently (Puppet 8 +
Puppet 9 — see `docs/puppet-core-9-dual-major-support.md` §7). Removal from the matrix is scoped
to which major(s) the incompatibility actually applies to. Puppet 8 is the **gating/primary**
major:

- **Categorical rulings** (genuinely OpenVox-only, dead legacy toolchain) apply identically on
  every major — always a full removal, no per-major check needed.
- **Version-specific test evidence** (a real failure from one major's run) needs a check before
  removing: is this incompatible on **Puppet 8**, or on **every** actively tested major? If so,
  it's a removal (Step 1–2 below). If it's incompatible on a **non-gating major only** (e.g.
  Puppet 9, with Puppet 8 unaffected), it is **not** a `KNOWN_INCOMPATIBLE.md` event — do not use
  this skill's removal steps. Leave the module in `config/modules.json` exactly as-is; it keeps
  running on every major so a future upstream fix is caught automatically, and its failure is
  simply a red cell in that major's `STATUS.md` / `KNOWN_COMPATIBLE.md` column. No action needed
  beyond letting the next run's ledger update reflect it.

### "OpenVox-only" is narrow — do not over-apply it

This harness's whole purpose is to **swap OpenVox for Puppet Core and run the tests** (see
AGENTS.md "Project Purpose"). So a module declaring **`openvox` (not `puppet`) in
`metadata.json`/`Gemfile` is the normal input, NOT an incompatibility.** A missing `puppet`
requirement is only a metadata *warning* (`conditionally_compatible`), never a blocking failure
or exclusion.

Mark a module OpenVox-only **Incompatible** only when it cannot yield a usable Puppet Core
result — one of:

- a **hard runtime check that refuses non-OpenVox** distributions (e.g. `puppet-choria` raising
  "Choria only supports OpenVox"), or
- its **purpose is to install/bootstrap OpenVox packages**, so even a passing test describes no
  valid Puppet Core use case (e.g. `puppet-openvox_bootstrap`).

If the module just declares `openvox` but its providers/manifests otherwise run under Puppet
Core, it is **not** incompatible — hand it to the `add-module` skill instead.

If unsure whether it's truly incompatible vs. just failing for a harness/config reason,
gather evidence first (a scoped run, log inspection) — a harness error, or a metadata-only
`openvox` declaration, is not an incompatibility.

## Step 1 — Add a row to KNOWN_INCOMPATIBLE.md

Add a row to the "Incompatibility Summary" table in
[KNOWN_INCOMPATIBLE.md](../../../KNOWN_INCOMPATIBLE.md). Columns:

`| Module | Puppet Core Tested | Status | Reason | Recommended Replacement | Details |`

- **Module** — linked to the upstream repo.
- **Puppet Core Tested** — the version/profile you tested against (e.g. `8.19.0`), or `N/A`
  for a categorical rule like OpenVox-only. If evidence came from more than one major (e.g.
  incompatible on both 8 and 9), list both versions — this free-text column is the record of
  which major(s) were involved; no separate schema field for it.
- **Status** — `Incompatible` or `Partial`.
- **Reason** — concise root cause.
- **Recommended Replacement** — a migration target if one exists, else `N/A`.
- **Details** — the full technical explanation: what failed, the error signature, and (for
  Partial) exactly which class/feature is affected and what the harness does about it.

Match the tone and depth of existing rows.

## Step 2 — Update config/modules.json

- **Incompatible**: remove the module entry entirely so it leaves the test matrix. Preserve
  the block ordering (voxpupuli-first / alphabetical) of the remaining entries.
- **Partial**: leave the entry in place. If the partial failure needs runner tolerance that
  isn't already in place, note the follow-up — don't silently assume it's handled.

## Step 3 — Validate & report

```bash
python scripts/validate_modules_config.py --config config/modules.json --schema config/modules.schema.json
```

Report: the classification (Incompatible / Partial), the evidence, whether the module was
removed or retained, and any migration guidance. Do not hand-edit the generated docs
(`STATUS.md`, `KNOWN_COMPATIBLE.md`) — they regenerate from the ledger and config; a
`KNOWN_INCOMPATIBLE.md` entry is what excludes a module from `KNOWN_COMPATIBLE.md`.
