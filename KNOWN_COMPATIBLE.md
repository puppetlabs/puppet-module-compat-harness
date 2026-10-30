# Known Compatible Modules

> Auto-generated from `status/ledger.json` by `scripts/render_status_dashboard.py`.
> Do not edit by hand — changes will be overwritten on the next run.

This document lists modules that have been fully validated against Puppet Core on at least one tested major version — meaning all available tests have passed for that major.

Each Puppet major has its own column: **✅ &lt;version&gt;** = fully compatible on that major, **❌** = tested on that major but not fully compatible, **—** = not yet tested on that major.

**N/A in a major column context** (shown in [STATUS.md](STATUS.md), not here) means the module has no acceptance tests in its upstream repository; unit tests alone constitute full coverage. Modules with upstream acceptance tests that cannot currently run in the harness (due to Docker/container limitations) do not count as fully compatible on that major — see [docs/available-acceptance-tests.md](docs/available-acceptance-tests.md) for the full audit including blocked modules.

**Distinction from [KNOWN_INCOMPATIBLE.md](KNOWN_INCOMPATIBLE.md):** Modules listed here have passed all tests available to this harness on at least one major. KNOWN_INCOMPATIBLE.md lists modules tested and found to have compatibility failures on the gating major (or every tested major) and removed from the matrix entirely.

**⚠️ next to a module name** marks it deprecated / no longer maintained upstream. It remains compatible, but consider migrating away from it.

## Compatibility Summary

| Module | Puppet 8 | Puppet 9 |
|--------|---|---|
| [puppet-alternatives](https://github.com/voxpupuli/puppet-alternatives) | ❌ | ✅ 9.1.0 |
| [puppet-archive](https://github.com/voxpupuli/puppet-archive) | ❌ | ✅ 9.1.0 |
| [puppet-augeas](https://github.com/voxpupuli/puppet-augeas) | ❌ | ✅ 9.1.0 |
| [puppet-augeasproviders_core](https://github.com/voxpupuli/puppet-augeasproviders_core) | ❌ | ✅ 9.1.0 |
| [puppet-augeasproviders_pam](https://github.com/voxpupuli/puppet-augeasproviders_pam) | ❌ | ✅ 9.1.0 |
| [puppet-augeasproviders_shellvar](https://github.com/voxpupuli/puppet-augeasproviders_shellvar) | ❌ | ✅ 9.1.0 |
| [puppet-augeasproviders_ssh](https://github.com/voxpupuli/puppet-augeasproviders_ssh) | ❌ | ✅ 9.1.0 |
| [puppet-augeasproviders_sysctl](https://github.com/voxpupuli/puppet-augeasproviders_sysctl) | ❌ | ✅ 9.1.0 |
| [puppet-autofs](https://github.com/voxpupuli/puppet-autofs) | ❌ | ✅ 9.1.0 |
| [puppet-ca_cert](https://github.com/voxpupuli/puppet-ca_cert) | ❌ | ✅ 9.1.0 |
| [puppet-chrony](https://github.com/voxpupuli/puppet-chrony) | ❌ | ✅ 9.1.0 |
| [puppet-confluence](https://github.com/voxpupuli/puppet-confluence) | ❌ | ✅ 9.1.0 |
| [puppet-cron](https://github.com/voxpupuli/puppet-cron) | ❌ | ✅ 9.1.0 |
| [puppet-dnsquery](https://github.com/voxpupuli/puppet-dnsquery) | ❌ | ✅ 9.1.0 |
| [puppet-elastic_stack](https://github.com/voxpupuli/puppet-elastic_stack) | ❌ | ✅ 9.1.0 |
| [puppet-elasticsearch](https://github.com/voxpupuli/puppet-elasticsearch) | ❌ | ✅ 9.1.0 |
| [puppet-epel](https://github.com/voxpupuli/puppet-epel) | ❌ | ✅ 9.1.0 |
| [puppet-filemapper](https://github.com/voxpupuli/puppet-filemapper) | ❌ | ✅ 9.1.0 |
| [puppet-firewalld](https://github.com/voxpupuli/puppet-firewalld) | ❌ | ✅ 9.1.0 |
| [puppet-format](https://github.com/voxpupuli/puppet-format) | ❌ | ✅ 9.1.0 |
| [puppet-gitlab_ci_runner](https://github.com/voxpupuli/puppet-gitlab_ci_runner) | ❌ | ✅ 9.1.0 |
| [puppet-grafana](https://github.com/voxpupuli/puppet-grafana) | ❌ | ✅ 9.1.0 |
| [puppet-hdm](https://github.com/voxpupuli/puppet-hdm) | ❌ | ✅ 9.1.0 |
| [puppet-hiera](https://github.com/voxpupuli/puppet-hiera) | ❌ | ✅ 9.1.0 |
| [puppet-keepalived](https://github.com/voxpupuli/puppet-keepalived) | ❌ | ✅ 9.1.0 |
| [puppet-kibana](https://github.com/jst-cyr/puppet-kibana) | ❌ | ✅ 9.1.0 |
| [puppet-kmod](https://github.com/voxpupuli/puppet-kmod) | ❌ | ✅ 9.1.0 |
| [puppet-logrotate](https://github.com/voxpupuli/puppet-logrotate) | ❌ | ✅ 9.1.0 |
| [puppet-nfs](https://github.com/voxpupuli/puppet-nfs) | ❌ | ✅ 9.1.0 |
| [puppet-nftables](https://github.com/voxpupuli/puppet-nftables) | ❌ | ✅ 9.1.0 |
| [puppet-nginx](https://github.com/voxpupuli/puppet-nginx) | ❌ | ✅ 9.1.0 |
| [puppet-nodejs](https://github.com/voxpupuli/puppet-nodejs) | ❌ | ✅ 9.1.0 |
| [puppet-nsswitch](https://github.com/voxpupuli/puppet-nsswitch) | ❌ | ✅ 9.1.0 |
| [puppet-openssl](https://github.com/voxpupuli/puppet-openssl) | ❌ | ✅ 9.1.0 |
| [puppet-php](https://github.com/voxpupuli/puppet-php) | ❌ | ✅ 9.1.0 |
| [puppet-posix_acl](https://github.com/voxpupuli/puppet-posix_acl) | ❌ | ✅ 9.1.0 |
| [puppet-postfix](https://github.com/voxpupuli/puppet-postfix) | ❌ | ✅ 9.1.0 |
| [puppet-prometheus](https://github.com/voxpupuli/puppet-prometheus) | ❌ | ✅ 9.1.0 |
| [puppet-prometheus_reporter](https://github.com/voxpupuli/puppet-prometheus_reporter) | ❌ | ✅ 9.1.0 |
| [puppet-python](https://github.com/voxpupuli/puppet-python) | ❌ | ✅ 9.1.0 |
| [puppet-redis](https://github.com/voxpupuli/puppet-redis) | ❌ | ✅ 9.1.0 |
| [puppet-selinux](https://github.com/voxpupuli/puppet-selinux) | ❌ | ✅ 9.1.0 |
| [puppet-snmp](https://github.com/voxpupuli/puppet-snmp) | ❌ | ✅ 9.1.0 |
| [puppet-squid](https://github.com/voxpupuli/puppet-squid) | ❌ | ✅ 9.1.0 |
| [puppet-sssd](https://github.com/voxpupuli/puppet-sssd) | ❌ | ✅ 9.1.0 |
| [puppet-swap_file](https://github.com/voxpupuli/puppet-swap_file) | ❌ | ✅ 9.1.0 |
| [puppet-systemd](https://github.com/voxpupuli/puppet-systemd) | ❌ | ✅ 9.1.0 |
| [puppet-telegraf](https://github.com/voxpupuli/puppet-telegraf) | ❌ | ✅ 9.1.0 |
| [puppet-unattended_upgrades](https://github.com/voxpupuli/puppet-unattended_upgrades) | ❌ | ✅ 9.1.0 |
| [puppet-yum](https://github.com/voxpupuli/puppet-yum) | ❌ | ✅ 9.1.0 |
| [puppet-zypprepo](https://github.com/voxpupuli/puppet-zypprepo) | ❌ | ✅ 9.1.0 |
