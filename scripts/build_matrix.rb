# frozen_string_literal: true

# Builds the CI matrix JSON from config/modules.json (or an override JSON string).
#
# Usage:
#   ruby scripts/build_matrix.rb                          # reads config/modules.json
#   ruby scripts/build_matrix.rb '[ {"repo":"..."} ]'    # uses inline override
#
# Outputs a single JSON object to stdout with keys:
#   unit_matrix       — array of unit test matrix entries
#   acceptance_matrix — array of acceptance test matrix entries
#   has_acceptance    — "true" or "false"

require 'json'
require 'set'

raw = (ARGV[0] || '').strip
modules = if raw.empty?
            JSON.parse(File.read('config/modules.json')).fetch('modules', [])
          else
            JSON.parse(raw)
          end

# Lean-matrix filtering (Phase 2). RUN_ALL defaults to true so an unset
# environment (local dev, or the modules_json override path) includes every
# module — matching pre-Phase-2 behaviour. When RUN_ALL=false, only modules
# whose id is in INCLUDE_IDS (a JSON array) are emitted.
run_all = ENV.fetch('RUN_ALL', 'true').strip != 'false'
include_ids = nil
unless run_all
  raw_ids = ENV['INCLUDE_IDS'].to_s.strip
  include_ids = (raw_ids.empty? ? [] : JSON.parse(raw_ids)).to_set
end

unit = []
acceptance = []

modules.each do |m|
  repo = m.fetch('repo')
  ref = m.fetch('ref', 'main')
  id = m['id'] || repo.sub(%r{/$}, '').split('/').last.sub(/\.git$/, '').gsub(/[^a-zA-Z0-9_.-]+/, '-')

  next unless run_all || include_ids.include?(id)

  os = m.fetch('os', 'ubuntu-latest')
  prereqs = m.fetch('prereqs', {})

  unit << {
    'repo' => repo,
    'ref' => ref,
    'id' => id,
    'os' => os,
    'prereqs' => prereqs,
    'lane' => 'unit',
    'target' => 'unit'
  }

  acceptance_cfg = m['acceptance']
  next unless acceptance_cfg.is_a?(Hash) && acceptance_cfg['enabled']

  targets = acceptance_cfg['targets']
  next unless targets.is_a?(Array)

  targets.each do |target|
    next unless target.is_a?(Hash)

    target_name = target.fetch('name')
    target_id = target_name.gsub(/[^a-zA-Z0-9_.-]+/, '-')
    acceptance << {
      'repo' => repo,
      'ref' => ref,
      'id' => id,
      'os' => 'ubuntu-latest',
      'prereqs' => prereqs,
      'lane' => 'acceptance',
      'target' => target_name,
      'target_id' => target_id,
      'setfile' => target.fetch('setfile'),
      'docker_mode' => target.fetch('docker_mode', 'sshd'),
      'install_puppetserver' => target.fetch('install_puppetserver', false),
      'setup_commands' => target.fetch('setup_commands', []),
      'pre_acceptance_commands' => target.fetch('pre_acceptance_commands', [])
    }
  end
end

puts JSON.generate({
  'unit_matrix' => unit,
  'acceptance_matrix' => acceptance,
  'has_acceptance' => (!acceptance.empty?).to_s
})
