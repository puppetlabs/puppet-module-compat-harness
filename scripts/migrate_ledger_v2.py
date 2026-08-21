"""One-time migration: lift ledger schema v1's flat per-module fields into the
v2 `puppet_majors` map (see docs/puppet-core-9-dual-major-support.md §3).

Today's ledger is implicitly all major 8, so every module's flat `unit` /
`acceptance` / `puppet_core_version` / `metadata_status` / `dependency_status`
/ `documentation_status` / `coverage_state` fields move under
`puppet_majors["8"]` unchanged. Fields that describe the module itself rather
than a test outcome (`repo`, `ref`, `disposition`, `deprecated`,
`acceptance_configured`, `acceptance_status`, `acceptance_reason`) stay at the
module level.

Idempotent: a ledger already at schema_version 2 is left untouched.

Environment:
  LEDGER_FILE  ledger path to migrate in place (default: status/ledger.json)
  DRY_RUN      'true' to print a summary without writing (default: false)
"""

import json
import os
import sys

_MAJOR_8_KEYS = (
    'puppet_core_version',
    'unit',
    'acceptance',
    'metadata_status',
    'dependency_status',
    'documentation_status',
    'coverage_state',
)


def migrate(ledger):
    if ledger.get('schema_version') == 2:
        return 0

    migrated = 0
    for entry in ledger.get('modules', {}).values():
        major_8 = {}
        for key in _MAJOR_8_KEYS:
            if key in entry:
                major_8[key] = entry.pop(key)
        if major_8:
            entry['puppet_majors'] = {'8': major_8}
            migrated += 1

    ledger['schema_version'] = 2
    return migrated


def main():
    ledger_file = os.environ.get('LEDGER_FILE', 'status/ledger.json')
    dry_run = os.environ.get('DRY_RUN', 'false').strip().lower() == 'true'

    with open(ledger_file, 'r', encoding='utf-8') as handle:
        ledger = json.load(handle)

    if ledger.get('schema_version') == 2:
        print(f"{ledger_file} is already schema_version 2; nothing to do.")
        return 0

    migrated = migrate(ledger)

    if dry_run:
        print(f"[dry-run] would migrate {migrated} module(s) in {ledger_file} to schema_version 2.")
        return 0

    with open(ledger_file, 'w', encoding='utf-8') as handle:
        json.dump(ledger, handle, indent=2, sort_keys=True)
        handle.write('\n')

    print(f"Migrated {migrated} module(s) in {ledger_file} to schema_version 2.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
