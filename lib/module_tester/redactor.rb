# frozen_string_literal: true

require 'cgi'

module ModuleTester
  module Redactor
    module_function

    # `extra_secrets` lets a caller redact ad-hoc runtime values that aren't
    # available via ENV — e.g. the VM provision service's per-request litmus
    # password (lib/module_tester/vm.rb), which is deliberately kept out of
    # any env hash entirely (see vm.rb) but is passed here too as
    # defense-in-depth against it appearing in command error output.
    def redact_sensitive(text, extra_secrets = [])
      value = text.to_s
      secrets = []

      api_key = ENV.fetch('PUPPET_CORE_API_KEY', '').to_s.strip
      secrets << api_key unless api_key.empty?

      password = ENV.fetch('PASSWORD', '').to_s.strip
      secrets << password unless password.empty?

      env_credential = ENV.fetch('BUNDLE_RUBYGEMS___PUPPETCORE__PUPPET__COM', '').to_s.strip
      secrets << env_credential unless env_credential.empty?

      Array(extra_secrets).each { |s| secrets << s.to_s.strip unless s.to_s.strip.empty? }

      secrets.uniq.each do |secret|
        value = value.gsub(secret, '[REDACTED]')
        escaped = CGI.escape(secret)
        value = value.gsub(escaped, '[REDACTED]') unless escaped.empty?
      end

      # Catch credentials embedded in shell snippets and wrapped YAML strings.
      value = value.gsub(/(password\s*=\s*)(?:\\\s*\n\s*)?[^\s'"\\]+/i, '\\1[REDACTED]')
      value = value.gsub(/(login\s+forge-key\s+password\s+)(?:\\\s*\n\s*)?[^\s'"\\]+/i, '\\1[REDACTED]')
      value = value.gsub(/forge-key:[^\s'"@]+/, 'forge-key:[REDACTED]')
      value = value.gsub(/license-id:[^\s'"@]+/, 'license-id:[REDACTED]')
      value
    end
  end
end
