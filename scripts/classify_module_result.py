import datetime
import json
import os
import sys


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def resolve_puppet_version(profile_name: str) -> str:
    if not profile_name:
        return 'unknown'
    profiles_file = os.environ.get('PROFILES_FILE', 'profiles/puppet_profiles.json')
    try:
        with open(profiles_file, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        for profile in data.get('profiles', []):
            if profile.get('name') == profile_name:
                return profile.get('puppet_core_version', 'unknown')
    except (OSError, ValueError):
        pass
    return 'unknown'


def main() -> int:
    report = os.environ['REPORT']
    status_file = os.environ['STATUS_FILE']
    module_id = os.environ['MODULE_ID']
    test_lane = os.environ.get('TEST_LANE', 'unit').strip() or 'unit'
    acceptance_target = os.environ.get('ACCEPTANCE_TARGET', '').strip()
    profile_env = os.environ.get('PROFILE', '').strip()

    payload = {
        'id': module_id,
        'lane': test_lane,
        'acceptance_target': acceptance_target,
        'class': 'failure',
        'compatibility_state': 'missing_report',
        'metadata_status': 'unknown',
        'metadata_message': '',
        'dependency_status': 'unknown',
        'dependency_message': '',
        'documentation_status': 'unknown',
        'documentation_message': '',
        'profile': profile_env,
        'puppet_core_version': resolve_puppet_version(profile_env),
        'tested_at': utc_now(),
        'message': 'compatibility-report.json not found',
    }

    if os.path.exists(report):
        with open(report, 'r', encoding='utf-8') as handle:
            parsed = json.load(handle)

        result = (parsed.get('results') or [{}])[0]
        state = result.get('compatibility_state', 'unknown')
        profile_name = result.get('profile') or profile_env
        tested_at = result.get('started_at') or utc_now()
        metadata = result.get('metadata_status', 'unknown')
        metadata_message = result.get('metadata_message', '')
        dependency = result.get('dependency_status', 'none')
        dependency_message = result.get('dependency_message', '')
        documentation = result.get('documentation_status', 'none')
        documentation_message = result.get('documentation_message', '')

        if state in ('harness_error', 'not_compatible'):
            klass = 'failure'
        elif dependency == 'warning' or documentation == 'warning' or state == 'conditionally_compatible' or metadata != 'supported':
            klass = 'warning'
        else:
            klass = 'clean'

        message = f'state={state} metadata={metadata} dependency={dependency} documentation={documentation}'
        if dependency_message:
            message = f'{message} {dependency_message}'
        if documentation_message:
            message = f'{message} {documentation_message}'

        payload = {
            'id': module_id,
            'lane': test_lane,
            'acceptance_target': acceptance_target,
            'class': klass,
            'compatibility_state': state,
            'metadata_status': metadata,
            'metadata_message': metadata_message,
            'dependency_status': dependency,
            'dependency_message': dependency_message,
            'documentation_status': documentation,
            'documentation_message': documentation_message,
            'profile': profile_name,
            'puppet_core_version': resolve_puppet_version(profile_name),
            'tested_at': tested_at,
            'message': message,
        }

    with open(status_file, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)

    print(
        f"[{payload['id']}] lane={payload.get('lane', 'unit')} class={payload['class']} "
        f"state={payload['compatibility_state']} "
        f"metadata={payload['metadata_status']} dependency={payload['dependency_status']} documentation={payload['documentation_status']}"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())