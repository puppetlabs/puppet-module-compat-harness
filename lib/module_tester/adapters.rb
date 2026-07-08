# frozen_string_literal: true

module ModuleTester
  class Adapters
    def initialize(stage_runner, docker, options)
      @stage = stage_runner
      @docker = docker
      @options = options
    end

    def run(module_dir, env, profile, result)
      if @options[:test_mode] == 'acceptance'
        run_acceptance(module_dir, env, result, profile)
        return
      end

      run_unit(module_dir, env, profile, result)
    end

    private

    def run_unit(module_dir, env, profile, result)
      # Prefer the rake/bundle path (over PDK) whenever the swap must govern the
      # actual test runtime:
      #   * uses_vox_vars — OpenVox modules whose Gemfile keys off OPENVOX_GEM_VERSION.
      #   * private source — the Gemfile.puppetcore overlay pins puppet/facter to
      #     the private Puppet Core source. PDK ignores that overlay and re-resolves
      #     against its own vendored FOSS puppet for `--puppet-version`, which would
      #     silently bypass the swap while the version probe still reported success.
      capability = result[:capability]
      prefer_rake = (capability.is_a?(Hash) && capability['uses_vox_vars']) ||
                    profile.fetch('gem_source_mode', '') == 'private'

      if @stage.command_available?('pdk') && !prefer_rake
        validate_stage = @stage.run_stage('validate', ['pdk', 'validate', '--puppet-version', profile.fetch('puppet_major').to_s], module_dir, env)
        result[:stages] << validate_stage
        downgrade_stale_reference_validate_failure(result, validate_stage)
        unit_stage = @stage.run_stage('unit', ['pdk', 'test', 'unit', '--puppet-version', profile.fetch('puppet_major').to_s], module_dir, env)
        result[:stages] << unit_stage
        result[:stages] << StageResult.new(
          name: 'fact_provider',
          status: 'passed',
          command: nil,
          exit_code: 0,
          duration_seconds: 0,
          output: 'fact_provider=unknown puppet_provider=unknown detection_method=skipped puppet_detection_method=skipped reason=pdk_adapter_path'
        )
        downgrade_puppet_server_default_unit_failure(result, unit_stage)
        downgrade_choria_openvox_unit_failure(result, unit_stage)
        return
      end

      return unless File.exist?(File.join(module_dir, 'Rakefile')) && @stage.command_available?('bundle')

      # Apply the same precedence guard pattern used for facter/openfact.
      # When both json and json_pure are present, prefer native json before
      # any rake task discovery runs, then record a probe stage for logs.
      json_enforcement = enforce_json_load_path(module_dir, env, profile)
      result[:stages] << JsonProviderDetector.detect(@stage, module_dir, env, enforcement: json_enforcement)

      tasks, rake_tasks_stage = @stage.rake_tasks(module_dir, env)
      result[:stages] << rake_tasks_stage
      if tasks.include?('validate')
        validate_stage = @stage.run_stage('validate', ['bundle', 'exec', 'rake', 'validate'], module_dir, env)
        result[:stages] << validate_stage
        downgrade_stale_reference_validate_failure(result, validate_stage)
      end

      # Detect fact provider once per module before any unit tests run.
      # This is deterministic: it inspects what `require 'facter'` resolves
      # to in the module's bundle plus parses Gemfile.lock. It does not
      # depend on tests actually calling the Facter API.
      enforcement = enforce_facter_load_path(module_dir, env, profile)
      result[:stages] << FactProviderDetector.detect(@stage, module_dir, env, result, enforcement: enforcement)
      result[:stages] << probe_runtime_versions(module_dir, env, 'unit_runtime_probe')

      if tasks.include?('spec')
        unit_stage = @stage.run_stage('unit', ['bundle', 'exec', 'rake', 'spec'], module_dir, env)
        result[:stages] << unit_stage
        downgrade_puppet_server_default_unit_failure(result, unit_stage)
        downgrade_choria_openvox_unit_failure(result, unit_stage)
      elsif tasks.include?('test')
        unit_stage = @stage.run_stage('unit', ['bundle', 'exec', 'rake', 'test'], module_dir, env)
        result[:stages] << unit_stage
        downgrade_puppet_server_default_unit_failure(result, unit_stage)
        downgrade_choria_openvox_unit_failure(result, unit_stage)
      else
        # No rake spec/test task was discovered. Record an explicit
        # failure stage that surfaces the discovered task list so the
        # root cause is visible in the compatibility report and the
        # rake_tasks log artifact can be downloaded for diagnosis.
        available = tasks.empty? ? '(none discovered)' : tasks.sort.uniq.join(', ')
        message = "No 'spec' or 'test' rake task found for module. " \
                  "Available rake tasks: #{available}. " \
                  "See rake_tasks stage log (.stage-rake_tasks.log) for full `rake -AT` output."
        result[:stages] << StageResult.new(
          name: 'unit',
          status: 'failed',
          command: nil,
          exit_code: -1,
          duration_seconds: 0,
          output: message
        )
      end
    end

    def run_acceptance(module_dir, env, result, profile)
      return unless @options[:allow_acceptance]
      return unless File.exist?(File.join(module_dir, 'Rakefile')) && @stage.command_available?('bundle')

      tasks, rake_tasks_stage = @stage.rake_tasks(module_dir, env)
      result[:stages] << rake_tasks_stage
      return unless result[:capability]['has_acceptance']
      return unless tasks.include?('beaker')

      puppet_core_api_key = ENV.fetch('PUPPET_CORE_API_KEY', '').strip
      docker_mode = @options.fetch(:docker_mode, 'sshd')

      acceptance_env = env.dup
      acceptance_env['BEAKER_HYPERVISOR'] = 'docker'
      effective_setfile = nil
      effective_collection = nil

      if @options[:beaker_setfile] && !puppet_core_api_key.empty?
        # Stage 1: Build a Docker image with Puppet Core pre-installed.
        # The API key is used only during the build and is NOT passed to
        # the acceptance test environment, so untrusted module test code
        # cannot read it.
        image_tag, build_stage = @docker.build_puppet_core_image(
          @options[:beaker_setfile],
          profile.fetch('puppet_major'),
          puppet_core_api_key,
          docker_mode: docker_mode,
          install_puppetserver: @options[:install_puppetserver],
          setup_commands: @options.fetch(:setup_commands, [])
        )
        result[:stages] << build_stage
        return if build_stage.status != 'passed'

        # Stage 2: Write a clean setfile that references the pre-built
        # image — no secrets embedded anywhere.
        effective_setfile = @docker.write_clean_setfile(@options[:beaker_setfile], image_tag, docker_mode: docker_mode)
        acceptance_env['BEAKER_SETFILE'] = effective_setfile
        acceptance_env['BEAKER_PUPPET_COLLECTION'] = 'preinstalled'
        effective_collection = 'preinstalled'
      elsif @options[:beaker_setfile]
        # No API key — fall back to FOSS puppet from public yum.puppet.com
        effective_setfile = File.expand_path(@options[:beaker_setfile])
        effective_collection = "puppet#{profile.fetch('puppet_major')}"
        acceptance_env['BEAKER_SETFILE'] = effective_setfile
        acceptance_env['BEAKER_PUPPET_COLLECTION'] = effective_collection
      else
        effective_collection = "puppet#{profile.fetch('puppet_major')}"
        acceptance_env['BEAKER_PUPPET_COLLECTION'] = effective_collection
      end

      # Strip all secrets from the env before running untrusted test code.
      Docker.strip_secrets_from_env!(acceptance_env)

      diag_lines = []
      diag_lines << "BEAKER_SETFILE=#{effective_setfile}" if effective_setfile
      diag_lines << "BEAKER_PUPPET_COLLECTION=#{effective_collection}" if effective_collection
      diag_lines << "BEAKER_HYPERVISOR=#{acceptance_env['BEAKER_HYPERVISOR']}"
      if effective_setfile && File.exist?(effective_setfile)
        diag_lines << "--- Effective setfile content ---"
        diag_lines << File.read(effective_setfile)
      end
      result[:stages] << StageResult.new(
        name: 'acceptance_env',
        status: 'passed',
        command: nil,
        exit_code: 0,
        duration_seconds: 0,
        output: diag_lines.join("\n")
      )

      pre_cmds = @options.fetch(:pre_acceptance_commands, [])
      pre_cmds.each_with_index do |cmd, idx|
        stage = @stage.run_stage("pre_acceptance_setup_#{idx}", ['bash', '-c', cmd], module_dir, acceptance_env)
        result[:stages] << stage
        return if stage.status != 'passed'
      end

      result[:stages] << probe_runtime_versions(module_dir, acceptance_env, 'acceptance_runtime_probe')
      result[:stages] << @stage.run_stage('acceptance', ['bundle', 'exec', 'rake', 'beaker'], module_dir, acceptance_env)
    end

    def probe_runtime_versions(module_dir, env, stage_name)
      script = <<~'RUBY'
        puppet = Gem::Specification.find_all_by_name('puppet').max_by(&:version)
        abort('puppet gem not installed') unless puppet
        expected = ENV.fetch('PUPPET_GEM_VERSION')
        abort("puppet #{puppet.version} != #{expected}") unless puppet.version.to_s == expected
        facter = Gem::Specification.find_all_by_name('facter').max_by(&:version)
        puts "runtime puppet=#{puppet.version} expected=#{expected} facter=#{facter&.version || 'not-installed'}"
      RUBY

      @stage.run_stage(
        stage_name,
        ['bundle', 'exec', 'ruby', '-e', script],
        module_dir,
        env
      )
    end

    def downgrade_puppet_server_default_unit_failure(result, unit_stage)
      return if unit_stage.nil?
      return if unit_stage.status == 'passed'

      output = unit_stage.output.to_s

      # Detect the specific Puppet 8.12 breaking change: the default value of the
      # 'server' setting changed from 'puppet' to '' (empty string).
      # Unit specs that hardcode the old default produce exactly this diff pattern.
      # See: https://help.puppet.com/core/current/Content/PuppetCore/PuppetReleaseNotes/release_notes_puppet_x-8-12-0.htm
      return unless output.include?('"server"=>"puppet"') && output.include?('"server"=>""')

      # Only downgrade when this is the sole rspec failure — don't mask unrelated failures.
      return if output.scan(/::error /).count > 1

      warning = 'Unit spec asserts the Puppet "server" setting default is "puppet", but Puppet Core 8.12+ ' \
                'changed this default to "" (empty string). The spec must be updated to reflect the ' \
                'new Puppet 8.12 behaviour. ' \
                'See: https://help.puppet.com/core/current/Content/PuppetCore/PuppetReleaseNotes/release_notes_puppet_x-8-12-0.htm'

      result[:dependency_status] = 'warning'
      result[:dependency_message] = warning
      Annotations.github_annotation('warning', "#{result[:module]} Puppet 8.12 server default", warning)

      result[:stages] << StageResult.new(
        name: 'puppet_server_default_warning',
        status: 'passed',
        command: nil,
        exit_code: 0,
        duration_seconds: 0,
        output: warning
      )

      unit_stage.status = 'passed'
      unit_stage.exit_code = 0
      unit_stage.output = [
        output,
        'Detected Puppet Core 8.12 server setting default change; unit failure downgraded to compatibility warning.'
      ].join("\n")
    end

    def downgrade_choria_openvox_unit_failure(result, unit_stage)
      return if unit_stage.nil?
      return if unit_stage.status == 'passed'

      output = unit_stage.output.to_s
      return unless output.include?('Choria only supports OpenVox')

      # Only downgrade when ALL rspec failures are attributable to the Choria/OpenVox check.
      # Split on ::error markers and verify every error section contains the Choria message.
      error_sections = output.split(/(?=::error )/).reject { |s| s.strip.empty? }
      choria_errors = error_sections.select { |s| s.start_with?('::error') }
      non_choria_errors = choria_errors.reject { |s| s.include?('Choria only supports OpenVox') }
      return if choria_errors.empty? || non_choria_errors.any?

      warning = 'Unit specs for the r10k::mcollective integration class fail because the choria fixture ' \
                'module only supports OpenVox and raises a hard error when run under Puppet Core. ' \
                'The r10k::mcollective class cannot be used with Puppet Core when mcollective/choria ' \
                'integration is enabled. All other puppet-r10k functionality is compatible with ' \
                'Perforce Puppet products. See KNOWN_INCOMPATIBLE.md for details.'

      result[:dependency_status] = 'warning'
      result[:dependency_message] = warning
      Annotations.github_annotation('warning', "#{result[:module]} choria/mcollective integration", warning)

      result[:stages] << StageResult.new(
        name: 'choria_openvox_warning',
        status: 'passed',
        command: nil,
        exit_code: 0,
        duration_seconds: 0,
        output: warning
      )

      unit_stage.status = 'passed'
      unit_stage.exit_code = 0
      unit_stage.output = [
        output,
        'Detected Choria OpenVox-only restriction; mcollective integration test failures downgraded to compatibility warning.'
      ].join("\n")
    end

    def downgrade_stale_reference_validate_failure(result, validate_stage)
      return if validate_stage.nil?
      return if validate_stage.status == 'passed'

      output = validate_stage.output.to_s
      return unless output.include?('REFERENCE.md is outdated')

      warning = 'REFERENCE.md is outdated; to regenerate: bundle exec rake strings:generate:reference'
      result[:documentation_status] = 'warning'
      result[:documentation_message] = warning
      Annotations.github_annotation('warning', "#{result[:module]} documentation", warning)
      result[:stages] << StageResult.new(
        name: 'documentation_warning',
        status: 'passed',
        command: nil,
        exit_code: 0,
        duration_seconds: 0,
        output: warning
      )

      validate_stage.status = 'passed'
      validate_stage.exit_code = 0
      validate_stage.output = [
        output,
        'Detected stale REFERENCE.md documentation drift; recorded as warning for compatibility classification.'
      ].join("\n")
    end

    # Best-effort enforcement: when the resolved bundle contains both facter
    # and openfact gems, prepend the facter gem's lib/ directory to RUBYOPT
    # so that `require 'facter'` resolves to the Perforce Facter gem instead
    # of OpenFact. This is inherited by child processes spawned via
    # `system()` (e.g. rspec via rake spec).
    #
    # Returns an enforcement status string:
    #   'skipped'   — not applicable (no openfact in bundle, or not private source mode)
    #   'attempted' — tried but could not locate facter gem path
    #   'succeeded' — RUBYOPT prepended successfully
    def enforce_facter_load_path(module_dir, env, profile)
      return 'skipped' unless profile.fetch('gem_source_mode', '') == 'private'

      lockfile_path = FactProviderDetector.resolve_lockfile_path(module_dir, env)
      lock_info = FactProviderDetector.parse_gemfile_lock(lockfile_path)

      return 'skipped' unless lock_info[:openfact] && lock_info[:facter]

      facter_lib = find_facter_gem_lib(module_dir, env, lock_info[:facter])
      return 'attempted' unless facter_lib && File.directory?(facter_lib)

      existing_rubyopt = env.fetch('RUBYOPT', '').to_s
      env['RUBYOPT'] = "-I#{facter_lib} #{existing_rubyopt}".strip

      'succeeded'
    end

    # Locate the installed facter gem's lib/ directory within the bundle path.
    def find_facter_gem_lib(module_dir, env, facter_version)
      # Try `bundle show facter` first — most reliable.
      if @stage.command_available?('bundle')
        stage = @stage.run_stage(
          'facter_gem_path',
          ['bundle', 'show', 'facter'],
          module_dir, env
        )
        if stage.exit_code == 0
          gem_root = stage.output.to_s.strip.lines.last&.strip
          if gem_root && !gem_root.empty?
            lib_path = File.join(gem_root, 'lib')
            return lib_path if File.directory?(lib_path)
          end
        end
      end

      # Fallback: scan the bundle path for the gem directory.
      bundle_path = env.fetch('BUNDLE_PATH', File.join(module_dir, 'vendor', 'bundle')).to_s
      pattern = File.join(bundle_path, '**', "facter-#{facter_version}", 'lib')
      Dir.glob(pattern).first
    end

    # Best-effort enforcement: when both json and json_pure are present,
    # prepend native json's lib dir and preload json via RUBYOPT so later
    # requires resolve to the native gem instead of json_pure.
    #
    # Returns an enforcement status string:
    #   'skipped'   — not applicable (no json_pure in bundle, or not private source mode)
    #   'attempted' — tried but could not locate native json gem path
    #   'succeeded' — RUBYOPT updated successfully
    def enforce_json_load_path(module_dir, env, profile)
      return 'skipped' unless profile.fetch('gem_source_mode', '') == 'private'

      lockfile_path = FactProviderDetector.resolve_lockfile_path(module_dir, env)
      lock_info = JsonProviderDetector.parse_gemfile_lock(lockfile_path)
      return 'skipped' unless lock_info[:json_pure] && lock_info[:json]

      json_lib = find_json_gem_lib(module_dir, env)
      return 'attempted' unless json_lib && File.directory?(json_lib)

      existing_rubyopt = env.fetch('RUBYOPT', '').to_s
      rubyopt = "-I#{json_lib} #{existing_rubyopt}".strip
      rubyopt = "-rjson #{rubyopt}" unless rubyopt.include?('-rjson')
      env['RUBYOPT'] = rubyopt.strip

      'succeeded'
    end

    # Locate the installed native json gem's lib/ directory within the bundle path.
    def find_json_gem_lib(module_dir, env)
      if @stage.command_available?('bundle')
        stage = @stage.run_stage(
          'json_gem_path',
          ['bundle', 'show', 'json'],
          module_dir, env
        )
        if stage.exit_code == 0
          gem_root = stage.output.to_s.strip.lines.last&.strip
          if gem_root && !gem_root.empty?
            lib_path = File.join(gem_root, 'lib')
            return lib_path if File.directory?(lib_path)
          end
        end
      end

      bundle_path = env.fetch('BUNDLE_PATH', File.join(module_dir, 'vendor', 'bundle')).to_s
      pattern = File.join(bundle_path, '**', 'json-*', 'lib')
      Dir.glob(pattern).sort.reverse.find { |path| File.directory?(path) }
    end
  end
end
