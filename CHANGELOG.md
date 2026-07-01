# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-07-01

First stable release. NornFlow now follows Semantic Versioning; the public
API and CLI surface described in the documentation are considered stable.

### Added
- Declarative YAML workflow system (`workflow:` / `tasks:`) built on Nornir.
- CLI: `init`, `run`, `show`, and `validate` commands.
- Catalog system with namespace isolation and tier priority
  (builtin > local > package) for six resource types
  (tasks, filters, workflows, blueprints, j2-filters, hooks).
- Packages system: installed Python packages contribute resources to catalogs.
- Six-level variable precedence with device-isolated context and the `host.*` namespace.
- Jinja2 templating service with builtin and namespaced custom filters.
- Hook system with builtin hooks: `if`, `store_as`, `single`, `shush`.
- Blueprints with recursive expansion and circular-dependency detection.
- Failure strategies: `skip-failed`, `fail-fast`, `run-all`.
- Output masking and redaction of sensitive values in CLI output and logs.
- Documentation set under `docs/` and a maintainer testing guide under `tests/`.

### Pre-1.0 history
Versions 0.0.2 (2025-02-23) through 0.9.1 (2026-06-14) were pre-release and are
not individually documented here. See the git tags for details.

[Unreleased]: https://github.com/theandrelima/nornflow/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/theandrelima/nornflow/releases/tag/v1.0.0
