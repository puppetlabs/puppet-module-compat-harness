"""Render docs/available-acceptance-tests.md from config/modules.json.

This is a pure presentation layer over the acceptance disposition declared in
`config/modules.json` (see the `acceptance.status` field and its `reason`). It
does not inspect module repositories — the config is the source of truth, so the
doc cannot drift from what the harness actually does.

Status vocabulary (from modules.json `acceptance.status`):
  running — tests exist upstream and run in CI (✅)
  blocked — tests exist upstream but cannot run in this harness (⛔, reason set)
  pending — tests exist upstream but are not yet wired up here (🚧, reason set)
  none    — no acceptance tests exist upstream

Environment:
  MODULES_FILE  modules config (default: config/modules.json)
  AUDIT_FILE    output path (default: docs/available-acceptance-tests.md)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_lib import load_modules_config  # noqa: E402

STATUS_ICON = {'running': '✅', 'blocked': '⛔', 'pending': '🚧'}
STATUS_LABEL = {'running': '✅ running', 'blocked': '⛔ blocked', 'pending': '🚧 pending'}


def module_link(cfg):
    repo = cfg.get('repo', '')
    return f"[{cfg['id']}]({repo})" if repo else cfg['id']


def main():
    modules_file = os.environ.get('MODULES_FILE', 'config/modules.json')
    audit_file = os.environ.get('AUDIT_FILE', 'docs/available-acceptance-tests.md')

    config = load_modules_config(modules_file)
    modules = [config[mid] for mid in sorted(config)]

    with_tests = [m for m in modules if m['acceptance_status'] in ('running', 'blocked', 'pending')]
    without_tests = [m for m in modules if m['acceptance_status'] == 'none']
    not_run = [m for m in modules if m['acceptance_status'] in ('blocked', 'pending')]

    lines = []
    lines.append('# Available Acceptance Tests')
    lines.append('')
    lines.append('> Auto-generated from `config/modules.json` by `scripts/render_acceptance_audit.py`.')
    lines.append('> Do not edit by hand — update the `acceptance` block in `config/modules.json` instead.')
    lines.append('')
    lines.append('Audit of the acceptance-test disposition of every module in `config/modules.json`.')
    lines.append('')

    lines.append(f'## Modules With Acceptance Tests ({len(with_tests)})')
    lines.append('')
    lines.append('Modules whose upstream repository contains acceptance tests. '
                 '✅ run in CI; ⛔ blocked (cannot run in this harness); 🚧 pending (not yet wired up).')
    lines.append('')
    lines.append('| Status | Module |')
    lines.append('|--------|--------|')
    for m in with_tests:
        lines.append(f"| {STATUS_ICON[m['acceptance_status']]} | {module_link(m)} |")
    lines.append('')

    lines.append(f'## Modules Without Acceptance Tests ({len(without_tests)})')
    lines.append('')
    lines.append('Repos where no acceptance-test entrypoint exists upstream. '
                 'Unit coverage alone is full coverage for these modules.')
    lines.append('')
    lines.append('| Module |')
    lines.append('|--------|')
    for m in without_tests:
        lines.append(f"| {module_link(m)} |")
    lines.append('')

    lines.append(f'## Modules With Acceptance Tests but Not Run in CI ({len(not_run)})')
    lines.append('')
    lines.append('These modules have acceptance tests upstream, but the harness does not run them — so '
                 'their compatibility is confirmed by unit tests only, not fully. They are intentionally '
                 'excluded from `KNOWN_COMPATIBLE.md`.')
    lines.append('')
    lines.append('| Module | Status | Reason |')
    lines.append('|--------|--------|--------|')
    for m in not_run:
        reason = (m.get('acceptance_reason') or '').replace('\n', ' ').strip() or '—'
        lines.append(f"| {module_link(m)} | {STATUS_LABEL[m['acceptance_status']]} | {reason} |")
    lines.append('')

    os.makedirs(os.path.dirname(audit_file) or '.', exist_ok=True)
    with open(audit_file, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(lines))

    print(
        f"Acceptance audit rendered: {len(with_tests)} with tests "
        f"({len(not_run)} not run in CI), {len(without_tests)} without tests."
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
