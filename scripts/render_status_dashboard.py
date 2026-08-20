"""Render STATUS.md and KNOWN_COMPATIBLE.md from the status ledger.

Unlike a single run's summary (which, once testing is lean, covers only the
modules that ran), this reads the accumulated ledger so it always reflects every
tracked module. It produces:
  - STATUS.md — the complete fleet dashboard (weekly-report numbers: unit /
    acceptance coverage, fully-compatible count, stale / never-tested / retired).
  - KNOWN_COMPATIBLE.md — the curated "fully validated" list, derived from the
    same `is_fully_compatible` predicate, so it can never drift from the ledger.

Reads ledger schema v2: per-module test outcomes (unit/acceptance/coverage_state)
live under `puppet_majors[major]`, so every count and the `is_fully_compatible`
verdict are computed once per tracked major (see
docs/puppet-core-9-dual-major-support.md §3, §6) rather than once per module.
Only major "8" is tested today, so output is equivalent to the pre-v2 dashboard
modulo the per-major column labels; a second major's columns appear
automatically once it starts reporting into the ledger.

Environment:
  LEDGER_FILE            ledger path (default: status/ledger.json)
  MODULES_FILE           modules config (default: config/modules.json)
  STATUS_FILE            dashboard output path (default: STATUS.md)
  KNOWN_COMPATIBLE_FILE  compatible-list output path (default: KNOWN_COMPATIBLE.md)
  STALE_DAYS             freshness threshold in days (default: 30)
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_lib import load_modules_config, parse_known_ids  # noqa: E402

# The one major that's tested today; always shown even if a module has no
# puppet_majors entry yet (never-tested), so the dashboard shape is stable.
GATING_MAJOR = '8'

# Reporting is pass/fail only. Warnings are deliberate green-keepers (tolerated
# metadata gaps, etc.) and count as pass; we do not surface the warning level.
def is_pass(status_class):
    return status_class in ('clean', 'warning')


def class_icon(status_class):
    if status_class == 'failure':
        return '❌'
    if is_pass(status_class):
        return '✅'
    if status_class == 'blocked':
        return '⛔'
    return '?'


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def parse_ts(value):
    if not value:
        return None
    text = value.strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        parsed = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def discover_majors(modules):
    """Every Puppet major with at least one module reporting into it, plus the
    gating major so the dashboard always has a stable shape even before any
    result has landed."""
    found = {major for entry in modules.values() for major in entry.get('puppet_majors', {})}
    found.add(GATING_MAJOR)
    return sorted(found, key=int)


def major_entry(entry, major):
    return entry.get('puppet_majors', {}).get(major, {})


def unit_icon(major_slice):
    unit = major_slice.get('unit')
    if not unit:
        return '—'
    return class_icon(unit.get('class'))


def acceptance_status(entry):
    # Config-derived disposition; falls back to the legacy boolean for old ledgers.
    status = entry.get('acceptance_status')
    if status:
        return status
    return 'running' if entry.get('acceptance_configured') else 'none'


def acceptance_cell(major_slice, entry):
    status = acceptance_status(entry)
    if status == 'none':
        return 'N/A'
    if status == 'blocked':
        return '⛔ blocked'
    if status == 'pending':
        return '🚧 pending'
    # status == 'running'
    acceptance = major_slice.get('acceptance')
    if not acceptance or not acceptance.get('targets'):
        return '⏳ awaiting run'
    targets = acceptance['targets']
    return ' '.join(f"{name}:{class_icon(cls)}" for name, cls in sorted(targets.items()))


def unit_passed(major_slice):
    unit = major_slice.get('unit')
    return bool(unit) and is_pass(unit.get('class'))


def acceptance_passed(major_slice):
    acceptance = major_slice.get('acceptance')
    return bool(acceptance) and bool(acceptance.get('targets')) and is_pass(acceptance.get('class'))


def is_fully_compatible(major_slice, entry):
    if not unit_passed(major_slice):
        return False
    status = acceptance_status(entry)
    if status == 'none':
        return True  # no acceptance tests exist — unit coverage is full coverage
    if status == 'running':
        return acceptance_passed(major_slice)
    # blocked / pending: acceptance tests exist but were never exercised here, so
    # coverage is incomplete. These are NOT fully compatible.
    return False


def last_tested(major_slice):
    stamps = []
    if major_slice.get('unit', {}).get('tested_at'):
        stamps.append(parse_ts(major_slice['unit']['tested_at']))
    if major_slice.get('acceptance', {}).get('tested_at'):
        stamps.append(parse_ts(major_slice['acceptance']['tested_at']))
    stamps = [s for s in stamps if s]
    return max(stamps) if stamps else None


def module_last_tested(entry):
    """Latest tested_at across every major, for the combined table's one column."""
    stamps = [last_tested(slice_) for slice_ in entry.get('puppet_majors', {}).values()]
    stamps = [s for s in stamps if s]
    return max(stamps) if stamps else None


def render_known_compatible(active, path, excluded_ids, majors):
    """Write KNOWN_COMPATIBLE.md — modules fully compatible on at least one
    tested major. Each major gets its own column so a module can show ✅ on one
    major and ❌ (tested, not compatible) or — (not yet tested on that major) on
    another in the same row. Blocked/pending acceptance disposition is treated
    as NOT fully compatible on that major, same as `is_fully_compatible`.
    Modules in `excluded_ids` (from KNOWN_INCOMPATIBLE.md) are excluded outright —
    a compatibility verdict is mutually exclusive with the compatible list, even
    for a module still in the test matrix whose only failures are downgraded to
    warnings (e.g. a "Partial" entry). Deprecation is NOT an exclusion: it is a
    lifecycle status orthogonal to compatibility.
    """
    rows = []
    for module_id in sorted(active):
        if module_id in excluded_ids:
            continue
        entry = active[module_id]
        cells = {}
        compatible_on_any = False
        for major in majors:
            slice_ = major_entry(entry, major)
            if not slice_.get('unit'):
                cells[major] = '—'
                continue
            if is_fully_compatible(slice_, entry):
                compatible_on_any = True
                version = slice_.get('puppet_core_version', '')
                cells[major] = f'✅ {version}'.strip() if version else '✅'
            else:
                cells[major] = '❌'
        if compatible_on_any:
            rows.append((module_id, entry, cells))

    lines = [
        '# Known Compatible Modules',
        '',
        '> Auto-generated from `status/ledger.json` by `scripts/render_status_dashboard.py`.',
        '> Do not edit by hand — changes will be overwritten on the next run.',
        '',
        'This document lists modules that have been fully validated against Puppet Core on at '
        'least one tested major version — meaning all available tests have passed for that major.',
        '',
        'Each Puppet major has its own column: **✅ &lt;version&gt;** = fully compatible on that '
        'major, **❌** = tested on that major but not fully compatible, **—** = not yet tested on '
        'that major.',
        '',
        '**N/A in a major column context** (shown in [STATUS.md](STATUS.md), not here) means the '
        'module has no acceptance tests in its upstream repository; unit tests alone constitute '
        'full coverage. Modules with upstream acceptance tests that cannot currently run in the '
        'harness (due to Docker/container limitations) do not count as fully compatible on that '
        'major — see [docs/available-acceptance-tests.md](docs/available-acceptance-tests.md) for '
        'the full audit including blocked modules.',
        '',
        '**Distinction from [KNOWN_INCOMPATIBLE.md](KNOWN_INCOMPATIBLE.md):** Modules listed here have '
        'passed all tests available to this harness on at least one major. KNOWN_INCOMPATIBLE.md lists '
        'modules tested and found to have compatibility failures on the gating major (or every tested '
        'major) and removed from the matrix entirely.',
        '',
        '**⚠️ next to a module name** marks it deprecated / no longer maintained upstream. It remains '
        'compatible, but consider migrating away from it.',
        '',
        '## Compatibility Summary',
        '',
        '| Module | ' + ' | '.join(f'Puppet {major}' for major in majors) + ' |',
        '|--------|' + '|'.join('---' for _ in majors) + '|',
    ]
    for module_id, entry, cells in rows:
        repo = entry.get('repo', '')
        name = f"[{module_id}]({repo})" if repo else module_id
        if entry.get('deprecated'):
            name += ' ⚠️'
        lines.append(f"| {name} | " + ' | '.join(cells[major] for major in majors) + ' |')

    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(lines) + '\n')
    return len(rows)


def render_major_summary(major, active, stale_cutoff):
    unit_tested = [e for e in active.values() if major_entry(e, major).get('unit')]
    unit_pass = [e for e in unit_tested if unit_passed(major_entry(e, major))]
    unit_fail = [e for e in unit_tested if not unit_passed(major_entry(e, major))]

    acceptance_running = [e for e in active.values() if acceptance_status(e) == 'running']
    acceptance_run = [e for e in acceptance_running if major_entry(e, major).get('acceptance', {}).get('targets')]
    acceptance_pass = [e for e in acceptance_run if acceptance_passed(major_entry(e, major))]
    acceptance_fail = [e for e in acceptance_run if not acceptance_passed(major_entry(e, major))]
    acceptance_blocked = [e for e in active.values() if acceptance_status(e) == 'blocked']
    acceptance_pending = [e for e in active.values() if acceptance_status(e) == 'pending']
    acceptance_none = [e for e in active.values() if acceptance_status(e) == 'none']

    fully_compatible = [e for e in active.values() if is_fully_compatible(major_entry(e, major), e)]
    never_tested = [e for e in active.values() if not major_entry(e, major).get('unit')]
    stale = [e for e in unit_tested if (lambda s: s is not None and s < stale_cutoff)(last_tested(major_entry(e, major)))]

    versions = sorted({
        major_entry(e, major).get('puppet_core_version')
        for e in active.values()
        if major_entry(e, major).get('puppet_core_version')
    })

    lines = [f'### Puppet {major}', '']
    lines.append(f"**Puppet Core version(s) seen:** {', '.join(versions) if versions else 'none yet'}  ")
    lines.append('')
    lines.append('| Metric | Count |')
    lines.append('|---|---|')
    lines.append(f"| Unit-tested | {len(unit_tested)} |")
    lines.append(f"| &nbsp;&nbsp;• unit pass | {len(unit_pass)} |")
    lines.append(f"| &nbsp;&nbsp;• unit fail | {len(unit_fail)} |")
    lines.append(f"| Acceptance-enabled (running) | {len(acceptance_running)} |")
    lines.append(f"| &nbsp;&nbsp;• acceptance run | {len(acceptance_run)} |")
    lines.append(f"| &nbsp;&nbsp;• acceptance pass | {len(acceptance_pass)} |")
    lines.append(f"| &nbsp;&nbsp;• acceptance fail | {len(acceptance_fail)} |")
    lines.append(f"| ⛔ Acceptance blocked (tests exist, can't run here) | {len(acceptance_blocked)} |")
    lines.append(f"| 🚧 Acceptance pending (tests exist, not yet wired) | {len(acceptance_pending)} |")
    lines.append(f"| No acceptance tests (N/A) | {len(acceptance_none)} |")
    lines.append(f"| **Fully compatible** (unit pass + acceptance pass or N/A) | **{len(fully_compatible)}** |")
    lines.append(f"| Never tested | {len(never_tested)} |")
    lines.append(f"| Stale | {len(stale)} |")
    lines.append('')
    return lines


def main():
    ledger_file = os.environ.get('LEDGER_FILE', 'status/ledger.json')
    modules_file = os.environ.get('MODULES_FILE', 'config/modules.json')
    status_file = os.environ.get('STATUS_FILE', 'STATUS.md')
    known_compatible_file = os.environ.get('KNOWN_COMPATIBLE_FILE', 'KNOWN_COMPATIBLE.md')
    stale_days = int(os.environ.get('STALE_DAYS', '30'))

    if not os.path.exists(ledger_file):
        print(f"No ledger at {ledger_file}; nothing to render.", file=sys.stderr)
        return 0

    with open(ledger_file, 'r', encoding='utf-8') as handle:
        ledger = json.load(handle)
    modules = ledger.get('modules', {})
    config = load_modules_config(modules_file)
    now = utc_now()
    stale_cutoff = now - datetime.timedelta(days=stale_days)

    active = {mid: e for mid, e in modules.items() if e.get('disposition') == 'active'}
    retired = {mid: e for mid, e in modules.items() if e.get('disposition') in ('incompatible', 'deprecated')}
    anomalies = {mid: e for mid, e in modules.items() if e.get('disposition') == 'removed-without-disposition'}

    majors = discover_majors(modules)

    deprecated_active = [e for e in active.values() if e.get('deprecated')]

    lines = []
    lines.append('# Module Compatibility Status')
    lines.append('')
    lines.append('> Auto-generated from `status/ledger.json` by `scripts/render_status_dashboard.py`.')
    lines.append('> Do not edit by hand — changes will be overwritten on the next run.')
    lines.append('')
    lines.append(f"**Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}  ")
    lines.append(f"**Staleness threshold:** {stale_days} days")
    lines.append('')

    lines.append('## Summary')
    lines.append('')
    lines.append(f"| Metric | Count |")
    lines.append('|---|---|')
    lines.append(f"| Active modules | {len(active)} |")
    lines.append(f"| ⚠️ Deprecated (unmaintained upstream) | {len(deprecated_active)} |")
    lines.append(f"| Retired (incompatible / deprecated) | {len(retired)} |")
    if anomalies:
        lines.append(f"| ⚠️ Removed without disposition | {len(anomalies)} |")
    lines.append('')
    lines.append('Per-major coverage is tracked independently — a Puppet 9 regression does not affect '
                 "Puppet 8's numbers or vice versa (docs/puppet-core-9-dual-major-support.md §5).")
    lines.append('')

    for major in majors:
        lines.extend(render_major_summary(major, active, stale_cutoff))

    lines.append('## Active Modules')
    lines.append('')
    lines.append('> Per major: `target:✅/❌` = ran, `N/A` = no acceptance tests exist upstream, '
                 '`⛔ blocked` = tests exist but cannot run in this harness, `🚧 pending` = tests exist but '
                 'not yet wired up, `⏳ awaiting run` = enabled but no result yet, `—` = not yet tested on '
                 'that major. Only ✅/N/A count toward that major\'s **Fully compatible**.')
    lines.append('>')
    lines.append('> ⚠️ next to a module name marks it **deprecated / no longer maintained upstream** — '
                 'independent of compatibility (a deprecated module can still be fully compatible).')
    lines.append('')
    header = ['Module']
    for major in majors:
        header.append(f'{major}: Unit')
        header.append(f'{major}: Acceptance')
    header.append('Last Tested')
    lines.append('| ' + ' | '.join(header) + ' |')
    lines.append('|' + '|'.join('---' for _ in header) + '|')
    for module_id in sorted(active):
        entry = active[module_id]
        repo = entry.get('repo', '')
        name = f"[{module_id}]({repo})" if repo else module_id
        if entry.get('deprecated'):
            name += ' ⚠️'
        row = [name]
        for major in majors:
            slice_ = major_entry(entry, major)
            row.append(unit_icon(slice_))
            row.append(acceptance_cell(slice_, entry))
        stamp = module_last_tested(entry)
        when = stamp.strftime('%Y-%m-%d') if stamp else '—'
        if stamp is not None and stamp < stale_cutoff:
            when += ' ⏰'
        row.append(when)
        lines.append('| ' + ' | '.join(row) + ' |')
    lines.append('')

    not_exercised = [mid for mid in active if acceptance_status(active[mid]) in ('blocked', 'pending')]
    if not_exercised:
        lines.append('> ⛔ **blocked** / 🚧 **pending** modules have acceptance tests upstream that the harness '
                     'did not run, so their compatibility is confirmed by unit tests only — not fully. The '
                     'per-module reasons are documented in '
                     '[docs/available-acceptance-tests.md](docs/available-acceptance-tests.md).')
        lines.append('')

    if retired or anomalies:
        lines.append('## Retired / Removed')
        lines.append('')
        lines.append(f'| Module | Disposition | Last Known Unit ({GATING_MAJOR}) | Last Tested |')
        lines.append('|---|---|---|---|')
        for module_id in sorted({**retired, **anomalies}):
            entry = modules[module_id]
            repo = entry.get('repo', '')
            name = f"[{module_id}]({repo})" if repo else module_id
            stamp = module_last_tested(entry)
            when = stamp.strftime('%Y-%m-%d') if stamp else '—'
            lines.append(f"| {name} | {entry.get('disposition')} | {unit_icon(major_entry(entry, GATING_MAJOR))} | {when} |")
        lines.append('')

    if anomalies:
        lines.append('> ⚠️ **Removed without disposition:** the module(s) above are in the ledger but '
                     'no longer in `config/modules.json` and are not listed in `KNOWN_INCOMPATIBLE.md` '
                     'or `KNOWN_DEPRECATED.md`. Add a disposition or restore them to the config.')
        lines.append('')

    os.makedirs(os.path.dirname(status_file) or '.', exist_ok=True)
    with open(status_file, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(lines))

    # Only KNOWN_INCOMPATIBLE excludes — it is a compatibility verdict, mutually
    # exclusive with "compatible". Deprecation is a lifecycle status, orthogonal to
    # compatibility (a module can be both deprecated and fully compatible, e.g. an
    # archived module whose unit tests still pass), so it does NOT exclude.
    excluded_ids = parse_known_ids(os.environ.get('KNOWN_INCOMPATIBLE_FILE', 'KNOWN_INCOMPATIBLE.md'))
    compatible_count = render_known_compatible(active, known_compatible_file, excluded_ids, majors)

    fully_compatible_gating = [e for e in active.values() if is_fully_compatible(major_entry(e, GATING_MAJOR), e)]
    print(
        f"STATUS.md rendered: {len(active)} active, "
        f"{len(fully_compatible_gating)} fully compatible on Puppet {GATING_MAJOR}, "
        f"{len(retired)} retired, {len(anomalies)} anomalies."
    )
    print(f"KNOWN_COMPATIBLE.md rendered: {compatible_count} module(s) compatible on at least one major.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
