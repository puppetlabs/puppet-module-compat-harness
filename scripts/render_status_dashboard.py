"""Render STATUS.md — the complete fleet dashboard — from the status ledger.

Unlike a single run's summary (which, once testing is lean, covers only the
modules that ran), this reads the accumulated ledger so it always reflects every
tracked module. It produces the weekly-report numbers: unit coverage, acceptance
coverage, fully-compatible count, plus stale / never-tested / retired accounting.

Environment:
  LEDGER_FILE   ledger path (default: status/ledger.json)
  MODULES_FILE  modules config (default: config/modules.json)
  STATUS_FILE   output path (default: STATUS.md)
  STALE_DAYS    freshness threshold in days (default: 30)
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_lib import load_modules_config  # noqa: E402

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


def unit_icon(entry):
    unit = entry.get('unit')
    if not unit:
        return '—'
    return class_icon(unit.get('class'))


def acceptance_status(entry):
    # Config-derived disposition; falls back to the legacy boolean for old ledgers.
    status = entry.get('acceptance_status')
    if status:
        return status
    return 'running' if entry.get('acceptance_configured') else 'none'


def acceptance_cell(entry):
    status = acceptance_status(entry)
    if status == 'none':
        return 'N/A'
    if status == 'blocked':
        return '⛔ blocked'
    if status == 'pending':
        return '🚧 pending'
    # status == 'running'
    acceptance = entry.get('acceptance')
    if not acceptance or not acceptance.get('targets'):
        return '⏳ awaiting run'
    targets = acceptance['targets']
    return ' '.join(f"{name}:{class_icon(cls)}" for name, cls in sorted(targets.items()))


def unit_passed(entry):
    unit = entry.get('unit')
    return bool(unit) and is_pass(unit.get('class'))


def acceptance_passed(entry):
    acceptance = entry.get('acceptance')
    return bool(acceptance) and bool(acceptance.get('targets')) and is_pass(acceptance.get('class'))


def is_fully_compatible(entry):
    if not unit_passed(entry):
        return False
    status = acceptance_status(entry)
    if status == 'none':
        return True  # no acceptance tests exist — unit coverage is full coverage
    if status == 'running':
        return acceptance_passed(entry)
    # blocked / pending: acceptance tests exist but were never exercised here, so
    # coverage is incomplete. These are NOT fully compatible.
    return False


def last_tested(entry):
    stamps = []
    if entry.get('unit', {}).get('tested_at'):
        stamps.append(parse_ts(entry['unit']['tested_at']))
    if entry.get('acceptance', {}).get('tested_at'):
        stamps.append(parse_ts(entry['acceptance']['tested_at']))
    stamps = [s for s in stamps if s]
    return max(stamps) if stamps else None


def main():
    ledger_file = os.environ.get('LEDGER_FILE', 'status/ledger.json')
    modules_file = os.environ.get('MODULES_FILE', 'config/modules.json')
    status_file = os.environ.get('STATUS_FILE', 'STATUS.md')
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

    unit_tested = [e for e in active.values() if e.get('unit')]
    unit_pass = [e for e in unit_tested if unit_passed(e)]
    unit_fail = [e for e in unit_tested if not unit_passed(e)]

    acceptance_running = [e for e in active.values() if acceptance_status(e) == 'running']
    acceptance_run = [e for e in acceptance_running if e.get('acceptance', {}).get('targets')]
    acceptance_pass = [e for e in acceptance_run if acceptance_passed(e)]
    acceptance_fail = [e for e in acceptance_run if not acceptance_passed(e)]
    acceptance_blocked = [e for e in active.values() if acceptance_status(e) == 'blocked']
    acceptance_pending = [e for e in active.values() if acceptance_status(e) == 'pending']
    acceptance_none = [e for e in active.values() if acceptance_status(e) == 'none']

    fully_compatible = [e for e in active.values() if is_fully_compatible(e)]
    never_tested = [e for e in active.values() if not e.get('unit')]
    stale = []
    for entry in unit_tested:
        stamp = last_tested(entry)
        if stamp is not None and stamp < stale_cutoff:
            stale.append(entry)

    versions = sorted({e['puppet_core_version'] for e in active.values() if e.get('puppet_core_version')})

    lines = []
    lines.append('# Module Compatibility Status')
    lines.append('')
    lines.append('> Auto-generated from `status/ledger.json` by `scripts/render_status_dashboard.py`.')
    lines.append('> Do not edit by hand — changes will be overwritten on the next run.')
    lines.append('')
    lines.append(f"**Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}  ")
    lines.append(f"**Puppet Core:** {', '.join(versions) if versions else 'unknown'}  ")
    lines.append(f"**Staleness threshold:** {stale_days} days")
    lines.append('')

    lines.append('## Summary')
    lines.append('')
    lines.append('| Metric | Count |')
    lines.append('|---|---|')
    lines.append(f"| Active modules | {len(active)} |")
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
    lines.append(f"| Stale (> {stale_days}d) | {len(stale)} |")
    lines.append(f"| Retired (incompatible / deprecated) | {len(retired)} |")
    if anomalies:
        lines.append(f"| ⚠️ Removed without disposition | {len(anomalies)} |")
    lines.append('')

    lines.append('## Active Modules')
    lines.append('')
    lines.append('> Acceptance column: `target:✅/❌` = ran, `N/A` = no acceptance tests exist upstream, '
                 '`⛔ blocked` = tests exist but cannot run in this harness, `🚧 pending` = tests exist but '
                 'not yet wired up, `⏳ awaiting run` = enabled but no result yet. Only ✅/N/A count toward '
                 '**Fully compatible**.')
    lines.append('')
    lines.append('| Module | Puppet Core | Unit | Acceptance | Coverage | Last Tested |')
    lines.append('|---|---|---|---|---|---|')
    for module_id in sorted(active):
        entry = active[module_id]
        repo = entry.get('repo', '')
        name = f"[{module_id}]({repo})" if repo else module_id
        stamp = last_tested(entry)
        when = stamp.strftime('%Y-%m-%d') if stamp else '—'
        if stamp is not None and stamp < stale_cutoff:
            when += ' ⏰'
        lines.append(
            f"| {name} | {entry.get('puppet_core_version', '—')} | {unit_icon(entry)} "
            f"| {acceptance_cell(entry)} | {entry.get('coverage_state', '—')} | {when} |"
        )
    lines.append('')

    not_exercised = sorted(
        [mid for mid in active if acceptance_status(active[mid]) in ('blocked', 'pending')]
    )
    if not_exercised:
        lines.append('## Acceptance Tests Not Exercised')
        lines.append('')
        lines.append('> These modules have acceptance tests upstream, but the harness has not run them — '
                     'so their compatibility is confirmed by unit tests only, **not** fully. This is distinct '
                     'from `N/A` (no acceptance tests exist).')
        lines.append('')
        lines.append('| Module | Status | Reason |')
        lines.append('|---|---|---|')
        for module_id in not_exercised:
            entry = active[module_id]
            repo = entry.get('repo', '')
            name = f"[{module_id}]({repo})" if repo else module_id
            status = acceptance_status(entry)
            label = '⛔ blocked' if status == 'blocked' else '🚧 pending'
            reason = entry.get('acceptance_reason', '').replace('\n', ' ').strip() or '—'
            lines.append(f"| {name} | {label} | {reason} |")
        lines.append('')

    if retired or anomalies:
        lines.append('## Retired / Removed')
        lines.append('')
        lines.append('| Module | Disposition | Last Known Unit | Last Tested |')
        lines.append('|---|---|---|---|')
        for module_id in sorted({**retired, **anomalies}):
            entry = modules[module_id]
            repo = entry.get('repo', '')
            name = f"[{module_id}]({repo})" if repo else module_id
            stamp = last_tested(entry)
            when = stamp.strftime('%Y-%m-%d') if stamp else '—'
            lines.append(f"| {name} | {entry.get('disposition')} | {unit_icon(entry)} | {when} |")
        lines.append('')

    if anomalies:
        lines.append('> ⚠️ **Removed without disposition:** the module(s) above are in the ledger but '
                     'no longer in `config/modules.json` and are not listed in `KNOWN_INCOMPATIBLE.md` '
                     'or `KNOWN_DEPRECATED.md`. Add a disposition or restore them to the config.')
        lines.append('')

    os.makedirs(os.path.dirname(status_file) or '.', exist_ok=True)
    with open(status_file, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(lines))

    print(
        f"STATUS.md rendered: {len(active)} active, {len(fully_compatible)} fully compatible, "
        f"{len(stale)} stale, {len(retired)} retired, {len(anomalies)} anomalies."
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
