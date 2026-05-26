# Known Incompatible Modules

This document lists modules that have been tested against Puppet Core and determined to be incompatible. These modules are not included in the active compatibility test suite.

## Incompatibility Summary

| Module | Puppet Core Tested | Status | Reason | Recommended Replacement | Details |
|--------|-------------------|--------|--------|------------------------|---------|
| [garethr-docker](https://github.com/garethr/garethr-docker) | 8.19.0 | Incompatible | Unmaintained module and legacy dependency graph incompatible with current Ruby/Puppet Core test toolchain | N/A | Repository is stale (last commit approximately 9 years old). Under Puppet Core 8.19.0 profile (Ruby 3.2), bootstrap resolves legacy dependencies (for example rake 10.5.0 and older beaker stack) that fail native extension build steps with `NoMethodError` in rake internals while building transitive gems (`unf`, `rainbow`). Result is persistent harness bootstrap failure and no reliable compatibility signal for modern Puppet Core. |
| [puppet-staging](https://github.com/voxpupuli/puppet-staging) | 8.17.0 | Incompatible | Deprecated by Maintainer and uses legacy test framework dependency | [puppet-archive](https://github.com/voxpupuli/puppet-archive#migrating-from-puppet-staging) | Module targets Puppet 5.5.8 - 6.x and uses deprecated `PuppetlabsSpec::PuppetInternals` helper internals in parser function specs (scope_defaults_spec.rb, staging_parse_spec.rb). Modern Puppet Core 8 test toolchain (voxpupuli-test + rspec-puppet) does not provide the PuppetlabsSpec module, resulting in NameError during unit test execution. Module maintainers would need to migrate specs to modern rspec-puppet patterns to support Puppet Core 8. |


