# frozen_string_literal: true

module ModuleTester
  DEFAULT_PUPPET_CORE_SOURCE_URL = 'https://rubygems-puppetcore.puppet.com'

  class Bootstrap
    def initialize(stage_runner)
      @stage = stage_runner
    end

    def run(module_dir, env, result, profile)
      return unless File.exist?(File.join(module_dir, 'Gemfile')) && @stage.command_available?('bundle')

      configure_bundle(module_dir, env, result)
      configure_source(module_dir, env, result, profile)

      bootstrap_stage = @stage.run_stage('bootstrap', ['bundle', 'install'], module_dir, env)
      result[:stages] << bootstrap_stage

      return if bootstrap_stage.status == 'passed'

      attempt_dependency_recovery(module_dir, env, result, bootstrap_stage)
    end

    private

    def configure_bundle(module_dir, env, result)
      bundle_path = ENV.fetch('PUPPET_COMPAT_BUNDLE_PATH', 'vendor/bundle').to_s.strip
      bundle_path = 'vendor/bundle' if bundle_path.empty?
      result[:stages] << @stage.run_stage('bundle_config_path', ['bundle', 'config', 'set', '--local', 'path', bundle_path], module_dir, env)
      result[:stages] << @stage.run_stage('bundle_config_multisource', ['bundle', 'config', 'set', '--local', 'disable_multisource', 'true'], module_dir, env)
    end

    def configure_source(module_dir, env, result, profile)
      return unless profile.fetch('gem_source_mode') == 'private'

      normalize_runtime_gem_versions(module_dir, profile, result)

      source_url = ENV.fetch('PUPPET_CORE_SOURCE_URL', DEFAULT_PUPPET_CORE_SOURCE_URL).strip
      result[:stages] << StageResult.new(
        name: 'bundle_config_source',
        status: 'passed',
        command: nil,
        exit_code: 0,
        duration_seconds: 0,
        output: "Using authenticated source: #{source_url}"
      )

      if split_source_mode?
        overlay_gemfile = write_split_gemfile(module_dir, profile, source_url)
        env['BUNDLE_GEMFILE'] = overlay_gemfile
        display_gemfile = File.basename(overlay_gemfile)
        result[:stages] << StageResult.new(
          name: 'bundle_config_split_gemfile',
          status: 'passed',
          command: nil,
          exit_code: 0,
          duration_seconds: 0,
          output: "Using split-source Gemfile: #{display_gemfile}"
        )
      else
        result[:stages] << @stage.run_stage('bundle_config_source_mirror', ['bundle', 'config', 'set', '--local', 'mirror.https://rubygems.org', source_url], module_dir, env)
      end
    end

    def attempt_dependency_recovery(module_dir, env, result, bootstrap_stage)
      dependency_warning = extract_dependency_incompatibility_warning(bootstrap_stage.output)
      return if dependency_warning.nil?

      result[:dependency_status] = 'warning'
      result[:dependency_message] = dependency_warning
      Annotations.github_annotation('warning', "#{result[:module]} dependency", dependency_warning)
      result[:stages] << StageResult.new(
        name: 'dependency_warning',
        status: 'passed',
        command: nil,
        exit_code: 0,
        duration_seconds: 0,
        output: dependency_warning
      )

      patch_info = patch_module_gemfile_for_puppet_core(module_dir)
      result[:stages] << StageResult.new(
        name: 'bootstrap_dependency_patch',
        status: patch_info[:changed] ? 'passed' : 'failed',
        command: nil,
        exit_code: patch_info[:changed] ? 0 : 1,
        duration_seconds: 0,
        output: patch_info[:message]
      )
      return unless patch_info[:changed]

      retry_stage = @stage.run_stage('bootstrap_puppet_core_retry', ['bundle', 'install'], module_dir, env)
      result[:stages] << retry_stage
      return unless retry_stage.status == 'passed'

      bootstrap_stage.status = 'passed'
      bootstrap_stage.exit_code = 0
      bootstrap_stage.output = [bootstrap_stage.output.to_s, 'Recovered by applying Puppet Core-compatible gem constraints and retrying bundle install.'].join("\n")
    end

    def extract_dependency_incompatibility_warning(output)
      text = output.to_s
      return nil unless text.include?('Could not find compatible versions') || text.include?('version solving has failed')

      return nil unless text.match?(/depends on puppet-resource_api/i)

      'Dependency incompatibility detected during bundle install; applying Puppet Core-compatible gem constraints and retrying.'
    end

    def patch_module_gemfile_for_puppet_core(module_dir)
      gemfile_path = File.join(module_dir, 'Gemfile')
      return { changed: false, message: 'Gemfile not found; cannot apply Puppet Core dependency fallback.' } unless File.exist?(gemfile_path)

      original = File.read(gemfile_path)
      updated = original.dup
      changes = []

      replacements = {
        'voxpupuli-release' => '~> 5.2',
        'openvox-strings' => '< 6.1.0',
        'openvox' => '< 8.24',
        'puppet-resource_api' => '~> 1.9'
      }

      replacements.each do |gem_name, requirement|
        updated, changed = force_gem_requirement(updated, gem_name, requirement)
        changes << "#{gem_name}=#{requirement}" if changed
      end

      if !updated.include?("gem 'puppet-resource_api'") && !updated.include?("gem \"puppet-resource_api\"")
        updated << "\n# Added by compatibility harness for Puppet Core dependency resolution\ngem 'puppet-resource_api', '~> 1.9'\n"
        changes << 'puppet-resource_api=~> 1.9 (added)'
      end

      return { changed: false, message: 'No compatible Gemfile overrides could be applied.' } if updated == original

      backup_path = File.join(module_dir, 'Gemfile.before-puppet-core-compat')
      File.write(backup_path, original)
      File.write(gemfile_path, updated)

      {
        changed: true,
        message: "Applied Puppet Core Gemfile overrides: #{changes.join(', ')}"
      }
    rescue StandardError => e
      { changed: false, message: "Failed to patch Gemfile for Puppet Core fallback: #{e.message}" }
    end

    def force_gem_requirement(content, gem_name, requirement)
      changed = false
      pattern = /^\s*gem\s+['\"]#{Regexp.escape(gem_name)}['\"](?:\s*,\s*([^\n#]+))?/m

      updated = content.gsub(pattern) do |line|
        new_line = if line.match?(/,\s*['\"][^'\"]+['\"]/)
                     line.sub(/,\s*['\"][^'\"]+['\"]/m, ", '#{requirement}'")
                   else
                     line.sub(/(['\"]#{Regexp.escape(gem_name)}['\"])/, "\\1, '#{requirement}'")
                   end
        changed ||= (new_line != line)
        new_line
      end

      [updated, changed]
    end

    def split_source_mode?
      ENV.fetch('PUPPET_SPLIT_SOURCES', 'true') == 'true'
    end

    def write_split_gemfile(module_dir, profile, source_url)
      overlay_gemfile = File.expand_path('Gemfile.puppetcore', module_dir)
      puppet_version = profile.fetch('puppet_core_version').to_s
      facter_version = profile.fetch('facter_version', '').to_s

      lines = []
      lines << "eval_gemfile 'Gemfile'"
      lines << ""
      lines << "gem 'json', '>= 2.5.0', require: false"
      lines << ""
      lines << "source '#{source_url}' do"
      lines << "  gem 'puppet', '= #{puppet_version}', require: false"
      lines << "  gem 'facter', '= #{facter_version}', require: false" unless facter_version.empty?
      lines << "end"
      lines << ""

      File.write(overlay_gemfile, lines.join("\n"))
      overlay_gemfile
    end

    def normalize_runtime_gem_versions(module_dir, profile, result)
      gemfile_path = File.join(module_dir, 'Gemfile')
      return unless File.exist?(gemfile_path)

      _ = profile # version comes from overlay; main Gemfile only needs constraints stripped
      original = File.read(gemfile_path)
      updated = original.dup
      changes = []

      # Strip version constraints from any existing puppet/facter declarations
      # in the main Gemfile so they don't conflict with the exact-version pin
      # added by the split-source overlay (Gemfile.puppetcore). We do NOT add
      # puppet/facter to the main Gemfile here — those gems come from the
      # private puppetcore source via the overlay, not from rubygems.org.
      #
      # Two declaration shapes are handled:
      #   1. Literal:  gem 'puppet', '>= 6.0'          (voxpupuli / classic)
      #   2. Dynamic:  gems['puppet'] = location_for(...)  then a
      #                `gems.each { |n, p| gem n, *p }` loop (current
      #                pdk-templates default). Leaving this in place makes
      #                bundler see `puppet` from BOTH rubygems.org (main
      #                Gemfile) and the puppetcore source (overlay), which is a
      #                hard "same gem from two sources" conflict.
      %w[puppet facter].each do |gem_name|
        new_content, changed = strip_gem_version_constraint(updated, gem_name)
        if changed
          updated = new_content
          changes << "#{gem_name}=unconstrained (overlay pins exact version)"
          next
        end

        new_content, changed = strip_dynamic_gem_assignment(updated, gem_name)
        if changed
          updated = new_content
          changes << "#{gem_name}=removed dynamic gems[] assignment (overlay pins exact version)"
        end
      end

      return if updated == original

      backup_path = File.join(module_dir, 'Gemfile.before-runtime-normalize')
      File.write(backup_path, original)
      File.write(gemfile_path, updated)

      result[:stages] << StageResult.new(
        name: 'bootstrap_runtime_gem_normalize',
        status: 'passed',
        command: nil,
        exit_code: 0,
        duration_seconds: 0,
        output: "Normalized runtime gem requirements in Gemfile: #{changes.join(', ')}"
      )
    rescue StandardError => e
      result[:stages] << StageResult.new(
        name: 'bootstrap_runtime_gem_normalize',
        status: 'failed',
        command: nil,
        exit_code: 1,
        duration_seconds: 0,
        output: "Failed to normalize runtime gem requirements: #{e.message}"
      )
    end

    def gem_declared_in_gemfile?(module_dir, gem_name)
      gemfile_path = File.join(module_dir, 'Gemfile')
      return false unless File.exist?(gemfile_path)

      gem_declared_in_content?(File.read(gemfile_path), gem_name)
    end

    def gem_declared_in_content?(content, gem_name)
      content.match?(/^\s*gem\s+['\"]#{Regexp.escape(gem_name)}['\"]/)
    end

    # Strip any version constraint(s) from a `gem 'name', '...'` declaration by
    # commenting out the entire line. This removes it from Bundler's dependency
    # resolution entirely, allowing the split-source overlay (Gemfile.puppetcore)
    # to be the sole authority for puppet/facter via the puppetcore source.
    # Prevents source-binding conflicts and version-requirement conflicts.
    #
    # Handles forms:
    #   gem 'puppet'
    #   gem 'puppet', '>= 6.0'
    #   gem 'puppet', '>= 6.0', '< 9.0'
    #   gem 'puppet', '>= 6.0', require: false
    #   gem "puppet", "~> 8.0", :require => false
    def strip_gem_version_constraint(content, gem_name)
      changed = false
      pattern = /^(\s*)gem\s+['\"]#{Regexp.escape(gem_name)}['\"].*$/

      updated = content.gsub(pattern) do
        indent = Regexp.last_match(1)
        original_line = Regexp.last_match(0)
        if original_line !~ /^\s*#/  # only comment if not already commented
          changed = true
          "#{indent}# Pinned by compatibility harness in Gemfile.puppetcore\n#{indent}# #{original_line.lstrip}"
        else
          original_line
        end
      end

      [updated, changed]
    end

    # Neutralize the pdk-templates "dynamic" gem declaration form by commenting
    # out the hash assignment. The template collects puppet/facter/hiera into a
    # `gems` hash and later emits them via `gems.each { |n, p| gem n, *p }`.
    # Commenting the assignment removes the key from the hash, so the loop never
    # declares that gem — leaving the split-source overlay (Gemfile.puppetcore)
    # as the sole authority for it via the puppetcore source.
    #
    # Handles forms:
    #   gems['puppet'] = location_for(puppet_version)
    #   gems['facter'] = location_for(facter_version) if facter_version
    #   gems["facter"] = location_for(ENV['FACTER_GEM_VERSION']) if ENV['FACTER_GEM_VERSION']
    def strip_dynamic_gem_assignment(content, gem_name)
      changed = false
      pattern = /^(\s*)gems\[\s*['\"]#{Regexp.escape(gem_name)}['\"]\s*\]\s*=.*$/

      updated = content.gsub(pattern) do
        indent = Regexp.last_match(1)
        original_line = Regexp.last_match(0)
        if original_line !~ /^\s*#/  # only comment if not already commented
          changed = true
          "#{indent}# Pinned by compatibility harness in Gemfile.puppetcore\n#{indent}# #{original_line.lstrip}"
        else
          original_line
        end
      end

      [updated, changed]
    end
  end
end
