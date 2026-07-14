"""Decide which modules need testing this run (lean matrix — Phase 2).

See docs/lean-testing-and-status-ledger-design.md. Rules:

  run_all = true IF
      a material harness path changed within the window, OR
      (manual workflow_dispatch AND lean == false)

  else include a module IF
      its ledger status is NOT green (never-tested / unit-failing / acceptance-failing), OR
      it is stale (not tested in > STALE_DAYS), OR
      it had an upstream commit on its ref within the window (GitHub API)

Everything else is skipped and recorded with a reason. Any indeterminate signal
(git failure, API error, non-GitHub host) fails safe by INCLUDING the module.

Outputs:
  - OUTPUT_FILE (default .tmp/change-decisions.json): full decision record.
  - GITHUB_OUTPUT (if set): `run_all` and `include_ids` (compact JSON array).

Environment:
  MODULES_FILE       config/modules.json
  LEDGER_FILE        status/ledger.json
  OUTPUT_FILE        .tmp/change-decisions.json
  WINDOW_HOURS       upstream/harness change window (default 48)
  STALE_DAYS         staleness threshold (default 30)
  EVENT_NAME         github.event_name (schedule | workflow_dispatch | ...)
  LEAN               'true' | 'false' (manual dispatch lean toggle; default true)
  GITHUB_TOKEN       for the commits API (falls back to unauthenticated)
  GITHUB_API_URL     default https://api.github.com
"""

import datetime
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_lib import load_modules_config  # noqa: E402

MATERIAL_PATHS = ['lib', 'bin', 'profiles', 'scripts', '.github', 'Gemfile', 'Gemfile.lock']
NOT_GREEN_STATES = {'never-tested', 'unit-failing', 'acceptance-failing'}
_GITHUB_URL = re.compile(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$')


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def iso_z(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


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


def harness_changed(window_hours):
    """True if any material harness path has a commit within the window."""
    paths = [p for p in MATERIAL_PATHS if os.path.exists(p)]
    if not paths:
        return True, 'assuming harness changed (no material paths found to diff)'
    try:
        result = subprocess.run(
            ['git', 'log', f'--since={window_hours} hours ago', '--pretty=format:%H', '--', *paths],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        return True, f'assuming harness changed (git check failed: {error})'
    commits = [line for line in result.stdout.splitlines() if line.strip()]
    if commits:
        return True, f'{len(commits)} harness commit(s) on material paths within {window_hours}h'
    return False, None


def last_tested(entry):
    stamps = [
        parse_ts(entry.get('unit', {}).get('tested_at')),
        parse_ts(entry.get('acceptance', {}).get('tested_at')),
    ]
    stamps = [s for s in stamps if s]
    return max(stamps) if stamps else None


def upstream_changed(repo_url, ref, since_iso, token, api_base):
    """Return (changed, note). Fail-safe: on any error, treat as changed."""
    match = _GITHUB_URL.match(repo_url.strip())
    if not match:
        return True, f'included (fail-safe): non-GitHub host, cannot check {repo_url}'
    owner_repo = f'{match.group(1)}/{match.group(2)}'
    url = f'{api_base}/repos/{owner_repo}/commits?sha={ref}&since={since_iso}&per_page=1'
    request = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'puppet-module-compat-harness',
    })
    if token:
        request.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (urllib.error.URLError, ValueError, TimeoutError) as error:
        return True, f'included (fail-safe): commits API error ({error})'
    if isinstance(payload, list) and payload:
        return True, None
    return False, None


def main():
    modules_file = os.environ.get('MODULES_FILE', 'config/modules.json')
    ledger_file = os.environ.get('LEDGER_FILE', 'status/ledger.json')
    output_file = os.environ.get('OUTPUT_FILE', '.tmp/change-decisions.json')
    window_hours = int(os.environ.get('WINDOW_HOURS', '48'))
    stale_days = int(os.environ.get('STALE_DAYS', '30'))
    event_name = os.environ.get('EVENT_NAME', 'schedule')
    lean = os.environ.get('LEAN', 'true').strip().lower() != 'false'
    token = os.environ.get('GITHUB_TOKEN', '')
    api_base = os.environ.get('GITHUB_API_URL', 'https://api.github.com')

    now = utc_now()
    since_iso = iso_z(now - datetime.timedelta(hours=window_hours))
    stale_cutoff = now - datetime.timedelta(days=stale_days)

    config = load_modules_config(modules_file)
    ledger_modules = {}
    if os.path.exists(ledger_file):
        with open(ledger_file, 'r', encoding='utf-8') as handle:
            ledger_modules = json.load(handle).get('modules', {})

    harness_hit, harness_reason = harness_changed(window_hours)
    if harness_hit:
        run_all, run_all_reason = True, harness_reason
    elif event_name == 'workflow_dispatch' and not lean:
        run_all, run_all_reason = True, 'manual dispatch with lean=false'
    else:
        run_all, run_all_reason = False, f'harness unchanged; per-module filtering ({window_hours}h window)'

    included, skipped = [], []
    for module_id in sorted(config):
        cfg = config[module_id]
        entry = ledger_modules.get(module_id)
        coverage = entry.get('coverage_state', 'never-tested') if entry else 'never-tested'

        if run_all:
            included.append({'id': module_id, 'reason': f'run_all: {run_all_reason}'})
            continue

        reason = None
        if coverage in NOT_GREEN_STATES:
            reason = f'ledger status: {coverage}'
        else:
            stamp = last_tested(entry) if entry else None
            if stamp is None or stamp < stale_cutoff:
                when = stamp.strftime('%Y-%m-%d') if stamp else 'never'
                reason = f'stale: last tested {when} (> {stale_days}d)'
            else:
                changed, note = upstream_changed(cfg['repo'], cfg['ref'], since_iso, token, api_base)
                if changed:
                    reason = note or f'upstream commit within {window_hours}h'

        if reason:
            included.append({'id': module_id, 'reason': reason})
        else:
            stamp = last_tested(entry)
            when = stamp.strftime('%Y-%m-%d') if stamp else 'never'
            skipped.append({
                'id': module_id,
                'reason': f'no upstream change in {window_hours}h; ledger {coverage}; last tested {when}',
            })

    decisions = {
        'generated_at': iso_z(now),
        'run_all': run_all,
        'run_all_reason': run_all_reason,
        'window_hours': window_hours,
        'stale_days': stale_days,
        'event_name': event_name,
        'lean': lean,
        'included': included,
        'skipped': skipped,
    }

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as handle:
        json.dump(decisions, handle, indent=2)
        handle.write('\n')

    include_ids = [item['id'] for item in included]
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a', encoding='utf-8') as handle:
            handle.write(f"run_all={'true' if run_all else 'false'}\n")
            handle.write(f'include_ids={json.dumps(include_ids)}\n')

    print(f"Change detection: run_all={run_all} ({run_all_reason})")
    print(f"  included={len(included)} skipped={len(skipped)} of {len(config)} modules")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
