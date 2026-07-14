"""Merge this run's module-status.json results into the persistent status ledger.

Semantics (see docs/lean-testing-and-status-ledger-design.md):
- Upsert ONLY the modules present in this run's artifacts. A module absent from
  the run is left untouched — absence never downgrades or deletes an entry.
- Seed a `never-tested` entry for any modules.json module not yet in the ledger.
- Reconcile every entry against modules.json + KNOWN_* files to set disposition.

Environment:
  STATUS_ROOT              artifact root to walk (default: all-artifacts)
  LEDGER_FILE              ledger path (default: status/ledger.json)
  MODULES_FILE             modules config (default: config/modules.json)
  KNOWN_INCOMPATIBLE_FILE  default: KNOWN_INCOMPATIBLE.md
  KNOWN_DEPRECATED_FILE    default: KNOWN_DEPRECATED.md
  GITHUB_RUN_ID, GITHUB_SHA  optional provenance stamped onto updated entries
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_lib import derive_id, load_modules_config, parse_known_ids  # noqa: E402

SCHEMA_VERSION = 1
_CLASS_RANK = {'clean': 0, 'warning': 1, 'failure': 2}


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def worst_class(classes):
    ranked = [c for c in classes if c in _CLASS_RANK]
    if not ranked:
        return 'none'
    return max(ranked, key=lambda c: _CLASS_RANK[c])


def load_ledger(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        data.setdefault('modules', {})
        return data
    return {'schema_version': SCHEMA_VERSION, 'modules': {}}


def collect_rows(root):
    rows = []
    if not os.path.isdir(root):
        return rows
    for current_root, _dirs, files in os.walk(root):
        if 'module-status.json' not in files:
            continue
        with open(os.path.join(current_root, 'module-status.json'), 'r', encoding='utf-8') as handle:
            rows.append(json.load(handle))
    return rows


def is_pass(status_class):
    # Warnings are deliberate green-keepers (e.g. tolerated metadata gaps); for
    # reporting we only distinguish pass from fail. Warning counts as pass.
    return status_class in ('clean', 'warning')


def coverage_state(entry, cfg):
    unit = entry.get('unit')
    if not unit:
        return 'never-tested'
    if not is_pass(unit.get('class')):
        return 'unit-failing'
    # Acceptance disposition comes from config (not from whether a run happened),
    # so we can distinguish "no tests exist" (N/A) from "tests exist but can't run
    # here" (blocked/pending). See docs/lean-testing-and-status-ledger-design.md §4.2.
    status = (cfg or {}).get('acceptance_status', 'none')
    if status == 'none':
        return 'unit-only'
    if status == 'blocked':
        return 'acceptance-blocked'
    if status == 'pending':
        return 'unit-pass/acceptance-pending'
    # status == 'running': coverage depends on whether acceptance actually ran/passed.
    acceptance = entry.get('acceptance')
    if not acceptance or not acceptance.get('targets'):
        return 'unit-pass/acceptance-pending'
    if is_pass(acceptance.get('class')):
        return 'unit+acceptance'
    return 'acceptance-failing'


def upsert_results(modules, config, rows, now):
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    harness_sha = os.environ.get('GITHUB_SHA', '')[:7]

    by_id = {}
    for row in rows:
        by_id.setdefault(row['id'], []).append(row)

    for module_id, group in by_id.items():
        entry = modules.setdefault(module_id, {})
        cfg = config.get(module_id, {})
        if cfg.get('repo'):
            entry['repo'] = cfg['repo']
        if cfg.get('ref'):
            entry['ref'] = cfg['ref']

        for row in group:
            version = row.get('puppet_core_version')
            if version and version != 'unknown':
                entry['puppet_core_version'] = version

            if row.get('lane', 'unit') == 'unit':
                entry['unit'] = {
                    'class': row.get('class', 'failure'),
                    'compatibility_state': row.get('compatibility_state', 'unknown'),
                    'tested_at': row.get('tested_at', now),
                    'last_run_id': run_id,
                    'last_harness_sha': harness_sha,
                }
                entry['metadata_status'] = row.get('metadata_status', 'unknown')
                entry['dependency_status'] = row.get('dependency_status', 'unknown')
                entry['documentation_status'] = row.get('documentation_status', 'unknown')
            else:
                acceptance = entry.setdefault('acceptance', {})
                targets = acceptance.setdefault('targets', {})
                target_name = row.get('acceptance_target') or 'default'
                targets[target_name] = row.get('class', 'failure')
                acceptance['tested_at'] = row.get('tested_at', now)

        if 'acceptance' in entry:
            entry['acceptance']['class'] = worst_class(entry['acceptance'].get('targets', {}).values())


def reconcile(modules, config, now):
    incompatible_ids = parse_known_ids(os.environ.get('KNOWN_INCOMPATIBLE_FILE', 'KNOWN_INCOMPATIBLE.md'))
    deprecated_ids = parse_known_ids(os.environ.get('KNOWN_DEPRECATED_FILE', 'KNOWN_DEPRECATED.md'))

    # Seed never-tested entries for config modules not yet in the ledger.
    for module_id, cfg in config.items():
        if module_id not in modules:
            modules[module_id] = {'repo': cfg['repo'], 'ref': cfg['ref']}

    for module_id, entry in modules.items():
        cfg = config.get(module_id)
        if cfg is not None:
            entry['disposition'] = 'active'
            entry['deprecated'] = cfg.get('deprecated', False)
            entry['acceptance_configured'] = cfg.get('acceptance_enabled', False)
            entry['acceptance_status'] = cfg.get('acceptance_status', 'none')
            reason = cfg.get('acceptance_reason', '')
            if reason:
                entry['acceptance_reason'] = reason
            else:
                entry.pop('acceptance_reason', None)
            entry['last_seen_in_config'] = now
        elif module_id in incompatible_ids:
            entry['disposition'] = 'incompatible'
        elif module_id in deprecated_ids:
            entry['disposition'] = 'deprecated'
        else:
            entry['disposition'] = 'removed-without-disposition'

        entry['coverage_state'] = coverage_state(entry, cfg)


def main():
    ledger_file = os.environ.get('LEDGER_FILE', 'status/ledger.json')
    modules_file = os.environ.get('MODULES_FILE', 'config/modules.json')
    status_root = os.environ.get('STATUS_ROOT', 'all-artifacts')

    now = utc_now()
    ledger = load_ledger(ledger_file)
    config = load_modules_config(modules_file)
    rows = collect_rows(status_root)

    upsert_results(ledger['modules'], config, rows, now)
    reconcile(ledger['modules'], config, now)

    ledger['schema_version'] = SCHEMA_VERSION
    ledger['generated_at'] = now

    os.makedirs(os.path.dirname(ledger_file) or '.', exist_ok=True)
    with open(ledger_file, 'w', encoding='utf-8') as handle:
        json.dump(ledger, handle, indent=2, sort_keys=True)
        handle.write('\n')

    updated = len({row['id'] for row in rows})
    print(f"Ledger updated: {updated} module(s) from this run, {len(ledger['modules'])} total tracked.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
