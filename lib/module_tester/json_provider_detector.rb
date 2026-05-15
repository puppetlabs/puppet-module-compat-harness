# frozen_string_literal: true

module ModuleTester
  # Deterministic runtime provider detector for JSON.
  #
  # In some module bundles both `json` and `json_pure` may be resolved.
  # This probe records which provider wins `require 'json'` at runtime.
  module JsonProviderDetector
    module_function

    PROBE_RUBY = <<~RUBY
      begin
        require 'json'
        loc = JSON.method(:parse).source_location
        path = loc ? loc.first : ''
        json_spec = Gem.loaded_specs['json']
        json_pure_spec = Gem.loaded_specs['json_pure']
        puts "JSON_PROVIDER_SOURCE=" + path.to_s
        puts "JSON_PROVIDER_VERSION=" + (defined?(JSON::VERSION) ? JSON::VERSION.to_s : '')
        puts "JSON_PROVIDER_JSON_SPEC=" + (json_spec ? json_spec.full_name.to_s : '')
        puts "JSON_PROVIDER_JSON_PURE_SPEC=" + (json_pure_spec ? json_pure_spec.full_name.to_s : '')
      rescue LoadError => e
        puts "JSON_PROVIDER_SOURCE="
        puts "JSON_PROVIDER_LOAD_ERROR=" + e.message
      end
    RUBY

    # Build the StageResult for the json_provider stage and return it.
    #
    # Options:
    #   enforcement: nil | 'skipped' | 'attempted' | 'succeeded'
    def detect(stage_runner, module_dir, env, enforcement: nil)
      lockfile_path = FactProviderDetector.resolve_lockfile_path(module_dir, env)
      lock_info = parse_gemfile_lock(lockfile_path)
      probe_info = run_resolution_probe(stage_runner, module_dir, env)
      provider, provider_gem = classify_provider(probe_info, lock_info)

      StageResult.new(
        name: 'json_provider',
        status: 'passed',
        command: probe_info[:command_display],
        exit_code: probe_info[:exit_code] || 0,
        duration_seconds: probe_info[:duration_seconds] || 0,
        output: build_summary(provider, provider_gem, probe_info, lock_info, lockfile_path, enforcement: enforcement)
      )
    end

    def parse_gemfile_lock(path)
      info = { json: nil, json_pure: nil, available: false }
      return info unless File.exist?(path)

      info[:available] = true
      File.foreach(path) do |line|
        m = line.match(/^\s{4}([a-z0-9_\-]+)\s\(([^)]+)\)\s*$/)
        next unless m

        name = m[1]
        version = m[2]
        case name
        when 'json' then info[:json] ||= version
        when 'json_pure' then info[:json_pure] ||= version
        end
      end
      info
    rescue StandardError
      info
    end

    def run_resolution_probe(stage_runner, module_dir, env)
      command = ['bundle', 'exec', 'ruby', '-e', PROBE_RUBY]

      unless stage_runner.command_available?('bundle')
        return {
          source: '',
          version: '',
          json_spec: '',
          json_pure_spec: '',
          load_error: 'bundle command not available',
          exit_code: nil,
          duration_seconds: 0,
          command_display: nil
        }
      end

      stage = stage_runner.run_stage('json_provider_probe', command, module_dir, env)

      source = ''
      version = ''
      json_spec = ''
      json_pure_spec = ''
      load_error = nil
      stage.output.to_s.each_line do |line|
        case line
        when /^JSON_PROVIDER_SOURCE=(.*)$/ then source = Regexp.last_match(1).strip
        when /^JSON_PROVIDER_VERSION=(.*)$/ then version = Regexp.last_match(1).strip
        when /^JSON_PROVIDER_JSON_SPEC=(.*)$/ then json_spec = Regexp.last_match(1).strip
        when /^JSON_PROVIDER_JSON_PURE_SPEC=(.*)$/ then json_pure_spec = Regexp.last_match(1).strip
        when /^JSON_PROVIDER_LOAD_ERROR=(.*)$/ then load_error = Regexp.last_match(1).strip
        end
      end

      {
        source: source,
        version: version,
        json_spec: json_spec,
        json_pure_spec: json_pure_spec,
        load_error: load_error,
        exit_code: stage.exit_code,
        duration_seconds: stage.duration_seconds,
        command_display: stage.command
      }
    end

    def classify_provider(probe_info, lock_info)
      source = probe_info[:source].to_s
      return ['json_pure', probe_info[:json_pure_spec]] unless probe_info[:json_pure_spec].to_s.empty?
      return ['json', probe_info[:json_spec]] unless probe_info[:json_spec].to_s.empty?

      if source.include?('/gems/json_pure-')
        return ['json_pure', "json_pure@#{lock_info[:json_pure] || extract_version_from_path(source, 'json_pure')}"]
      end
      if source.include?('/gems/json-')
        return ['json', "json@#{lock_info[:json] || extract_version_from_path(source, 'json')}"]
      end

      if lock_info[:json_pure] && !lock_info[:json]
        return ['json_pure', "json_pure@#{lock_info[:json_pure]}"]
      end
      if lock_info[:json] && !lock_info[:json_pure]
        return ['json', "json@#{lock_info[:json]}"]
      end

      ['unknown', '']
    end

    def extract_version_from_path(path, gem_name)
      m = path.match(%r{/gems/#{Regexp.escape(gem_name)}-([^/]+)/})
      m ? m[1] : ''
    end

    def build_summary(provider, provider_gem, probe_info, lock_info, lockfile_path, enforcement: nil)
      detection_method = if provider != 'unknown' && (!probe_info[:json_spec].to_s.empty? || !probe_info[:json_pure_spec].to_s.empty?)
                           'bundle_resolution'
                         elsif lock_info[:available]
                           'gemfile_lock_inference'
                         else
                           'unknown'
                         end

      parts = [
        "json_provider=#{provider}",
        "json_provider_gem=#{provider_gem.empty? ? 'unknown' : provider_gem}",
        "gemfile_json=#{lock_info[:json] || 'absent'}",
        "gemfile_json_pure=#{lock_info[:json_pure] || 'absent'}",
        "json_runtime_version=#{probe_info[:version].to_s.empty? ? 'unknown' : probe_info[:version]}",
        "gemfile_lock=#{File.basename(lockfile_path)}",
        "detection_method=#{detection_method}",
        "enforcement=#{enforcement || 'n/a'}"
      ]

      unless probe_info[:source].to_s.empty?
        parts << "json_source=#{probe_info[:source]}"
      end
      unless probe_info[:load_error].to_s.empty?
        parts << "json_load_error=#{probe_info[:load_error]}"
      end

      parts.join(' ')
    end
  end
end