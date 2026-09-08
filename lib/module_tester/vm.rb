# frozen_string_literal: true

require 'fileutils'
require 'yaml'
require 'shellwords'

module ModuleTester
  # VM preparation for the GCP provision-service acceptance path
  # (docs/vm-based-acceptance-testing.md §2.4, §3.1-3.2). A VM returned by
  # ProvisionService arrives reachable only as a non-root "litmus" user with
  # a service-issued password. This class escalates to root via an ephemeral,
  # harness-generated key (so the shared password never reaches the
  # untrusted test stage), installs the Puppet Core agent using the same
  # install logic Docker.puppet_core_agent_install_lines defines, and writes
  # the Beaker setfile that points at the result.
  class Vm
    SSH_OPTS = %w[-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10].freeze

    # GCP image family -> Beaker platform string (design doc §3.1). Small and
    # mechanical by design — see the doc for why this doesn't need YAML
    # setfiles the way the Docker path does.
    PLATFORM_BY_IMAGE = {
      'rocky-linux-cloud/rocky-linux-9' => 'el-9-x86_64',
      'rhel-9' => 'el-9-x86_64',
      'centos-stream-9' => 'el-9-x86_64',
      'almalinux-cloud/almalinux-9' => 'el-9-x86_64',
      'rocky-linux-cloud/rocky-linux-8' => 'el-8-x86_64',
      'rhel-8' => 'el-8-x86_64',
      'centos-stream-8' => 'el-8-x86_64',
      'rhel-10' => 'el-10-x86_64',
      'debian-12' => 'debian-12-x86_64',
      'ubuntu-2404-lts' => 'ubuntu-24.04-x86_64'
    }.freeze

    def initialize(stage_runner, workspace_dir)
      @stage = stage_runner
      @workspace_dir = workspace_dir
    end

    def self.platform_for_image(image)
      PLATFORM_BY_IMAGE.fetch(image) { raise "No Beaker platform mapping for GCP image '#{image}' — add one to Vm::PLATFORM_BY_IMAGE" }
    end

    # Escalates from the service's litmus/password login to root via an
    # ephemeral SSH key generated for this run only. Returns
    # [key_path_or_nil, StageResult]. The litmus password is used only in
    # this method (as an ad-hoc `extra_secrets` redaction value, since it is
    # never placed in an env hash — see Redactor) and is discarded once this
    # returns; nothing downstream ever sees it.
    def prepare_vm(host, module_dir)
      key_path = File.expand_path(File.join(@workspace_dir, '.vm-keys', "#{host.uuid}_id_ed25519"))
      FileUtils.mkdir_p(File.dirname(key_path))
      FileUtils.rm_f(key_path)
      FileUtils.rm_f("#{key_path}.pub")

      keygen = @stage.run_stage(
        'prepare_vm_keygen',
        ['ssh-keygen', '-t', 'ed25519', '-N', '', '-f', key_path, '-q'],
        module_dir, {}
      )
      return [nil, keygen] unless keygen.status == 'passed'

      File.chmod(0o600, key_path)
      pubkey = File.read("#{key_path}.pub").strip

      script = <<~REMOTESCRIPT
        set -euo pipefail
        sudo mkdir -p /root/.ssh
        echo #{Shellwords.escape(pubkey)} | sudo tee -a /root/.ssh/authorized_keys > /dev/null
        sudo chmod 700 /root/.ssh
        sudo chmod 600 /root/.ssh/authorized_keys
        sudo sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
        sudo systemctl restart sshd
      REMOTESCRIPT

      escalate = @stage.run_stage(
        'prepare_vm_escalate',
        ['sshpass', '-e', 'ssh', *SSH_OPTS, "#{host.user}@#{host.ip}", 'bash', '-s'],
        module_dir, { 'SSHPASS' => host.password },
        stdin: script,
        extra_secrets: [host.password]
      )
      return [nil, escalate] unless escalate.status == 'passed'

      verify = @stage.run_stage(
        'prepare_vm_verify_root',
        ['ssh', *SSH_OPTS, '-i', key_path, "root@#{host.ip}", 'whoami'],
        module_dir, {}
      )
      return [nil, verify] unless verify.status == 'passed' && verify.output.to_s.include?('root')

      [key_path, verify]
    end

    # Installs the Puppet Core agent over SSH using the same install logic
    # Docker.puppet_core_agent_install_lines defines for the container path.
    # The API key is interpolated into the script text locally, before it is
    # piped over SSH stdin, so it never appears as a subprocess argv element
    # on either host (verified byte-for-byte in the design doc's spike 1).
    def install_puppet_core_vm(host, key_path, platform, puppet_major, api_key, module_dir, install_puppetserver: false)
      variant, version, = platform.split('-', 3)
      install_lines = Docker.puppet_core_agent_install_lines(
        variant, version, puppet_major,
        api_key_expr: Shellwords.escape(api_key),
        install_puppetserver: install_puppetserver
      )

      script = <<~REMOTESCRIPT
        set -euo pipefail
        #{install_lines.join("\n")}
      REMOTESCRIPT

      @stage.run_stage(
        'install_puppet_core_vm',
        ['ssh', *SSH_OPTS, '-i', key_path, "root@#{host.ip}", 'bash', '-s'],
        module_dir, {},
        stdin: script,
        extra_secrets: [api_key]
      )
    end

    # Writes a Beaker setfile pointing at the prepared VM. Unlike the Docker
    # path's write_clean_setfile, there is no base setfile to start from —
    # everything Beaker needs (platform, ip, key path) is derived directly
    # (design doc §3.1). No secrets are embedded; the key path is a
    # reference, not key material.
    def write_vm_setfile(host, key_path, platform)
      setfile = {
        'HOSTS' => {
          'gcp-vm' => {
            'platform' => platform,
            'hypervisor' => 'none',
            'ip' => host.ip,
            'user' => 'root',
            'ssh' => {
              'keys' => [key_path],
              'paranoid' => false
            }
          }
        },
        'CONFIG' => {
          'log_level' => 'verbose',
          'type' => 'foss'
        }
      }

      out_dir = File.join(@workspace_dir, '.beaker-setfiles')
      FileUtils.mkdir_p(out_dir)
      out_path = File.join(out_dir, "gcp-#{host.uuid}.yml")
      File.write(out_path, YAML.dump(setfile))
      File.expand_path(out_path)
    end
  end
end
