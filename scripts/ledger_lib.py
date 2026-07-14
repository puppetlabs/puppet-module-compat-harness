"""Shared helpers for the status ledger (update + render).

Keeps module-id derivation identical to scripts/build_matrix.rb so the ledger,
the CI matrix, and modules.json all agree on the same stable id per module.
"""

import json
import os
import re

_ID_SANITIZE = re.compile(r'[^a-zA-Z0-9_.-]+')
_LINK_URL = re.compile(r'\]\((https?://[^)\s]+)\)')


def derive_id(repo, explicit_id=None):
    """Mirror of build_matrix.rb id derivation.

    id = explicit id if given, else the last path segment of the repo URL with
    any trailing slash and `.git` suffix removed, then sanitized.
    """
    if explicit_id:
        return explicit_id
    tail = repo.rstrip('/').split('/')[-1]
    if tail.endswith('.git'):
        tail = tail[:-4]
    return _ID_SANITIZE.sub('-', tail)


def load_modules_config(path='config/modules.json'):
    """Return {id: {repo, ref, id, deprecated, acceptance_enabled,
    acceptance_status, acceptance_reason, acceptance_targets[]}}.

    acceptance_status is one of:
      running — tests exist and run in CI (enabled).
      blocked — tests exist upstream but cannot run in this harness (reason set).
      pending — tests exist upstream but are not yet wired up here (reason set).
      none    — no acceptance tests exist upstream (rendered as N/A).

    For backward tolerance, a module whose acceptance status is absent is
    treated as 'running' when enabled, else 'none'.
    """
    with open(path, 'r', encoding='utf-8') as handle:
        data = json.load(handle)

    result = {}
    for module in data.get('modules', []):
        repo = module['repo']
        module_id = derive_id(repo, module.get('id'))
        acceptance = module.get('acceptance') if isinstance(module.get('acceptance'), dict) else {}
        enabled = bool(acceptance.get('enabled'))
        status = acceptance.get('status') or ('running' if enabled else 'none')
        reason = acceptance.get('reason', '')
        targets = []
        if enabled and isinstance(acceptance.get('targets'), list):
            targets = [
                target['name']
                for target in acceptance['targets']
                if isinstance(target, dict) and target.get('name')
            ]
        result[module_id] = {
            'repo': repo,
            'ref': module.get('ref', 'main'),
            'id': module_id,
            'deprecated': bool(module.get('deprecated', False)),
            'acceptance_enabled': enabled,
            'acceptance_status': status,
            'acceptance_reason': reason,
            'acceptance_targets': targets,
        }
    return result


def parse_known_ids(path):
    """Derive module ids from a KNOWN_*.md summary table.

    Only the first table cell (the Module column) is inspected, so that
    'Recommended Replacement' links to active modules are not misattributed.
    Returns an empty set if the file is absent.
    """
    ids = set()
    if not os.path.exists(path):
        return ids

    with open(path, 'r', encoding='utf-8') as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped.startswith('|') or '---' in stripped:
                continue
            cells = [cell.strip() for cell in stripped.split('|')]
            if len(cells) < 2:
                continue
            first = cells[1]
            if first.lower() == 'module':
                continue
            match = _LINK_URL.search(first)
            if match:
                ids.add(derive_id(match.group(1)))
    return ids
