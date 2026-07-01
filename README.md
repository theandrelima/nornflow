# NornFlow

<p align="center">
  <img src="https://raw.githubusercontent.com/theandrelima/nornflow/main/img/nox.png" alt="Nox, the NornFlow mascot." width="220">
</p>

[![CI](https://github.com/theandrelima/nornflow/actions/workflows/ci.yml/badge.svg)](https://github.com/theandrelima/nornflow/actions/workflows/ci.yml)
![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/nornflow.svg)](https://badge.fury.io/py/nornflow)
[![Linter: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Installer: uv](https://img.shields.io/badge/installer-uv-blue)](https://github.com/astral-sh/uv)

## What is NornFlow?
NornFlow is a lightweight workflow orchestration framework built on top of [Nornir](https://github.com/nornir-automation/nornir), bringing structure and predictability to network automation projects.

NornFlow bridges the gap between development and operations teams by providing:

- A **structured workflow system** for organizing Nornir tasks into reusable automation flows
- A **declarative YAML interface** for defining complex automation sequences
- A **command-line interface** for running individual Nornir tasks or complete workflows
- A **variable system** with multi-level precedence for flexible customization

## Why Use NornFlow?

NornFlow promotes collaboration between developers and network engineers:

⚡️ **Unlimited Power for Developers**: Write automation logic as pure Python functions with Nornir's task interface. No boilerplate, just clean Python code.

🚀 **Productivity for Operators**: Define and run workflows with familiar YAML syntax, enabling network engineers to be productive regardless of their Python programming background.

🔧 **Advanced Automation Capabilities**: Extends Nornir with powerful features beyond vanilla capabilities, including:
- Multi-level variable system with precedence (environment, global, domain, workflow, CLI, runtime)
- Rich Jinja2 filters for advanced templating and data manipulation
- Hooks system for extending task behavior without modifying task code
- Flexible failure strategies (skip-failed, fail-fast, run-all) for robust error handling

🧩 **Project-friendly**: Brings predictable structure to Nornir projects with:
- Standardized directory organization
- Consistent workflow definition patterns
- Clear separation between tasks, workflows, and inventory


## Documentation

- [Quick Start Guide](https://github.com/theandrelima/nornflow/blob/main/docs/quick_start.md) - Get up and running fast
- [Core Concepts](https://github.com/theandrelima/nornflow/blob/main/docs/core_concepts.md) - Learn how NornFlow works
- [Variables Basics](https://github.com/theandrelima/nornflow/blob/main/docs/variables_basics.md) - Understand NornFlow's variable system
- [NornFlow Settings](https://github.com/theandrelima/nornflow/blob/main/docs/nornflow_settings.md) - Configure your NornFlow environment
- [Jinja2 Filters](https://github.com/theandrelima/nornflow/blob/main/docs/jinja2_filters.md) - Advanced template manipulation
- [Hooks Guide](https://github.com/theandrelima/nornflow/blob/main/docs/hooks_guide.md) - Extend task behavior with custom hooks
- [API Reference](https://github.com/theandrelima/nornflow/blob/main/docs/api_reference.md) - For developers extending NornFlow
- [Testing Guide](tests/README.md) - Test tiers, CI defaults, and maintainer cEOS lab integration tests
