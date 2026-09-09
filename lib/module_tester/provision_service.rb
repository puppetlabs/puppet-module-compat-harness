# frozen_string_literal: true

require 'net/http'
require 'uri'
require 'json'
require 'yaml'

module ModuleTester
  # Thin client for Puppet DevX's GCP VM provision service
  # (docs/vm-based-acceptance-testing.md §2.1-2.2). No credentials are
  # required — authorization is entirely server-side, keyed off the calling
  # GitHub Actions run URL. Deliberately not built on puppet_litmus/Bolt (see
  # the design doc §3.3): this is a ~100-line POST/DELETE client against a
  # published contract, not a dependency on the Litmus toolchain.
  class ProvisionService
    DEFAULT_SERVICE_URL = 'https://facade-release-6f3kfepqcq-ew.a.run.app/v1/provision'

    # ip/user/password: SSH connection details for the *litmus* user the
    # service creates — ephemeral, randomized per request, non-root with
    # NOPASSWD sudo (see vm.rb#prepare_vm, which uses these once to install
    # an ephemeral root key and then discards the password entirely).
    ProvisionedHost = Struct.new(:ip, :user, :password, :platform, :uuid, keyword_init: true)

    def initialize(service_url: ENV.fetch('PUPPET_CORE_VM_SERVICE_URL', DEFAULT_SERVICE_URL))
      @service_url = service_url
    end

    # Requests one VM for the given GCP image. Returns [ProvisionedHost, StageResult]
    # — matching the [value, StageResult] convention used throughout this
    # codebase (see Docker#build_puppet_core_image) so callers can push the
    # stage and short-circuit consistently. `run_url` must be the calling
    # GitHub Actions run's API URL (the sole authorization mechanism).
    def provision(image, run_url:)
      started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
      body = { url: run_url, VMs: [{ cloud: nil, region: nil, zone: nil, images: [image] }] }.to_json
      response = post(body)
      elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - started

      unless response.is_a?(Net::HTTPSuccess)
        return [nil, failed_stage('provision_vm', "provisioning request failed: HTTP #{response.code} #{response.body}", elapsed)]
      end

      inventory = YAML.safe_load(response.body)
      target = extract_target(inventory)
      return [nil, failed_stage('provision_vm', 'no target found in returned inventory', elapsed)] unless target

      ssh_cfg = target.fetch('config', {}).fetch('ssh', {})
      host = ProvisionedHost.new(
        ip: target.fetch('uri'),
        user: ssh_cfg.fetch('user', ''),
        password: ssh_cfg.fetch('password', ''),
        platform: target.dig('facts', 'platform'),
        uuid: target.dig('facts', 'uuid')
      )

      stage = StageResult.new(
        name: 'provision_vm',
        status: 'passed',
        command: nil,
        exit_code: 0,
        duration_seconds: elapsed.round(2),
        output: "Provisioned #{host.ip} platform=#{host.platform} uuid=#{host.uuid}"
      )
      [host, stage]
    rescue StandardError => e
      [nil, failed_stage('provision_vm', "provisioning request raised: #{e.message}", 0)]
    end

    # Best-effort teardown. Returns a StageResult but a non-passed status here
    # must NOT be added to the classifier's harness-error stage list — a
    # failed teardown falls back to the service's own run-status reaper and
    # 3-hour VM TTL (design doc §9), not a harness/compatibility concern.
    def teardown(uuid)
      return nil if uuid.to_s.strip.empty?

      started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
      body = { uuid: uuid }.to_json
      response = delete(body)
      elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - started

      if response.is_a?(Net::HTTPSuccess)
        StageResult.new(
          name: 'teardown_vm', status: 'passed', command: nil, exit_code: 0,
          duration_seconds: elapsed.round(2), output: "Teardown succeeded for #{uuid}"
        )
      else
        StageResult.new(
          name: 'teardown_vm', status: 'failed', command: nil, exit_code: 1,
          duration_seconds: elapsed.round(2),
          output: "Teardown request returned HTTP #{response.code} — relying on the service's " \
                  "run-status reaper / 3h TTL as backstop (see docs/vm-based-acceptance-testing.md §9)"
        )
      end
    rescue StandardError => e
      StageResult.new(
        name: 'teardown_vm', status: 'failed', command: nil, exit_code: 1,
        duration_seconds: 0, output: "Teardown request raised: #{e.message} — relying on service backstops"
      )
    end

    private

    def failed_stage(name, message, elapsed)
      StageResult.new(name: name, status: 'failed', command: nil, exit_code: 1, duration_seconds: elapsed.round(2), output: message)
    end

    def extract_target(inventory)
      (inventory || {}).fetch('groups', []).each do |group|
        group.fetch('targets', []).each { |t| return t }
      end
      nil
    end

    def post(body)
      request(Net::HTTP::Post, body)
    end

    def delete(body)
      request(Net::HTTP::Delete, body)
    end

    def request(http_method_class, body)
      uri = URI.parse(@service_url)
      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = uri.scheme == 'https'
      http.read_timeout = 300 # matches the service's own client-side timeout
      req = http_method_class.new(uri, { 'Accept' => 'application/json', 'Content-Type' => 'application/json' })
      req.body = body
      http.request(req)
    end
  end
end
