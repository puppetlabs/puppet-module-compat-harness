# Module Compatibility Status

> Auto-generated from `status/ledger.json` by `scripts/render_status_dashboard.py`.
> Do not edit by hand — changes will be overwritten on the next run.

**Generated:** 2026-09-09 03:31 UTC  
**Staleness threshold:** 30 days

## Summary

| Metric | Count |
|---|---|
| Active modules | 74 |
| ⚠️ Deprecated (unmaintained upstream) | 1 |
| Retired (incompatible / deprecated) | 1 |

Per-major coverage is tracked independently — a Puppet 9 regression does not affect Puppet 8's numbers or vice versa (docs/puppet-core-9-dual-major-support.md §5).

### Puppet 8

**Puppet Core version(s) seen:** 8.21.0  

| Metric | Count |
|---|---|
| Unit-tested | 74 |
| &nbsp;&nbsp;• unit pass | 74 |
| &nbsp;&nbsp;• unit fail | 0 |
| Acceptance-enabled (running) | 45 |
| &nbsp;&nbsp;• acceptance run | 45 |
| &nbsp;&nbsp;• acceptance pass | 45 |
| &nbsp;&nbsp;• acceptance fail | 0 |
| ⛔ Acceptance blocked (tests exist, can't run here) | 9 |
| 🚧 Acceptance pending (tests exist, not yet wired) | 3 |
| No acceptance tests (N/A) | 17 |
| **Fully compatible** (unit pass + acceptance pass or N/A) | **62** |
| Never tested | 0 |
| Stale | 0 |

### Puppet 9

**Puppet Core version(s) seen:** 9.0.0  

| Metric | Count |
|---|---|
| Unit-tested | 74 |
| &nbsp;&nbsp;• unit pass | 63 |
| &nbsp;&nbsp;• unit fail | 11 |
| Acceptance-enabled (running) | 45 |
| &nbsp;&nbsp;• acceptance run | 43 |
| &nbsp;&nbsp;• acceptance pass | 36 |
| &nbsp;&nbsp;• acceptance fail | 7 |
| ⛔ Acceptance blocked (tests exist, can't run here) | 9 |
| 🚧 Acceptance pending (tests exist, not yet wired) | 3 |
| No acceptance tests (N/A) | 17 |
| **Fully compatible** (unit pass + acceptance pass or N/A) | **46** |
| Never tested | 0 |
| Stale | 0 |

## Active Modules

> Per major: `target:✅/❌` = ran, `N/A` = no acceptance tests exist upstream, `⛔ blocked` = tests exist but cannot run in this harness, `🚧 pending` = tests exist but not yet wired up, `⏳ awaiting run` = enabled but no result yet, `—` = not yet tested on that major. Only ✅/N/A count toward that major's **Fully compatible**.
>
> ⚠️ next to a module name marks it **deprecated / no longer maintained upstream** — independent of compatibility (a deprecated module can still be fully compatible).

| Module | 8: Unit | 8: Acceptance | 9: Unit | 9: Acceptance | Last Tested |
|---|---|---|---|---|---|
| [puppet-alternatives](https://github.com/voxpupuli/puppet-alternatives) | ✅ | el9:✅ | ✅ | el9:✅ | 2026-09-09 |
| [puppet-archive](https://github.com/voxpupuli/puppet-archive) | ✅ | el9:✅ | ✅ | el9:✅ | 2026-09-09 |
| [puppet-augeas](https://github.com/voxpupuli/puppet-augeas) | ✅ | el9:✅ | ✅ | el9:✅ | 2026-09-09 |
| [puppet-augeasproviders_core](https://github.com/voxpupuli/puppet-augeasproviders_core) | ✅ | N/A | ✅ | N/A | 2026-09-09 |
| [puppet-augeasproviders_grub](https://github.com/voxpupuli/puppet-augeasproviders_grub) | ✅ | ⛔ blocked | ✅ | ⛔ blocked | 2026-09-09 |
| [puppet-augeasproviders_pam](https://github.com/voxpupuli/puppet-augeasproviders_pam) | ✅ | N/A | ✅ | N/A | 2026-09-09 |
| [puppet-augeasproviders_shellvar](https://github.com/voxpupuli/puppet-augeasproviders_shellvar) | ✅ | N/A | ✅ | N/A | 2026-09-09 |
| [puppet-augeasproviders_ssh](https://github.com/voxpupuli/puppet-augeasproviders_ssh) | ✅ | el9:✅ | ✅ | el9:✅ | 2026-09-09 |
| [puppet-augeasproviders_sysctl](https://github.com/voxpupuli/puppet-augeasproviders_sysctl) | ✅ | el9:✅ | ✅ | el9:✅ | 2026-09-09 |
| [puppet-autofs](https://github.com/voxpupuli/puppet-autofs) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-boolean](https://github.com/voxpupuli/puppet-boolean) ⚠️ | ✅ | N/A | ❌ | N/A | 2026-09-09 |
| [puppet-ca_cert](https://github.com/voxpupuli/puppet-ca_cert) | ✅ | el9:✅ | ✅ | el9:✅ | 2026-09-09 |
| [puppet-chrony](https://github.com/voxpupuli/puppet-chrony) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-collectd](https://github.com/voxpupuli/puppet-collectd) | ✅ | debian12-systemd:✅ | ✅ | debian12-systemd:❌ | 2026-09-09 |
| [puppet-confluence](https://github.com/voxpupuli/puppet-confluence) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-corosync](https://github.com/voxpupuli/puppet-corosync) | ✅ | debian12-systemd:✅ | ✅ | debian12-systemd:❌ | 2026-09-09 |
| [puppet-cron](https://github.com/voxpupuli/puppet-cron) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-dnsquery](https://github.com/voxpupuli/puppet-dnsquery) | ✅ | N/A | ✅ | N/A | 2026-09-09 |
| [puppet-elastic_stack](https://github.com/voxpupuli/puppet-elastic_stack) | ✅ | el9-gcp:✅ | ✅ | ⏳ awaiting run | 2026-09-09 |
| [puppet-elasticsearch](https://github.com/voxpupuli/puppet-elasticsearch) | ✅ | ⛔ blocked | ✅ | ⛔ blocked | 2026-09-09 |
| [puppet-epel](https://github.com/voxpupuli/puppet-epel) | ✅ | el9:✅ | ✅ | el9:✅ | 2026-09-09 |
| [puppet-extlib](https://github.com/voxpupuli/puppet-extlib) | ✅ | N/A | ❌ | N/A | 2026-09-09 |
| [puppet-filemapper](https://github.com/voxpupuli/puppet-filemapper) | ✅ | N/A | ✅ | N/A | 2026-09-09 |
| [puppet-firewalld](https://github.com/voxpupuli/puppet-firewalld) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-format](https://github.com/voxpupuli/puppet-format) | ✅ | N/A | ✅ | N/A | 2026-09-09 |
| [puppet-gitlab](https://github.com/voxpupuli/puppet-gitlab) | ✅ | el9-systemd:✅ | ❌ | el9-systemd:✅ | 2026-09-09 |
| [puppet-gitlab_ci_runner](https://github.com/voxpupuli/puppet-gitlab_ci_runner) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-grafana](https://github.com/voxpupuli/puppet-grafana) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-hdm](https://github.com/voxpupuli/puppet-hdm) | ✅ | N/A | ✅ | N/A | 2026-09-09 |
| [puppet-hiera](https://github.com/voxpupuli/puppet-hiera) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:❌ | 2026-09-09 |
| [puppet-jira](https://github.com/voxpupuli/puppet-jira) | ✅ | 🚧 pending | ✅ | 🚧 pending | 2026-09-09 |
| [puppet-keepalived](https://github.com/voxpupuli/puppet-keepalived) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-kibana](https://github.com/jst-cyr/puppet-kibana) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-kmod](https://github.com/voxpupuli/puppet-kmod) | ✅ | N/A | ✅ | N/A | 2026-09-09 |
| [puppet-logrotate](https://github.com/voxpupuli/puppet-logrotate) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-nfs](https://github.com/voxpupuli/puppet-nfs) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-nftables](https://github.com/voxpupuli/puppet-nftables) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-nginx](https://github.com/voxpupuli/puppet-nginx) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-nodejs](https://github.com/voxpupuli/puppet-nodejs) | ✅ | el9:✅ | ✅ | el9:✅ | 2026-09-09 |
| [puppet-nsswitch](https://github.com/voxpupuli/puppet-nsswitch) | ✅ | el9:✅ | ✅ | el9:✅ | 2026-09-09 |
| [puppet-openldap](https://github.com/voxpupuli/puppet-openldap) | ✅ | ⛔ blocked | ✅ | ⛔ blocked | 2026-09-09 |
| [puppet-openssl](https://github.com/voxpupuli/puppet-openssl) | ✅ | el9:✅ | ✅ | el9:✅ | 2026-09-09 |
| [puppet-php](https://github.com/voxpupuli/puppet-php) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-posix_acl](https://github.com/voxpupuli/puppet-posix_acl) | ✅ | el9:✅ | ✅ | el9:✅ | 2026-09-09 |
| [puppet-postfix](https://github.com/voxpupuli/puppet-postfix) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-prometheus](https://github.com/voxpupuli/puppet-prometheus) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-prometheus_reporter](https://github.com/voxpupuli/puppet-prometheus_reporter) | ✅ | N/A | ✅ | N/A | 2026-09-09 |
| [puppet-python](https://github.com/voxpupuli/puppet-python) | ✅ | el9:✅ | ✅ | el9:✅ | 2026-09-09 |
| [puppet-r10k](https://github.com/voxpupuli/puppet-r10k) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-redis](https://github.com/voxpupuli/puppet-redis) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-rsyslog](https://github.com/voxpupuli/puppet-rsyslog) | ✅ | ⛔ blocked | ✅ | ⛔ blocked | 2026-09-09 |
| [puppet-selinux](https://github.com/voxpupuli/puppet-selinux) | ✅ | ⛔ blocked | ✅ | ⛔ blocked | 2026-09-09 |
| [puppet-snmp](https://github.com/voxpupuli/puppet-snmp) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-squid](https://github.com/voxpupuli/puppet-squid) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-sssd](https://github.com/voxpupuli/puppet-sssd) | ✅ | N/A | ✅ | N/A | 2026-09-09 |
| [puppet-swap_file](https://github.com/voxpupuli/puppet-swap_file) | ✅ | el9-gcp:✅ | ✅ | ⏳ awaiting run | 2026-09-09 |
| [puppet-systemd](https://github.com/voxpupuli/puppet-systemd) | ✅ | ⛔ blocked | ✅ | ⛔ blocked | 2026-09-09 |
| [puppet-telegraf](https://github.com/voxpupuli/puppet-telegraf) | ✅ | el9-systemd:✅ | ✅ | el9-systemd:✅ | 2026-09-09 |
| [puppet-unattended_upgrades](https://github.com/voxpupuli/puppet-unattended_upgrades) | ✅ | ubuntu24:✅ | ✅ | ubuntu24:✅ | 2026-09-09 |
| [puppet-vault_lookup](https://github.com/voxpupuli/puppet-vault_lookup) | ✅ | ⛔ blocked | ✅ | ⛔ blocked | 2026-09-09 |
| [puppet-wget](https://github.com/voxpupuli/puppet-wget) | ✅ | ⛔ blocked | ✅ | ⛔ blocked | 2026-09-09 |
| [puppet-windows_firewall](https://github.com/voxpupuli/puppet-windows_firewall) | ✅ | 🚧 pending | ✅ | 🚧 pending | 2026-09-09 |
| [puppet-windowsfeature](https://github.com/voxpupuli/puppet-windowsfeature) | ✅ | 🚧 pending | ✅ | 🚧 pending | 2026-09-09 |
| [puppet-yum](https://github.com/voxpupuli/puppet-yum) | ✅ | el9:✅ | ✅ | el9:✅ | 2026-09-09 |
| [puppet-zypprepo](https://github.com/voxpupuli/puppet-zypprepo) | ✅ | N/A | ✅ | N/A | 2026-09-09 |
| [saz-puppet-limits](https://github.com/saz/puppet-limits) | ✅ | el9:✅ | ❌ | el9:❌ | 2026-09-09 |
| [saz-puppet-memcached](https://github.com/jst-cyr/puppet-memcached) | ✅ | el9-systemd:✅ | ❌ | el9-systemd:❌ | 2026-09-09 |
| [saz-puppet-sudo](https://github.com/saz/puppet-sudo) | ✅ | el9:✅ | ❌ | el9:❌ | 2026-09-09 |
| [saz-puppet-timezone](https://github.com/saz/puppet-timezone) | ✅ | el9-systemd:✅ | ❌ | el9-systemd:❌ | 2026-09-09 |
| [smoeding-puppet-debconf](https://github.com/smoeding/puppet-debconf) | ✅ | N/A | ❌ | N/A | 2026-09-09 |
| [stschulte-puppet-oracle](https://github.com/stschulte/puppet-oracle) | ✅ | N/A | ❌ | N/A | 2026-09-09 |
| [suchpuppet-puppet-resolvconf](https://github.com/suchpuppet/puppet-resolvconf) | ✅ | N/A | ❌ | N/A | 2026-09-09 |
| [tragiccode-azure_key_vault](https://github.com/TraGicCode/tragiccode-azure_key_vault) | ✅ | N/A | ❌ | N/A | 2026-09-09 |
| [treydock-puppet-kdump](https://github.com/treydock/puppet-kdump) | ✅ | ⛔ blocked | ✅ | ⛔ blocked | 2026-09-09 |

> ⛔ **blocked** / 🚧 **pending** modules have acceptance tests upstream that the harness did not run, so their compatibility is confirmed by unit tests only — not fully. The per-module reasons are documented in [docs/available-acceptance-tests.md](docs/available-acceptance-tests.md).

## Retired / Removed

| Module | Disposition | Last Known Unit (8) | Last Tested |
|---|---|---|---|
| [puppet-openvox_bootstrap](https://github.com/voxpupuli/puppet-openvox_bootstrap) | incompatible | ✅ | 2026-07-18 |
