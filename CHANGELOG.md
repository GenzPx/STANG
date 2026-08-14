# Changelog

All notable changes to STANG will be documented in this file.

## [Unreleased]

### Added
- Initial STANG file format (version 1).
- `STGContainer` with header, schema, block table, data blocks, and SHA-256 checksum.
- `RotationEngine` implementing circular logical rotation.
- Encoder (`stang encode`) and decoder (`stang decode`).
- Dumper plugin system with `block`, `json`, `csv`, and `raw` formats.
- CLI commands: `init`, `encode`, `decode`, `dump`, `inspect`, `rotate`, `verify`.
- Comprehensive test suite covering round-trips, integrity, and rotation.
- Documentation: README, SPEC, ARCHITECTURE, CONTRIBUTING, and full `docs/` directory.

### Changed
- N/A

### Fixed
- N/A

### Security
- N/A
