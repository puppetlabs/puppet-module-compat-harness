# frozen_string_literal: true

require 'yaml'
require 'fileutils'

module ModuleTester
  class Docker
    def initialize(stage_runner, workspace_dir)
      @stage = stage_runner
      @workspace_dir = workspace_dir
    end

    # Builds a Docker image with puppet-agent from authenticated Puppet Core
    # repos.  The API key is used ONLY during the docker build and is removed
    # from the resulting image layers.  Returns [image_tag, StageResult].
    def build_puppet_core_image(base_setfile_path, puppet_major, api_key, docker_mode: 'sshd', install_puppetserver: false, setup_commands: [])
      base = YAML.safe_load(File.read(base_setfile_path), permitted_classes: [Symbol])
      hosts_key = base['HOSTS']&.keys&.first
      raise "No HOSTS entry found in setfile #{base_setfile_path}" unless hosts_key

      host_cfg = base['HOSTS'][hosts_key]
      base_image = host_cfg['image'].to_s
      platform = host_cfg['platform'].to_s
      variant, version, _arch = platform.split('-', 3)
      existing_cmds = (host_cfg['docker_image_commands'] || []) + Array(setup_commands)

      image_tag = "puppet-core-sut:#{File.basename(base_setfile_path, '.*')}"
      dockerfile = puppet_core_dockerfile(base_image, existing_cmds, variant, version, puppet_major, docker_mode: docker_mode, install_puppetserver: install_puppetserver, certname: hosts_key)
      return [image_tag, Result.failed_stage('build_sut_image', 'Docker CLI not found in PATH')] unless @stage.command_available?('docker')

      build_dir = File.expand_path(File.join(@workspace_dir, '.docker-build'))
      FileUtils.mkdir_p(build_dir)
      dockerfile_path = File.join(build_dir, 'Dockerfile')
      File.write(dockerfile_path, dockerfile)

      if install_puppetserver
        repo_root = File.expand_path(File.join(__dir__, '..', '..'))
        spec_src = File.join(repo_root, 'config', 'compat-rpms', 'openvox-server.spec')
        spec_dst = File.join(build_dir, 'openvox-server.spec')
        return [image_tag, Result.failed_stage('build_sut_image', "Compatibility spec missing: #{spec_src}")] unless File.exist?(spec_src)

        FileUtils.cp(spec_src, spec_dst)
      end

      return [image_tag, Result.failed_stage('build_sut_image', "Docker build directory missing: #{build_dir}")] unless Dir.exist?(build_dir)
      return [image_tag, Result.failed_stage('build_sut_image', "Dockerfile missing: #{dockerfile_path}")] unless File.exist?(dockerfile_path)

      # Build with BuildKit secrets so the key is never stored in image metadata.
      build_cmd = [
        'docker', 'build',
        '--no-cache',
        '--secret', 'id=puppet_core_api_key,env=PUPPET_CORE_API_KEY',
        '-t', image_tag,
        '-f', 'Dockerfile',
        '.'
      ]

      build_env = ENV.to_h.merge(
        'DOCKER_BUILDKIT' => '1',
        'PUPPET_CORE_API_KEY' => api_key
      )

      stage = @stage.run_stage('build_sut_image', build_cmd, build_dir, build_env)
      [image_tag, stage]
    end

    # Writes a clean setfile YAML that references a pre-built local image.
    # No secrets are embedded in this file.
    def write_clean_setfile(base_path, image_tag, docker_mode: 'sshd')
      base = YAML.safe_load(File.read(base_path), permitted_classes: [Symbol])
      hosts_key = base['HOSTS']&.keys&.first
      raise "No HOSTS entry found in setfile #{base_path}" unless hosts_key

      host_cfg = base['HOSTS'][hosts_key]
      host_cfg['image'] = image_tag
      host_cfg['docker_image_commands'] = []  # everything is in the pre-built image

      if docker_mode == 'systemd'
        # Systemd mode: preserve the setfile's PID 1 command when provided
        # because init path differs across distributions/images.
        # SSH is started by systemd (ssh/sshd.service), not as the entrypoint.
        # Requires privileged container with appropriate cgroup mounts.
        host_cfg['docker_cmd'] = host_cfg['docker_cmd'].to_s.empty? ? '/sbin/init' : host_cfg['docker_cmd']
      else
        # Override beaker-docker's default command (`service sshd start; tail -f /dev/null`),
        # which fails in non-systemd containers and causes ECONNRESET loops.
        host_cfg['docker_cmd'] = '/usr/sbin/sshd -D -e'
      end

      out_dir = File.join(@workspace_dir, '.beaker-setfiles')
      FileUtils.mkdir_p(out_dir)
      out_path = File.join(out_dir, "#{File.basename(base_path, '.*')}-puppetcore.yml")
      File.write(out_path, YAML.dump(base))
      File.expand_path(out_path)
    end

    # Removes all secret-bearing keys from an env hash so that untrusted
    # subprocess code cannot read them.
    def self.strip_secrets_from_env!(env)
      %w[
        PUPPET_CORE_API_KEY
        PASSWORD
        USERNAME
        BUNDLE_RUBYGEMS___PUPPETCORE__PUPPET__COM
      ].each { |key| env.delete(key) }
    end

    # Returns the shell command lines that install puppet-agent from Puppet
    # Core repos, shared between the Docker path (embedded in a Dockerfile RUN
    # layer, below) and the VM path (piped over SSH — see vm.rb). Each line is
    # a plain shell statement with no trailing continuation backslash; callers
    # join them for their own transport (Dockerfile `&&`-chaining vs. a plain
    # multi-line script).
    #
    # `api_key_expr` is a shell expression, already correctly quoted by the
    # caller, that evaluates to the Puppet Core API key — e.g. Docker passes
    # `"$(cat /run/secrets/puppet_core_api_key)"` (sourced from a BuildKit
    # secret mount at RUN-time); the VM path passes the literal key value
    # (already substituted into the script text before it is piped over SSH,
    # so the credential never appears as a subprocess argv element on either
    # host — see vm.rb). Either way the key exists on disk (in the repo file)
    # only transiently, and is removed by the final `rm -f` line before the
    # script returns.
    def self.puppet_core_agent_install_lines(variant, version, puppet_major, api_key_expr:, install_puppetserver: false)
      collection = "puppet#{puppet_major}"
      case variant
      when 'el', 'centos', 'redhat', 'rocky', 'alma', 'fedora', 'amazon'
        release_rpm = "https://yum-puppetcore.puppet.com/public/#{collection}-release-#{variant}-#{version}.noarch.rpm"
        repo_file = "/etc/yum.repos.d/#{collection}-release.repo"
        puppet_install_pkgs = install_puppetserver ? 'puppet-agent puppetserver' : 'puppet-agent'
        [
          "PUPPET_CORE_API_KEY=#{api_key_expr}",
          "rpm -Uvh #{release_rpm}",
          "sed -i '/^\\[#{collection}\\]/a username=forge-key\\npassword='\"$PUPPET_CORE_API_KEY\" #{repo_file}",
          "dnf install -y #{puppet_install_pkgs} || yum install -y #{puppet_install_pkgs}",
          "rm -f #{repo_file}"
        ]
      when 'debian', 'ubuntu'
        release_deb_url = "https://apt-puppetcore.puppet.com/public/#{collection}-release-$(. /etc/os-release && echo $VERSION_CODENAME).deb"
        auth_file = "/etc/apt/auth.conf.d/#{collection}-puppetcore.conf"
        [
          "PUPPET_CORE_API_KEY=#{api_key_expr}",
          'apt-get update -qq && apt-get install -y wget',
          "wget -O /tmp/#{collection}-release.deb \"#{release_deb_url}\"",
          "dpkg -i /tmp/#{collection}-release.deb",
          'mkdir -p /etc/apt/auth.conf.d',
          "echo \"machine apt-puppetcore.puppet.com login forge-key password $PUPPET_CORE_API_KEY\" > #{auth_file}",
          'apt-get update -qq && apt-get install -y puppet-agent',
          'ln -sf /opt/puppetlabs/bin/puppet /usr/bin/puppet',
          'ln -sf /opt/puppetlabs/bin/facter /usr/bin/facter',
          'ln -sf /opt/puppetlabs/bin/hiera /usr/bin/hiera',
          'command -v puppet',
          'puppet --version',
          "rm -f #{auth_file}",
          'grep -RIl --exclude-dir=preferences.d apt-puppetcore.puppet.com /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null | xargs -r rm -f || true'
        ]
      else
        raise "Unsupported platform variant '#{variant}' for Puppet Core agent install"
      end
    end

    private

    # Generates a Dockerfile that installs puppet-agent from Puppet Core repos.
    # Credentials are consumed from a BuildKit secret mount and are never stored
    # in image layers or build metadata.
    def puppet_core_dockerfile(base_image, setup_commands, variant, version, puppet_major, docker_mode: 'sshd', install_puppetserver: false, certname: nil)
      lines = []
      lines << '# syntax=docker/dockerfile:1.4'
      lines << "FROM #{base_image}"
      # Ensure Puppet agent binaries are discoverable during Beaker SSH sessions.
      lines << 'ENV PATH="/opt/puppetlabs/bin:${PATH}"'
      # Signal to systemd (and other init tooling) that we are inside a container.
      # Without this, systemd may hang trying to mount cgroups or access hardware,
      # preventing multi-user.target from being reached (and sshd from starting).
      lines << 'ENV container=docker'

      # Run the base setfile setup commands (cronie, initscripts, etc.)
      setup_commands.each { |cmd| lines << "RUN #{cmd}" } unless setup_commands.empty?

      case variant
      when 'el', 'centos', 'redhat', 'rocky', 'alma', 'fedora', 'amazon'
        install_lines = self.class.puppet_core_agent_install_lines(
          variant, version, puppet_major,
          api_key_expr: '"$(cat /run/secrets/puppet_core_api_key)"',
          install_puppetserver: install_puppetserver
        )
        lines << dockerize_run("--mount=type=secret,id=puppet_core_api_key", install_lines)
        lines << "RUN dnf install -y openssh-server openssh-clients passwd || yum install -y openssh-server openssh-clients passwd"

        if install_puppetserver
          lines << "RUN dnf install -y rpm-build rpmdevtools || yum install -y rpm-build rpmdevtools"
          lines << "COPY openvox-server.spec /tmp/openvox-server.spec"
          lines << "RUN /opt/puppetlabs/bin/puppet config set certname #{certname} --section main" if certname
          lines << <<~'RUN_BUILD_RPM'.strip
            RUN mkdir -p /root/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS} \
             && cp /tmp/openvox-server.spec /root/rpmbuild/SPECS/ \
             && rpmbuild -bb /root/rpmbuild/SPECS/openvox-server.spec \
             && rpm -i /root/rpmbuild/RPMS/noarch/openvox-server-8.0.0-1.noarch.rpm \
             && rm -rf /root/rpmbuild /tmp/openvox-server.spec
          RUN_BUILD_RPM
          lines << "RUN dnf remove -y rpm-build rpmdevtools || yum remove -y rpm-build rpmdevtools"
        end
      when 'debian', 'ubuntu'
        install_lines = self.class.puppet_core_agent_install_lines(
          variant, version, puppet_major,
          api_key_expr: '"$(cat /run/secrets/puppet_core_api_key)"',
          install_puppetserver: install_puppetserver
        )
        # Docker's original apt install line additionally pulled in
        # openssh-server/openssh-client/passwd inline (the EL branch installs
        # these as a separate RUN afterward instead) — preserve that exact
        # placement so the generated Dockerfile is unchanged.
        install_lines = install_lines.map do |line|
          line == 'apt-get update -qq && apt-get install -y puppet-agent' ? "#{line} openssh-server openssh-client passwd" : line
        end
        lines << dockerize_run("--mount=type=secret,id=puppet_core_api_key", install_lines)
      else
        raise "Unsupported platform variant '#{variant}' for Puppet Core agent install"
      end

      # Configure SSH for Beaker connectivity.
      lines << <<~'RUN_SSH'.strip
        RUN mkdir -p /var/run/sshd \
         && ssh-keygen -A \
        && echo 'd /run/sshd 0755 root root -' > /etc/tmpfiles.d/sshd.conf \
        && for cfg in /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf; do \
            [ -f "$cfg" ] || continue; \
            if grep -Eq '^#?PermitRootLogin' "$cfg"; then sed -ri 's/^#?PermitRootLogin.*/PermitRootLogin yes/' "$cfg"; fi; \
            if grep -Eq '^#?PasswordAuthentication' "$cfg"; then sed -ri 's/^#?PasswordAuthentication.*/PasswordAuthentication yes/' "$cfg"; fi; \
            if grep -Eq '^#?UsePAM' "$cfg"; then sed -ri 's/^#?UsePAM.*/UsePAM no/' "$cfg"; fi; \
            if grep -Eq '^#?UseDNS' "$cfg"; then sed -ri 's/^#?UseDNS.*/UseDNS no/' "$cfg"; fi; \
            if grep -Eq '^#?MaxAuthTries' "$cfg"; then sed -ri 's/^#?MaxAuthTries.*/MaxAuthTries 1000/' "$cfg"; fi; \
          done \
        && if grep -Eq '^#?PermitRootLogin' /etc/ssh/sshd_config; then sed -ri 's/^#?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config; else echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config; fi \
        && if grep -Eq '^#?PasswordAuthentication' /etc/ssh/sshd_config; then sed -ri 's/^#?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config; else echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config; fi \
        && if grep -Eq '^#?UsePAM' /etc/ssh/sshd_config; then sed -ri 's/^#?UsePAM.*/UsePAM no/' /etc/ssh/sshd_config; else echo 'UsePAM no' >> /etc/ssh/sshd_config; fi \
        && if grep -Eq '^#?UseDNS' /etc/ssh/sshd_config; then sed -ri 's/^#?UseDNS.*/UseDNS no/' /etc/ssh/sshd_config; else echo 'UseDNS no' >> /etc/ssh/sshd_config; fi \
        && if grep -Eq '^#?MaxAuthTries' /etc/ssh/sshd_config; then sed -ri 's/^#?MaxAuthTries.*/MaxAuthTries 1000/' /etc/ssh/sshd_config; else echo 'MaxAuthTries 1000' >> /etc/ssh/sshd_config; fi \
         && echo 'root:root' | chpasswd
      RUN_SSH
      lines << 'EXPOSE 22'

      if docker_mode == 'systemd'
        # Systemd mode: use /sbin/init as a portable default so systemd manages all
        # services (including sshd). This requires the container to run
        # privileged with appropriate cgroup mounts.
        # Debian/Ubuntu use ssh.service; EL-family uses sshd.service.
        ssh_service = %w[debian ubuntu].include?(variant) ? 'ssh.service' : 'sshd.service'
        lines << "RUN systemctl enable #{ssh_service}"
        lines << 'CMD ["/sbin/init"]'
      else
        # sshd mode: run sshd directly as PID 1 without systemd.
        # This is the default — faster and more portable, but services
        # that require systemd (e.g. chronyd) will not function.
        lines << 'CMD ["/bin/sh", "-lc", "mkdir -p /var/run/sshd; ssh-keygen -A >/dev/null 2>&1 || true; exec /usr/sbin/sshd -D -e"]'
      end

      lines.join("\n") + "\n"
    end

    # Joins install lines into a single Dockerfile `RUN <mount_flag> \` block
    # with `&&`-chaining, matching the exact continuation-line style Docker
    # expects for a multi-command RUN instruction: the first content line has
    # no `&&` prefix, every subsequent line does, and consecutive lines are
    # joined with a trailing backslash before the newline.
    def dockerize_run(mount_flag, install_lines)
      logical_lines = ["RUN #{mount_flag}"]
      install_lines.each_with_index do |line, idx|
        logical_lines << "#{idx.zero? ? ' ' : ' && '}#{line}"
      end
      logical_lines.join(" \\\n")
    end
  end
end
