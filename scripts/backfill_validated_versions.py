"""One-time backfill: reconstruct puppet_majors[major].validated_versions from
the full git history of status/ledger.json (see
docs/lean-testing-and-status-ledger-design.md and
docs/puppet-core-9-dual-major-support.md §3).

validated_versions did not exist before schema_version 3 (see
ledger_lib.record_validated_version / scripts/update_ledger.py), so every
version a module was ever confirmed fully compatible with — prior to this
script existing — would otherwise be lost the moment the harness profile
rolled past it. This script replays every historical revision of the ledger,
oldest first, through the exact same last-confirmed/retract-on-failure state
machine that update_ledger.py now applies live, so the result is identical to
what would exist had this field been written from day one.

Each historical commit is one snapshot: for every (module, major) with a
puppet_core_version present, the replay records that version as validated if
the snapshot's own data shows it fully compatible, or retracts it if not.
Because replay is chronological, a later commit's verdict always overrides an
earlier one for the *same* version, and a version only survives the full
replay if it was never subsequently shown failing while it was still being
tested at that pin.

Idempotent: re-running only adds keys absent from the current ledger; it never
overwrites or removes an entry the live ledger already has.

Environment:
  LEDGER_FILE  ledger path to update in place (default: status/ledger.json)
  DRY_RUN      'true' to print a summary without writing (default: false)
"""

import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_lib import is_fully_compatible, record_validated_version  # noqa: E402

SCHEMA_VERSION = 3
_MAJOR_8_KEYS = (
    'puppet_core_version',
    'unit',
    'acceptance',
    'metadata_status',
    'dependency_status',
    'documentation_status',
    'coverage_state',
)


def run_git(args):
    result = subprocess.run(['git'] + args, capture_output=True, text=True, check=True)
    return result.stdout


def ledger_commits(path='status/ledger.json'):
    """All commits touching the ledger, oldest first — replay order matters."""
    output = run_git(['log', '--follow', '--format=%H', '--reverse', '--', path])
    return [line for line in output.splitlines() if line]


def ledger_at(sha, path='status/ledger.json'):
    try:
        output = subprocess.run(
            ['git', 'show', f'{sha}:{path}'],
            capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def commit_timestamp(sha):
    # Normalize to the same 'YYYY-MM-DDTHH:MM:SSZ' (UTC) shape used elsewhere.
    iso = run_git(['show', '-s', '--format=%cI', sha]).strip()
    parsed = datetime.datetime.fromisoformat(iso)
    return parsed.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def major_slices(entry):
    """Yield (major, slice, context_entry) for every major present in this
    module entry, normalizing schema v1 (flat, implicitly major 8) and v2
    (nested under puppet_majors) to the same shape is_fully_compatible expects.
    """
    if 'puppet_majors' in entry:
        for major, slice_ in entry.get('puppet_majors', {}).items():
            yield major, slice_, entry
    elif any(key in entry for key in _MAJOR_8_KEYS):
        yield '8', entry, entry


def snapshot_tested_at(slice_, fallback):
    stamps = [
        slice_.get('unit', {}).get('tested_at'),
        slice_.get('acceptance', {}).get('tested_at'),
    ]
    stamps = [s for s in stamps if s]
    return max(stamps) if stamps else fallback


def replay(commits):
    """Returns {(module_id, major): {version: last_confirmed_at}}."""
    accumulator = {}
    commit_ts_cache = {}

    for sha in commits:
        ledger = ledger_at(sha)
        if not ledger:
            continue
        modules = ledger.get('modules', {})
        if not modules:
            continue

        fallback_ts = None  # lazily computed only if a snapshot lacks tested_at

        for module_id, entry in modules.items():
            for major, slice_, context in major_slices(entry):
                version = slice_.get('puppet_core_version')
                if not version:
                    continue
                if fallback_ts is None:
                    fallback_ts = commit_ts_cache.setdefault(sha, commit_timestamp(sha))
                tested_at = snapshot_tested_at(slice_, fallback_ts)
                compatible = is_fully_compatible(slice_, context)
                key = (module_id, major)
                # record_validated_version expects a major_entry-shaped dict (it
                # writes through a 'validated_versions' sub-key); wrap the
                # accumulator's versions dict by reference so mutations land
                # directly on accumulator[key] instead of a throwaway wrapper.
                versions = accumulator.setdefault(key, {})
                record_validated_version({'validated_versions': versions}, version, compatible, tested_at)

    return accumulator


def merge(ledger, accumulator):
    added = 0
    touched_modules = set()
    for (module_id, major), versions in accumulator.items():
        if not versions:
            continue
        module_entry = ledger['modules'].setdefault(module_id, {})
        major_entry = module_entry.setdefault('puppet_majors', {}).setdefault(major, {})
        existing = major_entry.setdefault('validated_versions', {})
        for version, tested_at in versions.items():
            if version not in existing:
                existing[version] = tested_at
                added += 1
                touched_modules.add(module_id)
    return added, touched_modules


def main():
    ledger_file = os.environ.get('LEDGER_FILE', 'status/ledger.json')
    dry_run = os.environ.get('DRY_RUN', 'false').strip().lower() == 'true'

    commits = ledger_commits(ledger_file)
    print(f"Replaying {len(commits)} historical revision(s) of {ledger_file}...")
    accumulator = replay(commits)

    with open(ledger_file, 'r', encoding='utf-8') as handle:
        ledger = json.load(handle)

    added, touched_modules = merge(ledger, accumulator)
    ledger['schema_version'] = SCHEMA_VERSION

    multi_version = sorted(
        (module_id, major, sorted(versions))
        for (module_id, major), versions in accumulator.items()
        if len(versions) > 1
    )

    print(f"Backfilled {added} validated-version entr{'y' if added == 1 else 'ies'} "
          f"across {len(touched_modules)} module(s).")
    print(f"{len(multi_version)} (module, major) pair(s) have more than one validated version. Examples:")
    for module_id, major, versions in multi_version[:10]:
        print(f"  {module_id} (Puppet {major}): {', '.join(versions)}")

    if dry_run:
        print("[dry-run] no file written.")
        return 0

    with open(ledger_file, 'w', encoding='utf-8') as handle:
        json.dump(ledger, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(f"Wrote {ledger_file}.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
