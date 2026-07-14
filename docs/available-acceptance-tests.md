# Available Acceptance Tests

> Auto-generated from `config/modules.json` by `scripts/render_acceptance_audit.py`.
> Do not edit by hand — update the `acceptance` block in `config/modules.json` instead.

Audit of the acceptance-test disposition of every module in `config/modules.json`.

## Modules With Acceptance Tests (53)

Modules whose upstream repository contains acceptance tests. ✅ run in CI; ⛔ blocked (cannot run in this harness); 🚧 pending (not yet wired up).

| Status | Module |
|--------|--------|
| ✅ | [puppet-alternatives](https://github.com/voxpupuli/puppet-alternatives) |
| ✅ | [puppet-archive](https://github.com/voxpupuli/puppet-archive) |
| ✅ | [puppet-augeas](https://github.com/voxpupuli/puppet-augeas) |
| ⛔ | [puppet-augeasproviders_grub](https://github.com/voxpupuli/puppet-augeasproviders_grub) |
| ✅ | [puppet-augeasproviders_ssh](https://github.com/voxpupuli/puppet-augeasproviders_ssh) |
| ✅ | [puppet-augeasproviders_sysctl](https://github.com/voxpupuli/puppet-augeasproviders_sysctl) |
| ✅ | [puppet-autofs](https://github.com/voxpupuli/puppet-autofs) |
| ✅ | [puppet-ca_cert](https://github.com/voxpupuli/puppet-ca_cert) |
| ✅ | [puppet-chrony](https://github.com/voxpupuli/puppet-chrony) |
| ✅ | [puppet-confluence](https://github.com/voxpupuli/puppet-confluence) |
| ✅ | [puppet-corosync](https://github.com/voxpupuli/puppet-corosync) |
| ✅ | [puppet-cron](https://github.com/voxpupuli/puppet-cron) |
| ⛔ | [puppet-elastic_stack](https://github.com/voxpupuli/puppet-elastic_stack) |
| ⛔ | [puppet-elasticsearch](https://github.com/voxpupuli/puppet-elasticsearch) |
| ✅ | [puppet-epel](https://github.com/voxpupuli/puppet-epel) |
| ✅ | [puppet-firewalld](https://github.com/voxpupuli/puppet-firewalld) |
| ✅ | [puppet-gitlab](https://github.com/voxpupuli/puppet-gitlab) |
| ✅ | [puppet-gitlab_ci_runner](https://github.com/voxpupuli/puppet-gitlab_ci_runner) |
| ✅ | [puppet-grafana](https://github.com/voxpupuli/puppet-grafana) |
| ✅ | [puppet-hiera](https://github.com/voxpupuli/puppet-hiera) |
| 🚧 | [puppet-jira](https://github.com/voxpupuli/puppet-jira) |
| ✅ | [puppet-keepalived](https://github.com/voxpupuli/puppet-keepalived) |
| ✅ | [puppet-kibana](https://github.com/jst-cyr/puppet-kibana) |
| ✅ | [puppet-logrotate](https://github.com/voxpupuli/puppet-logrotate) |
| ✅ | [puppet-nfs](https://github.com/voxpupuli/puppet-nfs) |
| ✅ | [puppet-nftables](https://github.com/voxpupuli/puppet-nftables) |
| ✅ | [puppet-nginx](https://github.com/voxpupuli/puppet-nginx) |
| ✅ | [puppet-nodejs](https://github.com/voxpupuli/puppet-nodejs) |
| ✅ | [puppet-nsswitch](https://github.com/voxpupuli/puppet-nsswitch) |
| ⛔ | [puppet-openldap](https://github.com/voxpupuli/puppet-openldap) |
| ✅ | [puppet-openssl](https://github.com/voxpupuli/puppet-openssl) |
| ✅ | [puppet-php](https://github.com/voxpupuli/puppet-php) |
| ✅ | [puppet-posix_acl](https://github.com/voxpupuli/puppet-posix_acl) |
| ✅ | [puppet-postfix](https://github.com/voxpupuli/puppet-postfix) |
| ✅ | [puppet-prometheus](https://github.com/voxpupuli/puppet-prometheus) |
| ✅ | [puppet-python](https://github.com/voxpupuli/puppet-python) |
| ✅ | [puppet-r10k](https://github.com/voxpupuli/puppet-r10k) |
| ✅ | [puppet-redis](https://github.com/voxpupuli/puppet-redis) |
| ⛔ | [puppet-rsyslog](https://github.com/voxpupuli/puppet-rsyslog) |
| ⛔ | [puppet-selinux](https://github.com/voxpupuli/puppet-selinux) |
| ✅ | [puppet-squid](https://github.com/voxpupuli/puppet-squid) |
| ⛔ | [puppet-swap_file](https://github.com/voxpupuli/puppet-swap_file) |
| ⛔ | [puppet-systemd](https://github.com/voxpupuli/puppet-systemd) |
| ✅ | [puppet-telegraf](https://github.com/voxpupuli/puppet-telegraf) |
| ✅ | [puppet-unattended_upgrades](https://github.com/voxpupuli/puppet-unattended_upgrades) |
| ⛔ | [puppet-vault_lookup](https://github.com/voxpupuli/puppet-vault_lookup) |
| ⛔ | [puppet-wget](https://github.com/voxpupuli/puppet-wget) |
| 🚧 | [puppet-windows_env](https://github.com/voxpupuli/puppet-windows_env) |
| 🚧 | [puppet-windows_firewall](https://github.com/voxpupuli/puppet-windows_firewall) |
| 🚧 | [puppet-windowsfeature](https://github.com/voxpupuli/puppet-windowsfeature) |
| ✅ | [puppet-yum](https://github.com/voxpupuli/puppet-yum) |
| ✅ | [saz-puppet-limits](https://github.com/saz/puppet-limits) |
| ✅ | [saz-puppet-sudo](https://github.com/saz/puppet-sudo) |

## Modules Without Acceptance Tests (15)

Repos where no acceptance-test entrypoint exists upstream. Unit coverage alone is full coverage for these modules.

| Module |
|--------|
| [puppet-augeasproviders_core](https://github.com/voxpupuli/puppet-augeasproviders_core) |
| [puppet-augeasproviders_pam](https://github.com/voxpupuli/puppet-augeasproviders_pam) |
| [puppet-augeasproviders_shellvar](https://github.com/voxpupuli/puppet-augeasproviders_shellvar) |
| [puppet-boolean](https://github.com/voxpupuli/puppet-boolean) |
| [puppet-dnsquery](https://github.com/voxpupuli/puppet-dnsquery) |
| [puppet-extlib](https://github.com/voxpupuli/puppet-extlib) |
| [puppet-filemapper](https://github.com/voxpupuli/puppet-filemapper) |
| [puppet-format](https://github.com/voxpupuli/puppet-format) |
| [puppet-hdm](https://github.com/voxpupuli/puppet-hdm) |
| [puppet-kmod](https://github.com/voxpupuli/puppet-kmod) |
| [puppet-openvox_bootstrap](https://github.com/voxpupuli/puppet-openvox_bootstrap) |
| [puppet-prometheus_reporter](https://github.com/voxpupuli/puppet-prometheus_reporter) |
| [puppet-sssd](https://github.com/voxpupuli/puppet-sssd) |
| [puppet-zypprepo](https://github.com/voxpupuli/puppet-zypprepo) |
| [tragiccode-azure_key_vault](https://github.com/TraGicCode/tragiccode-azure_key_vault) |

## Modules With Acceptance Tests but Not Run in CI (14)

These modules have acceptance tests upstream, but the harness does not run them — so their compatibility is confirmed by unit tests only, not fully. They are intentionally excluded from `KNOWN_COMPATIBLE.md`.

| Module | Status | Reason |
|--------|--------|--------|
| [puppet-augeasproviders_grub](https://github.com/voxpupuli/puppet-augeasproviders_grub) | ⛔ blocked | GRUB providers are confined to specific hardware/boot scenarios; acceptance tests require reboot semantics and filesystem access incompatible with containerized environments. Module scope fundamentally conflicts with Docker/container-based testing. |
| [puppet-elastic_stack](https://github.com/voxpupuli/puppet-elastic_stack) | ⛔ blocked | Same fundamental blockers as puppet-elasticsearch — orchestrates the Elasticsearch stack and its acceptance tests share the same vm.max_map_count kernel requirement, systemd dependency, and artifacts.elastic.co download pattern. Requires a real VM or privileged container. |
| [puppet-elasticsearch](https://github.com/voxpupuli/puppet-elasticsearch) | ⛔ blocked | Production-mode bootstrap enforces vm.max_map_count >= 262144 (a host kernel parameter) which cannot be set from inside an unprivileged Docker container; all acceptance specs hit a live Elasticsearch HTTP API and fail. Tests also require systemd (unavailable in standard containers), download from artifacts.elastic.co, and need the simp-beaker-helpers gem. Requires a real VM or privileged container with host kernel tuning. |
| [puppet-jira](https://github.com/voxpupuli/puppet-jira) | 🚧 pending | Acceptance tests exist upstream but are not yet wired into a harness setfile/target. |
| [puppet-openldap](https://github.com/voxpupuli/puppet-openldap) | ⛔ blocked | Acceptance tests use Dir.mktmpdir on the Beaker controller to create temporary directories for LDAP database paths (olcDbDirectory), then reference those host-local paths inside the Docker SUT where they do not exist; slapd rejects them with "invalid path: Permission denied". The tests assume a shared controller/SUT filesystem (VM/Vagrant model). Requires VM-based Beaker or upstream test changes to create directories inside the SUT. |
| [puppet-rsyslog](https://github.com/voxpupuli/puppet-rsyslog) | ⛔ blocked | The module's cleanup_helper removes the rsyslog package between tests. In the harness's persistent Docker container model (PuppetCore pre-installed in the image), RPM database entries from the image build become corrupt, so rpm -e rsyslog fails with "package not installed" even though Puppet detects it as installed. This is a Docker copy-on-write filesystem artifact unique to the persistent container model. |
| [puppet-selinux](https://github.com/voxpupuli/puppet-selinux) | ⛔ blocked | SELinux acceptance tests require kernel-level SELinux LSM support. Docker containers share the host kernel, and GitHub Actions ubuntu-latest runners use AppArmor, so the SELinux LSM is never loaded. Tests fail at setup because /etc/selinux/config does not exist and getenforce/semodule/setenforce require active kernel SELinux enforcement. Requires a self-hosted runner on a SELinux-enforcing host or a VM-based approach. |
| [puppet-swap_file](https://github.com/voxpupuli/puppet-swap_file) | ⛔ blocked | Manages kernel-level swap file operations via swapon/swapoff. Docker containers restrict swap functionality at the cgroup/namespace level, preventing swap activation regardless of container configuration. Requires a full VM or bare-metal environment for acceptance testing. |
| [puppet-systemd](https://github.com/voxpupuli/puppet-systemd) | ⛔ blocked | Attempts to manage /etc/resolv.conf via symlink replacement to /run/systemd/resolve/resolv.conf. The Docker container runtime owns /etc/resolv.conf, preventing overlay filesystem manipulation and causing "Device or resource busy" errors. Requires non-Docker execution or upstream test changes. |
| [puppet-vault_lookup](https://github.com/voxpupuli/puppet-vault_lookup) | ⛔ blocked | Tests are purpose-built for Docker and self-contained, but use a three-container topology (certs.local, vault.local, puppetserver.local) that the single-SUT harness cannot orchestrate. The VaultDockerfile and PuppetserverDockerfile use multi-stage COPY --from=certs:latest builds the harness image-build pipeline does not support, and require a live Puppet Server (not puppet apply) with mTLS cert auth via a shared PKI. Requires harness-level support for multi-container nodesets and cross-image build dependencies. |
| [puppet-wget](https://github.com/voxpupuli/puppet-wget) | ⛔ blocked | Acceptance tests target only legacy OSes (Debian 8-9, Ubuntu 16.04-18.04, RHEL 6-7) — none of which match any available setfile — and hardcode `su - vagrant` to run puppet apply as a Vagrant user not present in Docker-based SUT containers. Requires new legacy setfiles or upstream test modernization. |
| [puppet-windows_env](https://github.com/voxpupuli/puppet-windows_env) | 🚧 pending | Acceptance tests target Windows; the harness runs Linux Docker SUTs only. Requires Windows runner support. |
| [puppet-windows_firewall](https://github.com/voxpupuli/puppet-windows_firewall) | 🚧 pending | Acceptance tests target Windows; the harness runs Linux Docker SUTs only. Requires Windows runner support. |
| [puppet-windowsfeature](https://github.com/voxpupuli/puppet-windowsfeature) | 🚧 pending | Acceptance tests target Windows; the harness runs Linux Docker SUTs only. Requires Windows runner support. |
