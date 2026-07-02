# Known Compatible Modules

This document lists modules that have been fully validated against Puppet Core — meaning all available tests have passed.

**N/A in the Acceptance column** means the module has no acceptance tests in its upstream repository. Unit tests alone constitute full coverage for that module, and N/A is an intentional distinction from ✅: it does not mean acceptance was skipped or blocked — there is simply nothing to run.

Modules with upstream acceptance tests that cannot currently run in the harness (due to Docker/container limitations) are **not listed here** — they have not had all available tests exercised. See [docs/available-acceptance-tests.md](docs/available-acceptance-tests.md) for the full audit including blocked modules.

**Distinction from [KNOWN_INCOMPATIBLE.md](KNOWN_INCOMPATIBLE.md):** Modules listed here have passed all tests available to this harness. KNOWN_INCOMPATIBLE.md lists modules tested and found to have compatibility failures.

## Compatibility Summary

| Module | Puppet Core | Unit | Acceptance |
|--------|-------------|------|------------|
| [puppet-alternatives](https://github.com/voxpupuli/puppet-alternatives) | 8.19.0 | ✅ | ✅ |
| [puppet-archive](https://github.com/voxpupuli/puppet-archive) | 8.19.0 | ✅ | ✅ |
| [puppet-augeas](https://github.com/voxpupuli/puppet-augeas) | 8.19.0 | ✅ | ✅ |
| [puppet-augeasproviders_core](https://github.com/voxpupuli/puppet-augeasproviders_core) | 8.19.0 | ✅ | N/A |
| [puppet-augeasproviders_pam](https://github.com/voxpupuli/puppet-augeasproviders_pam) | 8.19.0 | ✅ | N/A |
| [puppet-augeasproviders_shellvar](https://github.com/voxpupuli/puppet-augeasproviders_shellvar) | 8.19.0 | ✅ | N/A |
| [puppet-augeasproviders_ssh](https://github.com/voxpupuli/puppet-augeasproviders_ssh) | 8.19.0 | ✅ | ✅ |
| [puppet-augeasproviders_sysctl](https://github.com/voxpupuli/puppet-augeasproviders_sysctl) | 8.19.0 | ✅ | ✅ |
| [puppet-autofs](https://github.com/voxpupuli/puppet-autofs) | 8.19.0 | ✅ | ✅ |
| [puppet-ca_cert](https://github.com/voxpupuli/puppet-ca_cert) | 8.19.0 | ✅ | ✅ |
| [puppet-chrony](https://github.com/voxpupuli/puppet-chrony) | 8.19.0 | ✅ | ✅ |
| [puppet-confluence](https://github.com/voxpupuli/puppet-confluence) | 8.19.0 | ✅ | ✅ |
| [puppet-cron](https://github.com/voxpupuli/puppet-cron) | 8.19.0 | ✅ | ✅ |
| [puppet-dnsquery](https://github.com/voxpupuli/puppet-dnsquery) | 8.19.0 | ✅ | N/A |
| [puppet-epel](https://github.com/voxpupuli/puppet-epel) | 8.19.0 | ✅ | ✅ |
| [puppet-extlib](https://github.com/voxpupuli/puppet-extlib) | 8.19.0 | ✅ | N/A |
| [puppet-filemapper](https://github.com/voxpupuli/puppet-filemapper) | 8.19.0 | ✅ | N/A |
| [puppet-firewalld](https://github.com/voxpupuli/puppet-firewalld) | 8.19.0 | ✅ | ✅ |
| [puppet-format](https://github.com/voxpupuli/puppet-format) | 8.19.0 | ✅ | N/A |
| [puppet-gitlab](https://github.com/voxpupuli/puppet-gitlab) | 8.19.0 | ✅ | ✅ |
| [puppet-gitlab_ci_runner](https://github.com/voxpupuli/puppet-gitlab_ci_runner) | 8.19.0 | ✅ | ✅ |
| [puppet-grafana](https://github.com/voxpupuli/puppet-grafana) | 8.19.0 | ✅ | ✅ |
| [puppet-hdm](https://github.com/voxpupuli/puppet-hdm) | 8.19.0 | ✅ | N/A |
| [puppet-hiera](https://github.com/voxpupuli/puppet-hiera) | 8.19.0 | ✅ | ✅ |
| [puppet-keepalived](https://github.com/voxpupuli/puppet-keepalived) | 8.19.0 | ✅ | ✅ |
| [puppet-kibana](https://github.com/voxpupuli/puppet-kibana) | 8.19.0 | ✅ | ✅ |
| [puppet-kmod](https://github.com/voxpupuli/puppet-kmod) | 8.19.0 | ✅ | N/A |
| [puppet-logrotate](https://github.com/voxpupuli/puppet-logrotate) | 8.19.0 | ✅ | ✅ |
| [puppet-nfs](https://github.com/voxpupuli/puppet-nfs) | 8.20.0 | ✅ | ✅ |
| [puppet-nftables](https://github.com/voxpupuli/puppet-nftables) | 8.19.0 | ✅ | ✅ |
| [puppet-openssl](https://github.com/voxpupuli/puppet-openssl) | 8.19.0 | ✅ | ✅ |
| [puppet-nginx](https://github.com/voxpupuli/puppet-nginx) | 8.19.0 | ✅ | ✅ |
| [puppet-nodejs](https://github.com/voxpupuli/puppet-nodejs) | 8.19.0 | ✅ | ✅ |
| [puppet-nsswitch](https://github.com/voxpupuli/puppet-nsswitch) | 8.19.0 | ✅ | ✅ |
| [puppet-openvox_bootstrap](https://github.com/voxpupuli/puppet-openvox_bootstrap) | 8.19.0 | ✅ | N/A |
| [puppet-php](https://github.com/voxpupuli/puppet-php) | 8.19.0 | ✅ | ✅ |
| [puppet-posix_acl](https://github.com/voxpupuli/puppet-posix_acl) | 8.19.0 | ✅ | ✅ |
| [puppet-postfix](https://github.com/voxpupuli/puppet-postfix) | 8.19.0 | ✅ | ✅ |
| [puppet-prometheus](https://github.com/voxpupuli/puppet-prometheus) | 8.19.0 | ✅ | ✅ |
| [puppet-prometheus_reporter](https://github.com/voxpupuli/puppet-prometheus_reporter) | 8.19.0 | ✅ | N/A |
| [puppet-python](https://github.com/voxpupuli/puppet-python) | 8.19.0 | ✅ | ✅ |
| [puppet-redis](https://github.com/voxpupuli/puppet-redis) | 8.19.0 | ✅ | ✅ |
| [puppet-squid](https://github.com/voxpupuli/puppet-squid) | 8.19.0 | ✅ | ✅ |
| [puppet-sssd](https://github.com/voxpupuli/puppet-sssd) | 8.19.0 | ✅ | N/A |
| [puppet-telegraf](https://github.com/voxpupuli/puppet-telegraf) | 8.19.0 | ✅ | ✅ |
| [puppet-unattended_upgrades](https://github.com/voxpupuli/puppet-unattended_upgrades) | 8.19.0 | ✅ | ✅ |
| [puppet-yum](https://github.com/voxpupuli/puppet-yum) | 8.19.0 | ✅ | ✅ |
| [puppet-zypprepo](https://github.com/voxpupuli/puppet-zypprepo) | 8.19.0 | ✅ | N/A |
| [saz-puppet-limits](https://github.com/saz/puppet-limits) | 8.19.0 | ✅ | ✅ |
| [saz-puppet-sudo](https://github.com/saz/puppet-sudo) | 8.19.0 | ✅ | ✅ |
