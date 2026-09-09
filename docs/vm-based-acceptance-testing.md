# Design: VM-Based Acceptance Testing (GCP Provision Service)

**Status:** Proposed — no implementation yet
**Author:** (harness maintainers, via planning discussion with Claude Code)
**Date:** 2026-09-04

**Builds on:** [`docs/lean-testing-and-status-ledger-design.md`](lean-testing-and-status-ledger-design.md)
(ledger, lean matrix, `KNOWN_COMPATIBLE.md` generation) and
[`docs/puppet-core-9-dual-major-support.md`](puppet-core-9-dual-major-support.md)
(per-major ledger nesting, twin caller workflows). This document adds a third
dimension — *where the SUT lives* — without changing either of those.

---

## 1. Motivation

The harness runs every acceptance suite against a Docker SUT. That is a hard
ceiling, and we are sitting on it: **11 of the 58 modules that ship acceptance
tests upstream are recorded as `blocked`**, and almost every one of those
blockers is a variation on the same theme — *a container is not a machine*.

Read the `acceptance.reason` strings in [`config/modules.json`](../config/modules.json)
and the pattern is unmistakable. Three of them say "Requires a real VM" in so
many words:

- `puppet-swap_file` — "Docker containers restrict swap functionality at the
  cgroup/namespace level… Requires a full VM or bare-metal environment."
- `puppet-elasticsearch` — "`vm.max_map_count >= 262144` (a host kernel
  parameter) which cannot be set from inside an unprivileged Docker container."
- `puppet-selinux` — "Docker containers share the host kernel, and GitHub Actions
  `ubuntu-latest` runners use AppArmor, so the SELinux LSM is never loaded."

Others are the same shape: `puppet-systemd` cannot replace `/etc/resolv.conf`
because the container runtime owns it; `treydock-puppet-kdump` and
`puppet-augeasproviders_grub` need to reboot into a differently-configured
kernel; `puppet-rsyslog` trips over RPM database state baked into the image.

This is not cosmetic. A `blocked` module is **deliberately excluded from
`KNOWN_COMPATIBLE.md`** — the whole point of the `blocked` status is to record
that the module's available tests were never exercised, so we must not claim
full confidence. The practical consequence is that the harness cannot make a
full-confidence Puppet Core compatibility statement about roughly a fifth of the
modules that actually have acceptance tests to run.

Puppet's DevX team already operates a GCP VM provisioning service, consumed by
`puppet_litmus` and `cat-github-actions`. This design adapts the harness to use
it as an **alternative provisioner behind the existing Beaker path**.

Unlike the dual-major work, this is largely *additive*. It breaks exactly one
baked-in assumption — that the SUT is a container — and that assumption turns
out to be concentrated in a single line:

```ruby
acceptance_env['BEAKER_HYPERVISOR'] = 'docker'   # adapters.rb:120
```

### Non-goals

- **Not Windows.** Investigated in depth and dropped as poor value — see
  [Appendix A](#appendix-a-why-windows-was-dropped) for the findings, so the
  question is not reopened from scratch.
- **Not a Litmus execution adapter.** The harness invokes `bundle exec rake
  beaker` and will continue to. The GCP service is *natively* a Litmus feature,
  but §3 shows we can consume it without adopting Litmus as a test runner. Only
  one module in the fleet is Litmus-based (`puppet-windows_env`), and it is
  out of scope for other reasons.
- **Not cross-validation.** A module gets *either* a Docker target or a GCP
  target, never both. The VM path exists to close a coverage gap, not to
  re-verify modules that already pass in a container. See §6.1.
- **Not multi-node.** The single-SUT model is unchanged. This is what keeps
  `puppet-vault_lookup` blocked regardless (§7).
- **Not a change to the ledger schema.** §5 shows why none is needed.
- **Not local/developer provisioning.** The service authorizes by GitHub
  workflow-run URL (§2.1), so this works in CI only. Local acceptance testing
  stays Docker-only.

---

## 2. What the investigation established

Everything in this section was verified against primary sources — upstream code,
not documentation. These findings are what make the design cheap, so they are
recorded with enough specificity to be re-checked.

### 2.1 No credentials are required, and this repo already qualifies

This was the largest open risk at the start of planning, and it is closed.

The provision service takes **no client-side authentication whatsoever**.
[`puppetlabs/provision`'s `tasks/provision_service.rb`](https://github.com/puppetlabs/provision/blob/main/tasks/provision_service.rb)
sends an unauthenticated `POST` to a publicly-invokable Cloud Run facade, with
headers limited to `Accept` and `Content-Type`:

```
POST https://facade-release-6f3kfepqcq-ew.a.run.app/v1/provision

{"url":"https://api.github.com/repos/<owner>/<repo>/actions/runs/<run_id>",
 "VMs":[{"cloud":null,"region":null,"zone":null,"images":["rocky-linux-cloud/rocky-linux-9"]}]}
```

Authorization happens entirely server-side. The backend fetches that workflow
run using its *own* GitHub token and applies two checks:

```ruby
# Validator.check_status
raise StandardError, msg unless github_info[:repo] =~ %r{puppetlabs/\S+}
return expected_status.include?(github_info[:status])   # queued | in_progress

# Validator.valid_event?
github_info[:event] == 'pull_request' || github_info[:owner] == 'puppetlabs'
```

This repo is `puppetlabs/puppet-module-compat-harness`, so it satisfies the
owner clause — which matters, because it means `schedule` and
`workflow_dispatch` events qualify, not just pull requests.

**Nothing needs to be requested from DevX to make this work.** No
`id-token: write`, no Workload Identity Federation, no service-account key, no
new GitHub secret, no org allowlisting. `cat-github-actions`'
`module_acceptance.yml` confirms this from the consumer side: its only
`permissions` block is `contents: read`, and it contains no GCP auth step of any
kind.

> A courtesy heads-up to DevX that the harness will begin consuming the service
> is still warranted — see §8, spike 6, on shared-project capacity. It is a
> conversation, not a blocker.

Teardown is `DELETE /v1/provision` with `{"uuid": "<uuid>"}`, where the uuid
comes from the provisioned host's facts.

### 2.2 The response is a ready-made host description

The service returns a complete Bolt inventory document as the HTTP response
body. The parts the harness needs:

```yaml
groups:
  - name: ssh_nodes
    targets:
      - uri: <public ip>
        config:
          transport: ssh
          ssh:
            user: litmus<rand>
            password: L1tmus<rand>
            port: 22
            run-as: root
            host-key-check: false
        facts:
          provisioner: provision_service
          platform: <image>
          uuid: <teardown handle>
```

Credentials are randomized per request and ephemeral. **No key material is
returned** — password auth only, and the user is non-root with `run-as: root`
(a Bolt concept Beaker does not share). §2.4 explains why that is fine.

### 2.3 Beaker natively supports pre-provisioned hosts

`Beaker::Hypervisor.create` maps both `none` and `default` to the base
`Beaker::Hypervisor` class, whose `provision` and `cleanup` are no-ops and whose
SSH connection preference is `[:ip, :vmhostname, :hostname]`:

```ruby
hyper_class = case type
              when /^noop$/            then Beaker::Noop
              when /^(default)|(none)$/ then Beaker::Hypervisor
              else
                require "beaker/hypervisor/#{type}"
                ...
```

So a setfile carrying `hypervisor: none` and a real `ip` simply works. **No new
Beaker gem is needed** — no `beaker-google`, no `beaker-abs`.

`voxpupuli-acceptance` only *defaults* the hypervisor
(`ENV['BEAKER_HYPERVISOR'] ||= 'docker'`), and the per-host `hypervisor:` key in
the setfile is what actually governs. Since the harness already writes and
passes an absolute setfile path, this is a pure data change.

### 2.4 The VM arrives sudo-capable and can be made to look exactly like today's SUT

Every Linux bootstrap template in the service
(`default/rhel/centos/debian/ubuntu.sh.erb`) performs the same setup:

```bash
sudo useradd -m "<user>"; sudo echo "<user>:<password>" | chpasswd
sudo echo '<user>  ALL=(ALL:ALL) NOPASSWD: ALL' >> /etc/sudoers
sudo sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config
sudo service sshd restart
# ... plus /opt/puppetlabs/bin appended to the sudoers secure_path
```

`NOPASSWD: ALL` is the key detail. It means a preparation stage can SSH in as
the litmus user, install an **ephemeral harness-generated root keypair**, enable
`PermitRootLogin`, and hand Beaker `user: root`.

That is precisely the environment
[`docker.rb:177-196`](../lib/module_tester/docker.rb#L177-L196) already
constructs for containers (`PermitRootLogin yes`, `PasswordAuthentication yes`,
`root:root`). **Module tests therefore see an identical SUT and need no
changes** — which is the single most important property of this design.

Using a generated keypair rather than the service's returned password also keeps
that shared password out of the untrusted test stage.

### 2.5 The agent-install logic already exists and is reusable

[`Docker#puppet_core_dockerfile`](../lib/module_tester/docker.rb#L113-L173)
already encodes exactly the right Puppet Core install for both the EL and Debian
families: fetch the `puppet<N>-release-*` package from `yum-puppetcore` /
`apt-puppetcore`, inject `username=forge-key` and `password=$KEY`, install
`puppet-agent`, then delete the credential file **in the same layer**.

Those are ordinary shell commands that happen to be emitted as Dockerfile `RUN`
lines. Extracting them into a shared generator that can emit either `RUN` lines
or a script to execute over SSH is the single largest piece of reuse available,
and it means the VM path inherits the credential-scrubbing discipline for free
rather than reimplementing it.

---

## 3. Architecture

The VM path is a **second provisioner behind the existing acceptance stage**,
not a second pipeline. The two-stage isolation model is preserved exactly; only
the substrate changes.

| | Docker path (today) | VM path (new) |
|---|---|---|
| Stage 1 — holds the API key | `docker build` with a BuildKit secret mount | SSH to the VM, run the install script |
| Credential scrubbing | `rm` the repo/auth file in the same `RUN` layer | `rm` the repo/auth file in the same script |
| Setfile | local image tag, `hypervisor: docker` | public IP + root key, `hypervisor: none` |
| `BEAKER_PUPPET_COLLECTION` | `preinstalled` | `preinstalled` |
| Stage 2 — untrusted code | `rake beaker`, secrets stripped | `rake beaker`, secrets stripped |
| Cleanup | container removed by `beaker-docker` | `DELETE /v1/provision`, from an `ensure` |

### 3.1 Stage sequence

These stages are inserted into
[`Adapters#run_acceptance`](../lib/module_tester/adapters.rb#L107), branching at
line 120 where `BEAKER_HYPERVISOR` is currently hardcoded:

| # | Stage | Notes |
|---|---|---|
| 1 | `provision_vm` | POST to the facade; parse the inventory; record the teardown `uuid`. Needs an explicit timeout — `StageRunner`'s 1800s default is not obviously enough for a cold VM boot plus the service's own Terraform apply |
| 2 | `prepare_vm` | SSH as the litmus user; generate and install an ephemeral root keypair; enable `PermitRootLogin`; restart sshd |
| 3 | `install_puppet_core_vm` | Run the shared agent-install script as root **with the API key**; scrub credential files. This is the last stage that sees the key |
| 4 | `write_vm_setfile` | Emit `hypervisor: none`, `ip`, `user: root`, ephemeral key path |
| 5 | *(existing)* | `Docker.strip_secrets_from_env!` — unchanged |
| 6 | `acceptance` | `bundle exec rake beaker` — unchanged |
| 7 | `teardown_vm` | `DELETE /v1/provision`, in an `ensure` block so it runs on every failure path |

### 3.2 VM targets need no static setfile

Everything in a Docker setfile that the harness actually consumes — `image`,
`docker_cmd`, `docker_image_commands` — is Docker-specific. The only field
Beaker genuinely needs for a VM is `platform`, which drives its package-manager
and service handling, and that is derivable from the GCP image name.

So `config/beaker/setfiles/` gains nothing from the VM path, and `setfile`
becomes optional when `provisioner: gcp`. The mapping is small and mechanical
and belongs as a constant beside the provisioner, not as YAML files:

| GCP image | Beaker `platform` |
|---|---|
| `rocky-linux-cloud/rocky-linux-9`, `rhel-9`, `centos-stream-9`, `almalinux-cloud/almalinux-9` | `el-9-x86_64` |
| `rocky-linux-cloud/rocky-linux-8`, `rhel-8`, `centos-stream-8` | `el-8-x86_64` |
| `rhel-10` | `el-10-x86_64` |
| `debian-12` | `debian-12-x86_64` |
| `ubuntu-2404-lts` | `ubuntu-24.04-x86_64` |

The generated setfile is a new artifact shape, so
[`Docker#write_clean_setfile`](../lib/module_tester/docker.rb#L69) is *not*
reused. The `acceptance_env` diagnostic stage that dumps the effective setfile
into the report ([adapters.rb:160-175](../lib/module_tester/adapters.rb#L160-L175))
**should** be reused — but it must not dump the private key, only the path.

### 3.3 Alternative considered and rejected: consuming `puppet_litmus`

The obvious route is the documented one: add `puppet_litmus`, run
`bundle exec rake 'litmus:provision[provision_service,<image>]'`, and translate
the generated `spec/fixtures/litmus_inventory.yaml` into a Beaker setfile.

**Rejected.** The harness `Gemfile` currently contains exactly one gem (`json`).
Litmus's provisioning path is a Bolt task executed via `BoltSpec::Run` against
`localhost`, which means adopting it drags in Bolt and a large transitive
dependency tree, plus a `spec/fixtures/modules` fixture layout and a
`rake spec_prep` step — all to perform two HTTP calls. It would also blur the
"Beaker only, no Litmus" boundary that keeps the runner comprehensible.

**Chosen instead:** implement the `POST`/`DELETE` directly. The contract is two
verbs and one YAML shape, and it is fully visible in upstream's *public* task
source, so this is re-implementing a published interface rather than reverse
engineering a private one.

Cost of the decision, stated plainly: we track an upstream contract by hand and
will not automatically inherit changes to it. Mitigations — the contract is
tiny, spike 3 (§8) pins it against the live service, and vendoring upstream's
task remains available as a fallback if it proves unstable.

### 3.4 Alternative considered and rejected: a `beaker-google` hypervisor

Letting Beaker provision GCP instances directly would remove the provisioning
stages entirely. **Rejected** because no such gem exists in the Vox Pupuli
Beaker ecosystem, and writing one would mean the harness holding real GCP
credentials — which §6 shows we currently avoid completely. The provision
service's value is precisely that it brokers GCP access so we never hold a
credential.

---

## 4. CI topology — a separate `test_acceptance_vm` job

Both [`compatibility-runner-puppet8.yml`](../.github/workflows/compatibility-runner-puppet8.yml)
and [`compatibility-runner-puppet9.yml`](../.github/workflows/compatibility-runner-puppet9.yml)
must change **identically**; `AGENTS.md:41` treats any other diff as drift.

**Decision: VM targets get their own matrix job, permanently, rather than
riding the existing `test_acceptance` job.** This is not a bootstrapping
measure to be folded back in once the feature stabilizes — the two structural
reasons below hold for as long as VM targets exist in the matrix at all. It is
a CI-topology choice only and does not affect §5 — VM results still report
`lane: acceptance`, so the ledger is untouched.

Two structural reasons, plus two conveniences:

1. **Timeout ceiling (structural, permanent).** GitHub Actions'
   `timeout-minutes` is set per *job*, not per matrix entry. Docker targets can
   safely run for up to `PUPPET_JOB_TIMEOUT_MINUTES` (currently 360). VM targets
   must stay well inside the provision service's hard 3-hour VM TTL — budget
   around 170 minutes, matching `cat-github-actions`' `timeout-minutes: 180` for
   the same reason. As long as both target types exist, they cannot share one
   job's timeout without either risking VM jobs running past their TTL or
   needlessly capping Docker jobs at a fraction of their safe budget.
2. **Concurrency pacing (structural, permanent) — this caps how many VMs
   provision at once, not how many modules get re-verified.**
   [`detect_changes.py`](../scripts/detect_changes.py) sets `run_all` whenever
   anything under `lib`, `bin`, `scripts`, `profiles`, `Gemfile` or
   `.github/actions` changes — and that is *correct behaviour we want to keep*:
   a harness code change must re-verify every module, VM-tested ones included,
   or a regression in the VM path could ship undetected. This will keep
   happening for the life of the harness on any future refactor or bug fix, not
   just during this feature's initial implementation, and none of it should be
   skipped.

   What differs between the two target types is what kind of capacity a
   simultaneous fan-out consumes. A Docker job builds its container entirely
   inside its own GitHub-hosted runner, so 20 of them firing at once cost
   nothing beyond GitHub's own per-account concurrent-job ceiling, which GitHub
   already manages. A VM provision request instead hits one external, shared
   GCP project (`ia-content`) that DevX also uses for every other Puppet
   module's CI — not just ours — and the service enforces **no
   application-level quota of its own** (verified in its backend source). With
   `fail-fast: false`, a `run_all` event would otherwise fire a provision
   request for every enabled VM target across both majors in the same few
   seconds — a real number once Phase 2+ modules are enabled (§7), not a
   hypothetical one.

   A separate job is what lets `strategy.max-parallel` cap *how many of those
   requests are in flight at once*, independently of the Docker matrix. Every
   module still gets tested on every `run_all` event — a capped fan-out just
   spreads the same total work across more waves instead of one simultaneous
   burst, trading a longer wall-clock for that one CI run against not being the
   noisy neighbor on infrastructure the harness doesn't own. The actual cap is
   spike 6 (§7.2) — a number to set with DevX, not to guess here.

   **Update, spike 6 closed 2026-09-08:** DevX confirmed the harness's
   expected load is well within existing capacity. That does not relax this
   section — their explicit guidance alongside that confirmation was to keep
   load as minimal as possible regardless (VMs cost the company money) and to
   prefer Docker over GCP VMs wherever both can do the job. `max-parallel`
   stays; pick a concrete value as part of Phase 1 implementation rather than
   deferring it further, since "capacity isn't the constraint" removes the
   only reason that number was still open.
3. *(convenience)* The "Seed Beaker host mappings" step is skipped cleanly
   rather than conditionally. It parses `HOSTS.*.ip` expecting `127.0.0.1` and
   appends to `/etc/hosts`; Beaker reaches a VM by `ip` directly, so it is
   unnecessary. This alone could be handled with an `if:` inside a shared job —
   it is not what forces the split.
4. *(convenience)* Distinct job naming in the Checks UI.

**Sequencing: parallel, not gated.** `test_acceptance_vm` runs as a third
sibling — `needs: prepare`, feeding into `publish` alongside the other two —
exactly like `test_unit` and `test_acceptance` already run concurrently with
each other today. It is **not** gated behind `test_acceptance` succeeding
first.

This was weighed against gating VM tests on Docker acceptance passing, which
has a real argument in its favor: the shared install-logic generator (§2.5,
§3) means a single code regression could break both paths at once, and Docker
jobs fail fast and cheaply, so gating would avoid spending real GCP VM time on
runs already known to be broken. Rejected in favor of parallel because (a) it
matches the existing `test_unit`/`test_acceptance` precedent, which accepts the
same class of shared-regression risk today without gating one behind the
other, and (b) gating adds real wall-clock cost — VM tests would not start
until the *entire* Docker acceptance matrix finished, which can be lengthy on a
full `run_all`. If shared-regression waste on VM quota proves to be a real
problem in practice, revisit this — a narrow smoke-test gate (one fast Docker
target, both matrices depend on it) is the middle option to reach for rather
than gating on the full Docker matrix.

Supporting changes:

- **No `permissions` change** (§2.1). The workflow-level `contents: read` stands.
- [`scripts/build_matrix.rb`](../scripts/build_matrix.rb) — emit a third matrix
  (`vm_acceptance`) carrying `provisioner` and `image`, plus a
  `has_vm_acceptance` output. An empty matrix vector is a hard Actions error, so
  it needs the same `if:` gate as the existing two.
- [`prepare-test-matrix/action.yml`](../.github/actions/prepare-test-matrix/action.yml) —
  new output passthrough.
- [`run-module-test/action.yml`](../.github/actions/run-module-test/action.yml) —
  new inputs threaded through to the runner CLI.
- [`publish-compatibility-results/action.yml`](../.github/actions/publish-compatibility-results/action.yml) —
  the `publish` job must `needs:` the new job, or VM results are silently
  dropped from the ledger.

---

## 5. Ledger and dashboard — no schema change needed

**Decision: a VM run is just another acceptance *target name* (e.g. `el9-gcp`),
not a new lane.**

This is the cheapest slot-in available, and it is cheap because the existing
schema is already open at exactly the right place.
[`update_ledger.py`](../scripts/update_ledger.py) stores acceptance results as
an open `name → class` map and rolls them up by severity:

```python
acceptance = major_entry.setdefault('acceptance', {})
targets = acceptance.setdefault('targets', {})
target_name = row.get('acceptance_target') or 'default'
targets[target_name] = row.get('class', 'failure')
...
major_entry['acceptance']['class'] = worst_class(targets.values())
```

`acceptance_target` is a free-form string threaded from the `ACCEPTANCE_TARGET`
env var through [`classify_module_result.py`](../scripts/classify_module_result.py).
So a target named `el9-gcp` requires **zero** ledger schema change, **zero**
dashboard change, and `render_status_dashboard.py` renders it for free as
`el9-gcp:✅` alongside any Docker targets.

`is_fully_compatible()` keeps working unchanged: a module whose `acceptance.status`
is `running` needs its acceptance targets to pass, and it does not care where
they ran.

### Alternative considered and rejected: a `vm_acceptance` lane

Tracking VM runs as a distinct lane beside `unit` and `acceptance` would make
"container-verified" and "VM-verified" separately visible. **Rejected** — it
would touch `update_ledger.py` (new lane branch, new coverage states),
`render_status_dashboard.py` (new column pair per major, new summary counters),
`detect_changes.py` (new not-green state) and the ledger schema, for no
behavioural gain. Note the existing lane branch is `if row.get('lane') ==
'unit' ... else`, so an unrecognised lane would silently land in the acceptance
bucket anyway — the "cheap" option is also the one the code already expects.

**One thing to verify rather than assume:** that a failing VM target yields
`coverage_state: acceptance-failing`, which is already in
`detect_changes.py`'s `NOT_GREEN_STATES`. If it does, lean runs retry failed VM
targets automatically. If it does not, VM failures would go stale silently.

---

## 6. Security model

The Puppet Core API key is handled exactly as it is today: present only during
stages 1–3, scrubbed from the VM by the same script that uses it, and removed
from the environment before any module-authored code executes.

What is genuinely new is that **Beaker must retain SSH credentials for the VM
during the test stage** — it cannot drive the SUT otherwise. The current
`strip_secrets_from_env!` discipline therefore cannot be absolute for the VM
path. The design constrains this rather than waiving it:

- The root key is **generated per run** by the harness and never reused.
- The service's returned litmus password is used only in `prepare_vm` and does
  not reach stage 2.
- **No GCP service-account credential exists anywhere in the harness** (§2.1),
  so there is no broader cloud credential available to leak.
- Untrusted test code already has root on the VM by design, so possessing the
  SSH key grants it nothing it did not already have.
- The service scopes each VM's firewall to the requesting runner's public IP
  (`source_ranges = "<source_ip>/32"` plus two internal subnets).
- `strip_secrets_from_env!` ([docker.rb:99](../lib/module_tester/docker.rb#L99))
  must still be extended with any new credential-bearing env keys the VM path
  introduces.

**Residual risk, accepted explicitly:** the VM is a real machine with outbound
internet access running untrusted third-party test code. Containment rests on
the service's isolation model — a fresh VM per run, no persistence between runs,
its own network segment with no access to internal systems — plus the hard
3-hour TTL. This is the same posture `cat-github-actions` operates under today
for every puppetlabs module, so we are not inventing a new risk profile.

### 6.1 A module gets one provisioner, not both

A module carries *either* a Docker target or a GCP target. The schema should
reject mixed-provisioner target lists so this is enforced rather than merely
conventional — and so that a later decision to allow cross-validation is a
deliberate, visible change rather than a drift.

The rationale is capacity and clarity: the VM path exists to close a coverage
gap, and re-running already-green modules on VMs would multiply load on a shared
project for a marginal signal.

**This is now DevX's stated preference too, not just an internal one.**
Confirmed directly by Lukas (2026-09-08, closing spike 6 — §7.2): the
service's capacity is well within what the harness needs, but the explicit
guidance was still to keep the harness's load on it as minimal as possible
and to prefer Docker over GCP VMs wherever both can do the job, since VMs cost
the company money regardless of spare capacity. That is exactly what this
section already enforces, plus the lean-matrix behavior in §4 (change
detection only re-runs what needs it) and the phasing in §7 (VM-viable
modules are triaged in, not swept in wholesale). No design change follows
from this — it is confirmation that the constraint was the right one to build
in from the start, not something bolted on after the fact.

---

## 7. Target set and phasing

### 7.1 Two facts from module triage that reframe the target set

Before the per-module table, two things surfaced while triaging the blocked
list against upstream test code that change how several verdicts should be
read:

1. **Upstream Vox Pupuli CI does not test against Docker.** `gha-puppet`'s
   `beaker.yml@v4` defaults to `beaker_hypervisor: container_podman` — rootless
   Podman with systemd, not Docker. Several modules recorded here as "blocked,
   requires a VM" are already green upstream today, in a container. That means
   some of this fleet's recorded blockers are artifacts of *this harness's
   specific Docker model* (its persistent pre-baked image, its non-systemd
   default), not of containers-versus-VMs as a category. Where that is the
   case it is called out below, because it means the honest fix may not need a
   VM at all.
2. **`voxpupuli-acceptance` already treats `preinstalled` + no-hypervisor as a
   first-class path.** `configure_beaker`
   (`lib/voxpupuli/acceptance/spec_helper_acceptance.rb`) only *defaults*
   `BEAKER_HYPERVISOR` and skips its own install logic entirely when
   `collection == 'preinstalled'`. Ten of the eleven blocked modules use this
   helper unmodified, so `BEAKER_PUPPET_COLLECTION=preinstalled` +
   `hypervisor: none` is a supported combination for all of them except
   `kdump`, which does not use `voxpupuli-acceptance` at all (§7.5).

### 7.2 Phase 0 — spikes

Run these before writing runner code. Spike 3 is gating.

| # | Question | Why it matters |
|---|---|---|
| 1 | Puppet Core repo behaviour on a GCP RHEL/Rocky image | ✅ **Validated 2026-09-08.** See below |
| 2 | Do Beaker's `validate` / `configure` prebuilt steps behave against a `hypervisor: none` host? | ✅ **Validated 2026-09-08.** See below |
| 3 | **End-to-end provision → teardown against the live facade from a CI run on this repo** | ✅ **Validated 2026-09-08.** See below |
| 4 | Teardown reliability across failure modes | ✅ **Closed 2026-09-08 — DevX confirmed reaping is fine for this usage.** The technical breakdown in §9 (reaper vs. 3h TTL, which covers which failure mode) stands as documented; DevX's confirmation addresses the residual "did the 504 orphan a VM" concern operationally rather than by giving us a technical guarantee we could verify ourselves — reasonable to close on that basis given the 3h TTL is the true backstop regardless |
| 5 | Wall-clock cost of provision + agent install | ✅ **Measured 2026-09-08.** See spike 1 below — full provision-to-Puppet-Core-installed is ~90s–2min |
| 6 | Agree a concurrency ceiling with DevX | ✅ **Closed 2026-09-08.** DevX (Lukas) confirmed they handle substantially more load than the harness will add, and expect no capacity issue. **This is not a license to be unbounded** — DevX's own framing was to keep harness load as minimal as possible regardless, since VMs cost the company money, and to prefer Docker over GCP VMs wherever both can do the job. See the resulting design update below and in §6.1/§4 |
| 7 | Ask DevX the reaper's actual polling interval | ✅ **Closed 2026-09-08** — folded into spike 4's resolution above; DevX confirmed reaping behavior is fine for this usage. The exact interval remains unknown but is no longer being treated as a blocking question |

#### Spike 3 result

Run against the live facade from a `pull_request`-triggered job on this repo
(no `workflow_dispatch` registration needed — see the throwaway workflow's own
comments for why): [run 34230684096](https://github.com/puppetlabs/puppet-module-compat-harness/actions/runs/34230684096).

| Step | Result |
|---|---|
| Provision | `HTTP 200` in ~35s. Returned `ssh_nodes` target `34.187.171.44`, `platform: rocky-linux-cloud/rocky-linux-9`, `uuid: d46c5a4e-2af7-43b4-9f8c-a327345c6ba9` — inventory shape matches §2.2 exactly |
| SSH port check (15s probe, non-fatal by design) | Did not answer within the window — expected for a VM ~35s post-boot, not a signal of a problem |
| Explicit teardown | `DELETE /v1/provision {"uuid": ...}` → `HTTP 200` in ~43s |
| Total wall-clock | ~95 seconds, provision request to confirmed teardown |

**The owner-clause authorization works exactly as the source review predicted**
— no credentials, no `id-token`, no special permissions; a plain `POST` from a
PR-triggered job in `puppetlabs/puppet-module-compat-harness` was accepted.
This closes the single assumption the rest of the design depended on. The
throwaway workflow and its branch/PR (#21) have been deleted; nothing from the
spike is retained beyond this result and the run link.

#### Spike 2 result

Prototyped the full chain end to end: provision a VM, escalate to root via an
ephemeral SSH key (prototyping §2.4/§3.1's `prepare_vm` stage), scaffold a
minimal throwaway fixture module, run a real `bundle exec rake beaker` against
the VM with `BEAKER_PUPPET_COLLECTION=puppet8` (public, no credential), tear
down. Two attempts on the same branch/PR (#22, deleted after capturing
results):

**First attempt — [run 34239242919](https://github.com/puppetlabs/puppet-module-compat-harness/actions/runs/34239242919) — failed at the provisioning step itself:**

```
14:35:35 → request sent
14:40:35 → HTTP 504, body: "upstream request timeout"
```

Exactly 300 seconds — a Cloud Run gateway timeout, not a rejection. No `uuid`
was returned, so the harness had nothing to reference and could not attempt a
`DELETE`. **This is the first observed occurrence of spike 4's previously-
hypothetical "GCP-side failure partway through provisioning" scenario.**
Whether the backend's Terraform apply completed anyway after the facade gave
up on us is unknown and unknowable from the harness side — this is exactly
the gap §9 already describes, now with a concrete timestamp and run URL
attached rather than being purely theoretical.

**Second attempt (a plain re-run of the same job) — [run 34239242919, rerun](https://github.com/puppetlabs/puppet-module-compat-harness/actions/runs/34239242919/job/102125038365) — provisioning succeeded cleanly** (so the 504 was transient, at least in the sense that identical retried input worked shortly after), confirming:

| Check | Result |
|---|---|
| `Hypervisor for gcp-spike is none` / `found some none boxes to create` | Beaker correctly treats the pre-provisioned host as a no-op hypervisor — confirms §2.3 |
| SSH via the ephemeral key (`auth_methods=>["publickey"]`) | Root escalation from §2.4 works |
| Beaker's own prebuilt checks (`rpm -q iputils`, `rpm -q rootfiles`) and config edits (`PermitUserEnvironment`, sshd restart) | Ran cleanly; touched a *different* sshd directive than our own `PermitRootLogin` edit, and root SSH survived Beaker's own sshd restart — **no collision between Beaker's host-prep and the harness's own prep** |
| Public agent install (`puppet8-release` → `puppet-agent-8.10.0`) | Succeeded via plain `dnf` against the GCP Rocky 9 image — no repo/GPG friction |
| Module install + first `apply_manifest` (`catch_failures: true`) | Passed |
| Second `apply_manifest` (`catch_changes: true`, "is idempotent") | **Failed** — but see below, this is a spike-authoring bug, not a finding |

The idempotency failure was self-inflicted: the throwaway fixture used
`notify { 'hello from spike 2': }`, and `notify` resources report as changed
on *every* apply by design — the spec was doomed regardless of environment.
Fixed the fixture to use a genuinely idempotent `file` resource and re-ran
once more — [run 34251734058](https://github.com/puppetlabs/puppet-module-compat-harness/actions/runs/34251734058) —
**fully green**: provision (55s) → root escalation (40s) → scaffold → Ruby
setup → both acceptance specs passing → teardown (`HTTP 200`, ~2m13s).

**Net result:** spike 2's actual question — does Beaker's own validate/configure
fight a host the harness has already prepared — is answered **no**, with a
fully passing real Beaker run as evidence. The 504 from the first attempt is
retained above as evidence for spike 4/6, not as a spike-2 finding.

#### Spike 1 result

Adapted [`Docker#puppet_core_dockerfile`](../lib/module_tester/docker.rb#L113-L173)'s
exact EL-family install logic — private release RPM, `sed`-inject a
`forge-key` credential into the repo file, `dnf install`, scrub the repo
file — to run as a single SSH-piped script instead of a Dockerfile `RUN`
layer, using the real `PUPPET_CORE_API_KEY` secret. Fully green on the first
attempt — [run 34262921647](https://github.com/puppetlabs/puppet-module-compat-harness/actions/runs/34262921647/job/102185093864):

| Step | Result |
|---|---|
| Provision | `HTTP 200`, 37s |
| Root escalation | ~36s |
| Release RPM | `puppet8-release-10.5.0-3.el9` installed cleanly — **no `google-cloud.repo` friction**, the original concern behind this spike |
| Credential handling | `PUPPET_CORE_API_KEY: ***` — GitHub's log redaction confirmed working; the key was interpolated locally into the outgoing SSH stdin stream and never appeared as a literal CLI argument on either host (verified byte-for-byte with a fake key before running for real — see the workflow's own commit message) |
| Agent install | **`puppet-agent-8.21.0-1.el9.x86_64`** from the `puppet8` repo — an exact match to `profiles/puppet_profiles.json`'s `8-latest-maintained` pin, and materially different from spike 2's public-collection `8.10.0`. This is decisive: the private-repo path is genuinely being exercised, not silently falling back to public |
| Scrub verification | `SCRUB_OK` — the repo file with the embedded credential was confirmed deleted before the script exited |
| `puppet --version` | `8.21.0`, confirmed twice: once inside the credentialed SSH session, once more in a fresh follow-up session with no secret in scope |
| **Install step wall-clock** | **41 seconds** — release RPM + credential inject + full `puppet-agent` package pull/install + scrub |
| Teardown | `HTTP 200`, ~2m20s |

**Spike 5 falls out of this for free:** combined with provisioning (~35–55s
across all spikes so far) and root escalation (~35–40s), a VM goes from
nonexistent to Puppet-Core-installed-and-verified in roughly **90 seconds to
2 minutes**. Comfortably within a nightly cadence; no separate timing exercise
needed.

The inject-then-scrub credential pattern survives the move from a Docker
BuildKit secret mount to an SSH-piped script without modification — the
security property (`docker.rb`'s "never persists in a layer") maps directly
onto "never persists in a file after the script exits" for the VM case.

#### Phase 0 is complete

All seven spikes are closed as of 2026-09-08. Five were resolved by direct
testing against the live service (1, 2, 3, 5, and the technical half of 4);
the remaining two required DevX's own operational visibility rather than more
harness-side testing, and are now closed by direct confirmation from Lukas
(DevX): the harness's expected load is well within what the service already
handles day to day, and reaping/cleanup behavior is not a concern for this
usage pattern. Nothing here overturns the architecture in §2–§6 — it confirms
it. One explicit piece of guidance did come out of that conversation, though,
which sharpens (rather than changes) an existing decision — see the update to
§6.1 below, and the note added to §4.

### 7.3 Phase 1 — pilot: `puppet-swap_file` on `el-9`

One module, end to end, against the real service. Chosen because it isolates the
provisioning spine from every other variable:

- Its `spec/spec_helper_acceptance.rb` is the **canonical modulesync-managed
  idiom** — `require 'voxpupuli/acceptance/spec_helper_acceptance'` followed by
  `configure_beaker(modules: :metadata)`. That means it honours
  `BEAKER_PUPPET_COLLECTION=preinstalled` correctly, uses no legacy
  `beaker-puppet` DSL, hardcodes no hosts or credentials, and makes no
  controller/SUT shared-filesystem assumption. If the spine works anywhere, it
  works here.
- Eight acceptance spec files — meaningful coverage, not a smoke test.
- The blocker is unambiguous and purely kernel-level (`swapon`/`swapoff` blocked
  at the cgroup/namespace layer), so a real VM is a *definitive* fix rather than
  a hopeful one. Confirmed independently: upstream already runs this exact
  suite on real VMs (`beaker_hypervisor: vagrant_libvirt`) and it is green on
  AlmaLinux 8/9, Rocky 8/9, Debian 11/12 and Ubuntu 22.04.
- `metadata.json` supports RedHat/Rocky/AlmaLinux 8–9 → GCP
  `rocky-linux-cloud/rocky-linux-9`, Beaker platform `el-9-x86_64`.
- No external artifact downloads and no extra gems, unlike the Elasticsearch
  family.

**One required capability, found during triage, not before:**
`manifests/files.pp` sizes the swapfile from
`$facts['memory']['system']['total']` — on an unconstrained multi-GB GCP VM
that means creating a swapfile the size of the VM's full RAM, against a
`timeout => 300` in the module's own exec resource. The harness must export
`BEAKER_FACTER_memory.system.total="300 MiB"` (mechanism: `voxpupuli-acceptance`'s
`Facts.write_beaker_facts_on` writes `BEAKER_FACTER_*` env vars to
`/etc/facter/facts.d/` on the SUT before tests run) so the suite creates a
small, fast swapfile instead. Without this the pilot would still exercise the
provisioning spine, but would run unreasonably slowly or time out — so this is
part of "done," not an optional refinement.

**Phase 1 is done when** `puppet-swap_file` reports `unit+acceptance` in
`status/ledger.json` for Puppet 8, renders as `el9-gcp:✅` in `STATUS.md`, and
the VM is torn down (or, failing that, backstopped by the service's own
reaper + 3h TTL per §9 — a failed `teardown_vm` is never a blocker).

**Verified 2026-09-09** (run
[34296524333](https://github.com/puppetlabs/puppet-module-compat-harness/actions/runs/34296524333/job/102294296919)):
spine + fix confirmed end-to-end against the real service — 33 examples, 0
failures, `compatibility_state: compatible`. `read_fact_overrides` read the
VM's real memory (7.01 GiB) and `write_fact_overrides` wrote the corrected
override; the three previously-`ENOSPC`-failing resources
(`tmp file swap`, `tmp file swap 1`, `tmp file swap 2`) and the
fully-default example all created their swapfiles successfully. `teardown_vm`
itself failed on this run (`Connection reset by peer` — the same transient
error class hit `provision_vm` on the run immediately before it, suggesting a
brief facade-side blip that night rather than anything harness-side);
correctly did not affect classification, per the backstop design above. This
run used the `modules_json` workflow-dispatch override, which — as noted in
§7 Verification — skips ledger persistence by design, so `status/ledger.json`
and `STATUS.md` will pick up the real `el9-gcp:✅` row on the first nightly
run after this lands on `main`, not immediately at merge time.

*If the Facter-override plumbing proves awkward to land first,
`puppet-rsyslog` (§7.4) is an equally strong pilot candidate and needs no
harness capability beyond the provisioning spine itself — it was the
highest-confidence module in the entire triage. Swap_file remains the primary
choice because its blocker is the most legible "a VM fixes this" story to
validate the spine against.*

#### Phase 1 result: the `BEAKER_FACTER_memory.system.total` override was a silent no-op

The first live end-to-end run (Sept 2026) provisioned, escalated, installed
Puppet Core, and ran the real acceptance suite — but 8 of 33 examples failed
with `dd: error writing '/mnt/swapfile1': No space left on device`, at
`count=7178` (megabytes) — i.e. `swapfile::files` used the VM's **real**
~7 GB of memory, not the 300 MiB the harness set via `beaker_env`.

Root cause, confirmed against `voxpupuli-acceptance`'s own source
(`Facts.write_beaker_facts_on`) and against Facter's external-fact loader
(`LegacyFacter::Util::DirectoryLoader#add_data`): a `BEAKER_FACTER_<dotted.path>`
env var is written to `/etc/facter/facts.d/` as a **flat**, dotted-key JSON
value (`{"memory.system.total": "300 MiB"}`). Facter's external-fact loader
takes a JSON top-level key as a literal fact name — it does not split on
`.` — so this registers as an unrelated, unused fact literally named
`memory.system.total`, and never reaches the nested
`$facts['memory']['system']['total']` the module actually reads. This is not
a harness-specific mistake: `puppet-swap_file`'s own upstream CI
(`voxpupuli/gha-puppet`'s `beaker.yml`) passes the identical
`beaker_facter: 'memory.system.total:TotalMemory:300 MiB'` input, which
resolves through `puppet_metadata`'s `metadata2gha` to the exact same
`BEAKER_FACTER_memory.system.total` env var and the same (4.4.x)
`voxpupuli-acceptance` gem — so it is equally a no-op there. Upstream's own
CI is green anyway because its `vagrant_libvirt` VMs apparently have enough
disk headroom relative to their configured memory that the real,
un-overridden swapfile size still fits; the harness's default GCP boot disk
does not have that headroom once the OS and Puppet Core agent install are
accounted for (only ~2.4 GB was free at failure time).

**Fix:** `Vm#write_fact_overrides` (`lib/module_tester/vm.rb`), run as a new
optional stage after `install_puppet_core_vm`. For any `beaker_env` entry
shaped like `BEAKER_FACTER_<a.b.c>`, it reads the real value of the
top-level fact (`facter -j <a>`), deep-merges the override into it (so
sibling values like `memory.swap.*` survive rather than being blanked out
by the external fact's higher weight), and writes the merged, correctly
nested structure to a distinctly-named facts.d file
(`/etc/facter/facts.d/harness-fact-overrides.json`) — deliberately leaving
`voxpupuli-acceptance`'s own (flat, functionally inert) file alone rather
than trying to race or suppress it. Flat (non-dotted) `BEAKER_FACTER_*`
overrides are untouched and continue to work via the existing mechanism.
`config/modules.json`'s `beaker_env` declaration for `puppet-swap_file`
required no change — the fix is entirely harness-side.

### 7.4 Phase 2 — zero new harness capability beyond the spine

These four need nothing beyond `hypervisor: none` +
`BEAKER_PUPPET_COLLECTION=preinstalled` — no reboot support, no bundle-group
handling, no time-budget concerns. Land them together right after the pilot.

| Module | Verdict | GCP image | Note |
|---|---|---|---|
| `puppet-rsyslog` | **VM-FIXES — landed 2026-09-08** | Rocky 9 | The recorded reason (RPM DB corruption from the harness's persistent pre-baked-image model) is a self-diagnosed Docker artifact. A fresh VM has a coherent package database. Upstream is green on 11 podman platforms. Needs outbound network to `rpms.adiscon.com`; avoid Ubuntu initially (the upstream-repo assertion shells out through `python3-apt`) |
| `puppet-elastic_stack` | **VM-FIXES — landed 2026-09-08 — recorded reason was wrong** | Rocky 9 | Its actual acceptance suite is a single `elastic_stack::repo` idempotency test — it manages a yum/apt repo definition and nothing else. It has no Elasticsearch service and no `vm.max_map_count` dependency, despite the recorded reason claiming it shares elasticsearch's blockers. Enabled directly on a `gcp` target rather than re-testing in Docker first |
| `puppet-swap_file` (Phase 1) | see §7.3 | — | — |
| `puppet-openldap` | **VM-FIXES-WITH-CAVEAT — deferred, see below** | Rocky 9 / AlmaLinux 9, **SELinux set permissive** | The recorded reason says the tests assume a shared controller/SUT filesystem via `Dir.mktmpdir`. They do not — the tmpdir only supplies a unique path string interpolated into the manifest; the directory is created on the SUT by the module's own `file` resource (`manifests/server/database.pp`), and the harness's Docker `"invalid path: Permission denied"` is better explained by an LSM confining `slapd` (SELinux `slapd_db_t` on EL, AppArmor's `usr.sbin.slapd` profile on Debian). Upstream is green on 11 podman platforms, which likewise share no filesystem with the controller. A GCP EL image actually raises this risk rather than lowering it — GCP's RHEL/Rocky images boot SELinux enforcing by default — so provisioning must explicitly `setenforce 0` |

`rsyslog` and `elastic_stack` landed together as a first slice of Phase 2 —
truly zero new harness capability, a straight `gcp` target flip in
`config/modules.json`. The `reason` text above for `elastic_stack` was also
rewritten in its config entry per the note below, preserving the corrected
diagnosis even though the module is now enabled.

**`openldap` is deferred out of that slice.** Its `setenforce 0` requirement
does not fit either existing mechanism: `setup_commands` only runs during
the Docker image build (the schema forbids it for `provisioner: gcp`), and
`pre_acceptance_commands` runs on the GitHub Actions runner itself, not over
SSH on the VM. Landing it needs a small new capability — something in the
shape of a `vm_setup_commands` list, run over SSH as root right after
`install_puppet_core_vm` and before the fact-override/setfile stages, reusing
`Vm`'s existing SSH stage pattern and classified as a harness stage (like
`provision_vm`) in `classifier.rb`. That capability is not yet designed;
treat `openldap` as its own follow-up rather than assuming it rides along
with the next batch.

Rewrite the `reason` text for `elastic_stack` and `openldap` when their config
entries are edited (§3.1) — even though both are being enabled, the corrected
diagnosis is worth preserving in the module's history for the next person who
reads it.

### 7.5 Phase 3 — needs reboot support

Beaker exposes `host.reboot`; the harness must additionally tolerate the SSH
disconnect and reconnect on the same IP with a bounded timeout, and account for
it in the job's overall time budget. Implement this once, then land:

| Module | Verdict | GCP image | Note |
|---|---|---|---|
| `puppet-selinux` | **VM-FIXES-WITH-CAVEAT** | **Rocky 8 / AlmaLinux 8** (not 9) | Four reboots (`hosts.each(&:reboot)` across several contexts). On EL9+, `SELINUX=disabled` in `/etc/selinux/config` no longer disables the LSM at boot — the kernel still enforces, so `class_disabled_spec.rb`'s `getenforce` assertion will fail on EL9/10 specifically. Target EL8 for a fully green result; EL9 will show one legitimate spec failure unrelated to Puppet Core compatibility. No upstream acceptance CI exists for this module, so the suite itself is unvalidated territory |
| `treydock-puppet-kdump` | **VM-FIXES-WITH-CAVEAT — larger lift than it first appears** | Rocky 8 / AlmaLinux 8 | Two reboots plus a fixed `sleep 60`, asserting `crashkernel` on `/proc/cmdline` — a VM is the only way to satisfy this. But this module does not use `voxpupuli-acceptance` at all: its `spec_helper_acceptance.rb` calls `run_puppet_install_helper` (from `beaker/puppet_install_helper`), which installs Puppet from the public collections based on `PUPPET_INSTALL_TYPE` and does not honour `BEAKER_PUPPET_COLLECTION=preinstalled`. Left as-is, this module would install FOSS Puppet and never actually exercise Puppet Core. Its Gemfile also pins `beaker ~> 4.29`, against `beaker >= 6, < 8` for the rest of the fleet — each module bundles its own Beaker, so this is not a harness-wide conflict, but it does mean kdump runs against meaningfully older Beaker internals. Do not land this in the same batch as `selinux` on the strength of "reboot support" alone — it additionally needs either an upstream-style override of `run_puppet_install_helper`'s behavior, or a harness-side environment shim making it a no-op the way `install_puppet` did for `windowsfeature` (Appendix A). Treat as its own small spike |

### 7.6 Phase 4 — needs bundle-group handling and a larger time budget

| Module | Verdict | GCP image | Note |
|---|---|---|---|
| `puppet-elasticsearch` | **VM-FIXES-WITH-CAVEAT** | Rocky 9 / AlmaLinux 9 | `simp-beaker-helpers`, `rspec-retry` and `bcrypt` are already declared in the module's `:system_tests` Gemfile group — the fix is installing that bundle group, not adding a new gem. `vm.max_map_count` genuinely needs pre-setting to 262144 on the VM (GCP's default of 65530 is why this looks fixed on the CI runner's host kernel but wouldn't be on a fresh VM). Vault-licensed examples self-skip via `ENV['CI']`, so no Vault gem or service is needed. This is the heaviest suite in the fleet — 16 shared-example groups doing full install/restart cycles plus controller-side artifact downloads — budget accordingly against the 3-hour TTL |
| `puppet-systemd` | **VM-FIXES-WITH-CAVEAT** | Rocky 9 / AlmaLinux 9 | Notably, this unlocks test coverage upstream itself has never exercised: `resolved_spec.rb` only sets `manage_resolv_conf => true` when the hypervisor is not `container_podman`, so the `/etc/resolv.conf` symlink path this harness cares about has zero prior CI signal anywhere. Two VM-specific risks to watch rather than blockers: on EL9 GCP images, `systemd-resolved` isn't the active resolver by default, so symlinking `/etc/resolv.conf` to it can transiently break DNS for the rest of the run; on Ubuntu/Debian GCP images, netplan renders to `systemd-networkd`, so `networkd_spec.rb`'s "configure systemd stopped" context could drop the SSH session entirely. Target EL9 first — losing DNS mid-run is recoverable, losing the network connection is not |

### 7.7 Phase 5 — defer

| Module | Verdict | Note |
|---|---|---|
| `puppet-augeasproviders_grub` | **VM-FIXES-WITH-CAVEAT, high operational risk** | Two reboots are required and only a VM can provide them, but `06_grub2_superuser_spec.rb` runs (alphabetically) before the reboot in `10_grub_menuentry_spec.rb` and sets a GRUB superuser password. If menu entries aren't subsequently emitted with `--unrestricted`, the post-reboot VM can land at an unattended GRUB password prompt — no SSH, no console access via this harness, the full 3-hour TTL burned with zero diagnostic output. This needs either per-spec-file selection (skip `06_*`) or a serial-console/screenshot capability the harness does not have, before it is safe to enable. Also effectively EL-only in practice (`grubby`, `/etc/grub2.cfg`) despite metadata claiming Debian/Ubuntu support. No upstream acceptance CI exists to cross-check against |

### 7.8 Not scheduled — a VM does not fix these

Confirmed, not just estimated: reading the actual test code shows the recorded
blockers are unrelated to containers-versus-VMs, so provisioning a VM would
change nothing.

| Module | Why a VM doesn't help |
|---|---|
| `puppet-wget` | Three independent blockers, none infrastructure-related: `su - vagrant` (no such user on a GCP image, same as Docker), `--modulepath=/etc/puppet/modules` (the Puppet 3 path — a modern AIO install puts modules elsewhere, so the class would not even be found), and a `metadata.json` capped at RedHat/CentOS 6–7, Debian 8–9, Ubuntu 16.04/18.04 with no matching image in the provision service's catalogue. This is upstream test modernization, not a provisioning problem |
| `puppet-vault_lookup` | Confirmed structurally impossible on one SUT: `spec/acceptance/lookup_spec.rb` calls `find_host_with_role('vault')` against a fixed three-role topology (`master`, `vault`, `certs`), which raises if that role doesn't exist. The suite already runs successfully upstream — pinned to Docker, with a cross-image `COPY --from=certs:latest` build dependency between three Dockerfiles. The real unlock for this module is multi-host Docker nodesets with ordered image builds on the existing runner — a VM is strictly a detour from that, not a step toward it. Explicitly out of scope here (§1, non-goals: not multi-node) |

Both keep their `blocked` status. Update their `reason` text to record that a
VM was evaluated and specifically why it doesn't help, so the question starts
from this evidence next time rather than from scratch.

---

## 8. New / changed files

| File | Change |
|---|---|
| `lib/module_tester/provision_service.rb` | **New** — POST/DELETE client, inventory parsing |
| `lib/module_tester/vm.rb` | **New** — `prepare_vm`, `install_puppet_core_vm`, `write_vm_setfile` |
| `lib/module_tester/docker.rb` | Extract the EL/Debian install+scrub logic from `puppet_core_dockerfile` into a shared script generator; extend `strip_secrets_from_env!` |
| `lib/module_tester/adapters.rb` | Branch on provisioner at line 120; wrap acceptance in `ensure` for teardown |
| `lib/module_tester/runner.rb` | New CLI flags (`--provisioner`, `--vm-image`) |
| `lib/module_tester/classifier.rb` | Add the VM infrastructure stages to the harness-stage list (§9) |
| `config/modules.schema.json` | `provisioner` + `image` on `acceptanceTarget`; `setfile` conditionally optional; mixed-provisioner constraint |
| `config/modules.json` | Flip triaged modules from `blocked` to `running` with a `gcp` target |
| `scripts/build_matrix.rb` | Third matrix + `has_vm_acceptance` output |
| `.github/workflows/compatibility-runner-puppet{8,9}.yml` | New `test_acceptance_vm` job — **identically in both** |
| `.github/actions/prepare-test-matrix/action.yml` | New output passthrough |
| `.github/actions/run-module-test/action.yml` | New inputs |
| `.github/actions/publish-compatibility-results/action.yml` | `needs:` the new job |
| `docs/architecture-flow.md` | Provisioner branch in the diagram; VM stage table; generalize the two-stage isolation section beyond Docker |

---

## 9. Edge cases & decisions

- **Infrastructure failures must not read as incompatibility.** This is the
  subtlest correctness issue in the design.
  [`classifier.rb:28-33`](../lib/module_tester/classifier.rb#L28-L33) reads
  *only* the `acceptance` stage in acceptance mode: absent → `inconclusive`,
  non-passing → `not_compatible`. A failed provision produces no `acceptance`
  stage at all, so it would silently become `inconclusive` — and worse, any
  future path that lets a provisioning flake through would read as
  `not_compatible`, i.e. the harness would blame the module for a cloud outage.
  **`provision_vm`, `prepare_vm` and `install_puppet_core_vm` must be added to
  the harness-stage list at `classifier.rb:13-24`** so they classify as
  `harness_error`.
- **Teardown must be best-effort but always attempted.** In the normal case —
  the acceptance stage finishes, pass or fail — the `ensure` block's explicit
  `DELETE /v1/provision` tears the VM down within minutes; it does not wait out
  the job's `timeout-minutes` ceiling. That ceiling exists to bound the worst
  case (a hang), not to describe typical usage.

  The `ensure` block does not survive a killed runner, though — a cancelled
  job, a runner crash, or the `DELETE` call itself failing (network blip,
  facade hiccup) all skip it. The service's own two backstops cover that gap,
  and neither depends on the harness doing anything right:
  1. **The run-status reaper** destroys a VM once its associated GitHub
     **workflow run** — not the individual job — reports `completed` or
     `not found`. This is coarser than it sounds: if a sibling job (say
     `test_unit`) is still running, an orphaned VM from an early-failing
     `test_acceptance_vm` entry is not reaped until every other job in that
     same run also finishes.
  2. **The unconditional 3-hour TTL sweep** destroys any VM (and its firewall
     rule) past 3 hours regardless of run or job state — the true worst-case
     bound, independent of the reaper and independent of our own `DELETE`.

  These two backstops are not equally robust against every failure mode, and
  it is worth being explicit about which covers which:
  - **User cancels the workflow.** Resolves relatively quickly. GitHub Actions
    cancellation transitions the run to a terminal `completed` status
    (`conclusion: cancelled`) fairly promptly — exactly what the reaper polls
    for — so it is caught on the reaper's next cycle. GitHub also gives a job a
    brief grace period before force-killing it, so the harness's own `ensure`
    block has a real, if not guaranteed, chance to fire before the process
    dies.
  - **A GitHub Actions infrastructure outage.** This defeats the reaper's
    GitHub-status check specifically — `Scanner.finished?` polls *GitHub's*
    API for the run's status, and if GitHub itself is unreachable, that check
    cannot resolve either way. The 3-hour age-based sweep is what actually
    survives this: it queries GCP Compute directly for each instance's
    `creation_timestamp` and needs no GitHub API call, no Firestore
    job-status lookup, nothing that depends on GitHub being reachable at all.
    Treat it as the only guarantee that holds during a GitHub-side outage.
  - **A GCP-side infrastructure issue during provisioning itself — open
    question, not a solved problem.** This differs in kind from the other two:
    it is not "a VM exists and something later prevents tearing it down," it
    is "the provisioning call fails partway through" — a Terraform apply
    erroring after creating some resources, a quota hit mid-request, the
    backend crashing before writing a Firestore job record. If the harness
    never receives a `uuid` back, it has nothing to reference and cannot issue
    a `DELETE` for anything. Whether the service's own error handling cleans
    up its own partial resources in that case is internal to the service and
    not visible from its public source. **This is DevX's operational surface,
    not something harness-side design can mitigate — raise it with them
    directly (spike 4) rather than assume it is handled.**
  - **The reaper's actual polling interval is unknown to the harness.** Its
    schedule (`SCHEDULER_TIME`) is configured server-side at deploy time and
    is not visible from the source reviewed here. The 3-hour TTL bounds the
    worst case regardless of this interval, but the typical latency before a
    cancelled or GitHub-outage-orphaned VM is actually reclaimed is presently
    unknown (spike 7).
- **Stage timeouts.** `StageRunner`'s default is 1800s
  (`PUPPET_STAGE_TIMEOUT_SECONDS`). `provision_vm` needs its own, longer value;
  the service's own client uses a 300s read timeout with retries, and a cold VM
  plus Terraform apply can exceed the default comfortably.
- **A VM is always systemd.** The `docker_mode` (`sshd` | `systemd`) distinction
  is meaningless for VM targets and should be rejected by the schema rather than
  silently ignored.
- **`prereqs` remain host-runner packages.** They install on the Actions runner,
  not the SUT — unchanged by this design, and worth stating because it is easy
  to misread once a second SUT type exists.
- **Ephemeral key hygiene.** The generated keypair lives in the workspace for
  the duration of the run. It must not be written into the report, and the
  `acceptance_env` diagnostic stage must dump the key *path*, never contents.
- **Firewall pinning.** The service scopes the VM firewall to the requesting
  runner's public IP, so the host that provisions must be the host that runs
  Beaker. This holds naturally in a single job, but forbids any future split of
  provisioning and testing into separate jobs.

---

## 10. Implementation progress tracker

| Phase | Status |
|---|---|
| Phase 0 — spikes (§7.2) | ✅ **Complete 2026-09-08.** All 7 spikes closed — 1/2/3/5 by direct testing, 4/6/7 by DevX confirmation (Lukas) |
| Phase 1 — `puppet-swap_file` pilot (§7.3) | ✅ **Complete 2026-09-09.** Spine + `BEAKER_FACTER_memory.system.total` no-op fix (`Vm#write_fact_overrides`) verified live: 33/33 examples passing. Ledger row lands on the first nightly run after merge (see §7.3) |
| Phase 2 — zero-new-capability expansion: rsyslog, elastic_stack, openldap (§7.4) | **In progress.** `rsyslog` + `elastic_stack` landed 2026-09-08 as a config-only `gcp` target flip (branch `phase2/rsyslog-elastic_stack-vm-pilot`); live CI verification pending. `openldap` deferred — needs a new `vm_setup_commands`-shaped capability for `setenforce 0` that doesn't exist yet (see §7.4) |
| Phase 3 — reboot support + selinux, kdump (§7.5) | Not started |
| Phase 4 — bundle-group handling + elasticsearch, systemd (§7.6) | Not started |
| Phase 5 — deferred: augeasproviders_grub (§7.7) | Not started |
| Not scheduled: wget, vault_lookup (§7.8) | N/A — VM does not fix these |

---

## Appendix A: Why Windows was dropped

Windows was the original starting point and was investigated in depth before
being abandoned as poor value. Recorded here so the question is not reopened
from scratch. **No action is taken on any of these modules by this design** —
they stay exactly as they are in `config/modules.json`.

| Module | Finding |
|---|---|
| `puppet-windows_firewall` | **No `spec/acceptance/` directory exists on `master`** (verified against the git tree API). Only an orphaned `spec_helper_acceptance.rb` remains, which calls `Spec.configure` (a `NameError`) and `include Serverspec::Helper::WinRM` (a serverspec 1.x namespace; serverspec 2.x retains only `helper/type.rb`). There is nothing to run. Its recorded `pending` status is inaccurate — it has no acceptance tests — but correcting that is unrelated to VM work |
| `puppet-windowsfeature` | Real, clean specs (`apply_manifest` with `catch_failures`/`catch_changes`, plus a genuine serverspec `windows_feature` matcher). But `spec_helper_acceptance.rb` calls `install_puppet`, `install_cert_on_windows` and `puppet_module_install` — all `beaker-puppet` / `beaker-module_install_helper` DSL, and **`voxpupuli-acceptance 4.4.0` depends on neither**. Its own CI never runs acceptance, so this rotted unnoticed. Would require a harness-side DSL shim. Puppet 8 only (`openvox >= 8.19 < 9.0`) |
| `puppet-windows_env` | The repo 301-redirects to `puppetlabs/puppetlabs-windows_env` — first-party Perforce-maintained now, and Litmus-based rather than Beaker. Arguably outside the community-compatibility remit, but **left in place**; revisit separately |

Net: one module (`windowsfeature`) could be made to work, and only behind a
compatibility shim for a suite its own maintainers do not run.

Two facts worth preserving in case Windows is revisited, because they were the
expensive parts to establish:

1. The service's `windows.ps1.erb` bootstrap **already installs OpenSSH Server,
   starts `sshd`, sets PowerShell as the default shell via
   `HKLM:\SOFTWARE\OpenSSH\DefaultShell`, and puts the litmus user in
   Administrators.** So Beaker's SSH transport would reach a Windows VM with
   `is_cygwin: false` — no WinRM transport work needed.
2. Puppet Core's Windows agent MSI lives on `artifacts-puppetcore.puppet.com`
   behind `forge-key:<Forge API key>` — the same credential the harness already
   holds as `PUPPET_CORE_API_KEY`. (`beaker_puppet_helpers`'
   `get_agent_package_url` only knows the *public* `downloads.puppetlabs.com`
   path, so the licensed MSI URL pattern would still need pinning.)
