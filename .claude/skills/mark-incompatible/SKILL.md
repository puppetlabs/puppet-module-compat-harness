---
name: mark-incompatible
description: Record a module as incompatible (or partially incompatible) with Puppet Core and remove it from the active test matrix. Use when the user says a module is incompatible, should be excluded, "doesn't work with Puppet Core", is OpenVox-only, or when your own testing/inspection proves a module cannot pass. Updates KNOWN_INCOMPATIBLE.md and config/modules.json per AGENTS.md.
---

# Mark a module incompatible

Record an incompatibility ruling per [AGENTS.md](../../../AGENTS.md) "Adding New
Incompatibilities". First decide **which** of three distinct outcomes applies — they are not
the same and are handled differently.

## Step 0 — Classify the outcome (do not conflate these)

- **Incompatible** — the module cannot produce a reliable pass on Puppet Core (OpenVox-only
  hard failure, dead legacy toolchain, unresolvable deps). → Document + **remove** from the
  matrix.
- **Partial** — core functionality works but a specific class/feature fails on Puppet Core
  (e.g. an mcollective/choria integration class). → Document as **Partial** and **keep** the
  module in `config/modules.json`; the harness tolerates the documented failure.
- **Deprecated but compatible** — upstream is archived/unmaintained but still passes. This is
  **NOT** an incompatibility. Do not use this skill — set `"deprecated": true` on the module
  entry in `modules.json` instead (it stays in the matrix). Deprecation is orthogonal to
  compatibility.

If unsure whether it's truly incompatible vs. just failing for a harness/config reason,
gather evidence first (a scoped run, log inspection) — a harness error is not an
incompatibility.

## Step 1 — Add a row to KNOWN_INCOMPATIBLE.md

Add a row to the "Incompatibility Summary" table in
[KNOWN_INCOMPATIBLE.md](../../../KNOWN_INCOMPATIBLE.md). Columns:

`| Module | Puppet Core Tested | Status | Reason | Recommended Replacement | Details |`

- **Module** — linked to the upstream repo.
- **Puppet Core Tested** — the version/profile you tested against (e.g. `8.19.0`), or `N/A`
  for a categorical rule like OpenVox-only.
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
