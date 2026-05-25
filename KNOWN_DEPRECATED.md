# Known Deprecated & Archived Modules

This document lists modules that are no longer maintained, have been archived by their maintainers, or are explicitly deprecated. These modules are excluded from the active test matrix but may still be functional with current Puppet Core.

**Distinction from [KNOWN_INCOMPATIBLE.md](KNOWN_INCOMPATIBLE.md):** Modules listed here are deprecated/archived but may still work. See KNOWN_INCOMPATIBLE.md for modules that have been **tested and determined to be incompatible** with current Puppet Core.

## Deprecated & Archived Summary

| Module | Status | Date | Reason | Recommended Replacement | Notes |
|--------|--------|------|--------|------------------------|-------|
| [puppet-boolean](https://github.com/voxpupuli/puppet-boolean) | Archived | 2023-04-28 | No longer maintained by Vox Pupuli | N/A | Repository is read-only. Module provided simple boolean type support. Use Puppet's native `Boolean` data type (Puppet 6+) or alternative implementations as needed. Unit tests still pass with current Puppet Core. |
