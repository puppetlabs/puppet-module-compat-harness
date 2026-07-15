# Module Compatibility Status

> Auto-generated from `status/ledger.json` by `scripts/render_status_dashboard.py`.
> Do not edit by hand — changes will be overwritten on the next run.

**Generated:** 2026-07-15 20:31 UTC  
**Puppet Core:** 8.20.0  
**Staleness threshold:** 30 days

## Summary

| Metric | Count |
|---|---|
| Active modules | 70 |
| Unit-tested | 70 |
| &nbsp;&nbsp;• unit pass | 70 |
| &nbsp;&nbsp;• unit fail | 0 |
| Acceptance-enabled (running) | 41 |
| &nbsp;&nbsp;• acceptance run | 41 |
| &nbsp;&nbsp;• acceptance pass | 41 |
| &nbsp;&nbsp;• acceptance fail | 0 |
| ⛔ Acceptance blocked (tests exist, can't run here) | 10 |
| 🚧 Acceptance pending (tests exist, not yet wired) | 4 |
| No acceptance tests (N/A) | 15 |
| **Fully compatible** (unit pass + acceptance pass or N/A) | **56** |
| Never tested | 0 |
| Stale (> 30d) | 0 |
| ⚠️ Deprecated (unmaintained upstream) | 1 |
| Retired (incompatible / deprecated) | 0 |

## Active Modules

> Acceptance column: `target:✅/❌` = ran, `N/A` = no acceptance tests exist upstream, `⛔ blocked` = tests exist but cannot run in this harness, `🚧 pending` = tests exist but not yet wired up, `⏳ awaiting run` = enabled but no result yet. Only ✅/N/A count toward **Fully compatible**.
>
> ⚠️ next to a module name marks it **deprecated / no longer maintained upstream** — independent of compatibility (a deprecated module can still be fully compatible).

| Module | Puppet Core | Unit | Acceptance | Coverage | Last Tested |
|---|---|---|---|---|---|
| [puppet-alternatives](https://github.com/voxpupuli/puppet-alternatives) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [puppet-archive](https://github.com/voxpupuli/puppet-archive) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [puppet-augeas](https://github.com/voxpupuli/puppet-augeas) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [puppet-augeasproviders_core](https://github.com/voxpupuli/puppet-augeasproviders_core) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [puppet-augeasproviders_grub](https://github.com/voxpupuli/puppet-augeasproviders_grub) | 8.20.0 | ✅ | ⛔ blocked | acceptance-blocked | 2026-07-15 |
| [puppet-augeasproviders_pam](https://github.com/voxpupuli/puppet-augeasproviders_pam) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [puppet-augeasproviders_shellvar](https://github.com/voxpupuli/puppet-augeasproviders_shellvar) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [puppet-augeasproviders_ssh](https://github.com/voxpupuli/puppet-augeasproviders_ssh) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [puppet-augeasproviders_sysctl](https://github.com/voxpupuli/puppet-augeasproviders_sysctl) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [puppet-autofs](https://github.com/voxpupuli/puppet-autofs) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-boolean](https://github.com/voxpupuli/puppet-boolean) ⚠️ | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [puppet-ca_cert](https://github.com/voxpupuli/puppet-ca_cert) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [puppet-chrony](https://github.com/voxpupuli/puppet-chrony) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-confluence](https://github.com/voxpupuli/puppet-confluence) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-corosync](https://github.com/voxpupuli/puppet-corosync) | 8.20.0 | ✅ | debian12-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-cron](https://github.com/voxpupuli/puppet-cron) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-dnsquery](https://github.com/voxpupuli/puppet-dnsquery) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [puppet-elastic_stack](https://github.com/voxpupuli/puppet-elastic_stack) | 8.20.0 | ✅ | ⛔ blocked | acceptance-blocked | 2026-07-15 |
| [puppet-elasticsearch](https://github.com/voxpupuli/puppet-elasticsearch) | 8.20.0 | ✅ | ⛔ blocked | acceptance-blocked | 2026-07-15 |
| [puppet-epel](https://github.com/voxpupuli/puppet-epel) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [puppet-extlib](https://github.com/voxpupuli/puppet-extlib) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [puppet-filemapper](https://github.com/voxpupuli/puppet-filemapper) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [puppet-firewalld](https://github.com/voxpupuli/puppet-firewalld) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-format](https://github.com/voxpupuli/puppet-format) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [puppet-gitlab](https://github.com/voxpupuli/puppet-gitlab) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-gitlab_ci_runner](https://github.com/voxpupuli/puppet-gitlab_ci_runner) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-grafana](https://github.com/voxpupuli/puppet-grafana) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-hdm](https://github.com/voxpupuli/puppet-hdm) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [puppet-hiera](https://github.com/voxpupuli/puppet-hiera) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-jira](https://github.com/voxpupuli/puppet-jira) | 8.20.0 | ✅ | 🚧 pending | unit-pass/acceptance-pending | 2026-07-15 |
| [puppet-keepalived](https://github.com/voxpupuli/puppet-keepalived) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-kibana](https://github.com/jst-cyr/puppet-kibana) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-kmod](https://github.com/voxpupuli/puppet-kmod) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [puppet-logrotate](https://github.com/voxpupuli/puppet-logrotate) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-nfs](https://github.com/voxpupuli/puppet-nfs) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-nftables](https://github.com/voxpupuli/puppet-nftables) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-nginx](https://github.com/voxpupuli/puppet-nginx) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-nodejs](https://github.com/voxpupuli/puppet-nodejs) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [puppet-nsswitch](https://github.com/voxpupuli/puppet-nsswitch) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [puppet-openldap](https://github.com/voxpupuli/puppet-openldap) | 8.20.0 | ✅ | ⛔ blocked | acceptance-blocked | 2026-07-15 |
| [puppet-openssl](https://github.com/voxpupuli/puppet-openssl) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [puppet-openvox_bootstrap](https://github.com/voxpupuli/puppet-openvox_bootstrap) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [puppet-php](https://github.com/voxpupuli/puppet-php) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-posix_acl](https://github.com/voxpupuli/puppet-posix_acl) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [puppet-postfix](https://github.com/voxpupuli/puppet-postfix) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-prometheus](https://github.com/voxpupuli/puppet-prometheus) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-prometheus_reporter](https://github.com/voxpupuli/puppet-prometheus_reporter) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [puppet-python](https://github.com/voxpupuli/puppet-python) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [puppet-r10k](https://github.com/voxpupuli/puppet-r10k) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-redis](https://github.com/voxpupuli/puppet-redis) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-rsyslog](https://github.com/voxpupuli/puppet-rsyslog) | 8.20.0 | ✅ | ⛔ blocked | acceptance-blocked | 2026-07-15 |
| [puppet-selinux](https://github.com/voxpupuli/puppet-selinux) | 8.20.0 | ✅ | ⛔ blocked | acceptance-blocked | 2026-07-15 |
| [puppet-snmp](https://github.com/voxpupuli/puppet-snmp) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-squid](https://github.com/voxpupuli/puppet-squid) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-sssd](https://github.com/voxpupuli/puppet-sssd) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [puppet-swap_file](https://github.com/voxpupuli/puppet-swap_file) | 8.20.0 | ✅ | ⛔ blocked | acceptance-blocked | 2026-07-15 |
| [puppet-systemd](https://github.com/voxpupuli/puppet-systemd) | 8.20.0 | ✅ | ⛔ blocked | acceptance-blocked | 2026-07-15 |
| [puppet-telegraf](https://github.com/voxpupuli/puppet-telegraf) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [puppet-unattended_upgrades](https://github.com/voxpupuli/puppet-unattended_upgrades) | 8.20.0 | ✅ | ubuntu24:✅ | unit+acceptance | 2026-07-15 |
| [puppet-vault_lookup](https://github.com/voxpupuli/puppet-vault_lookup) | 8.20.0 | ✅ | ⛔ blocked | acceptance-blocked | 2026-07-15 |
| [puppet-wget](https://github.com/voxpupuli/puppet-wget) | 8.20.0 | ✅ | ⛔ blocked | acceptance-blocked | 2026-07-15 |
| [puppet-windows_env](https://github.com/voxpupuli/puppet-windows_env) | 8.20.0 | ✅ | 🚧 pending | unit-pass/acceptance-pending | 2026-07-15 |
| [puppet-windows_firewall](https://github.com/voxpupuli/puppet-windows_firewall) | 8.20.0 | ✅ | 🚧 pending | unit-pass/acceptance-pending | 2026-07-15 |
| [puppet-windowsfeature](https://github.com/voxpupuli/puppet-windowsfeature) | 8.20.0 | ✅ | 🚧 pending | unit-pass/acceptance-pending | 2026-07-15 |
| [puppet-yum](https://github.com/voxpupuli/puppet-yum) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [puppet-zypprepo](https://github.com/voxpupuli/puppet-zypprepo) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |
| [saz-puppet-limits](https://github.com/saz/puppet-limits) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [saz-puppet-sudo](https://github.com/saz/puppet-sudo) | 8.20.0 | ✅ | el9:✅ | unit+acceptance | 2026-07-15 |
| [saz-puppet-timezone](https://github.com/saz/puppet-timezone) | 8.20.0 | ✅ | el9-systemd:✅ | unit+acceptance | 2026-07-15 |
| [tragiccode-azure_key_vault](https://github.com/TraGicCode/tragiccode-azure_key_vault) | 8.20.0 | ✅ | N/A | unit-only | 2026-07-15 |

> ⛔ **blocked** / 🚧 **pending** modules have acceptance tests upstream that the harness did not run, so their compatibility is confirmed by unit tests only — not fully. The per-module reasons are documented in [docs/available-acceptance-tests.md](docs/available-acceptance-tests.md).
