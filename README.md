# NornFlow

[![CI](https://github.com/theandrelima/nornflow/actions/workflows/ci.yml/badge.svg)](https://github.com/theandrelima/nornflow/actions/workflows/ci.yml)
![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
[![License](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](https://opensource.org/licenses/GPL-3.0)
[![PyPI version](https://badge.fury.io/py/nornflow.svg)](https://badge.fury.io/py/nornflow)
[![Linter: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Installer: uv](https://img.shields.io/badge/installer-uv-blue)](https://github.com/astral-sh/uv)


> ***NornFlow is still in the prototype phase.***

NornFlow leverages the power of [Nornir](https://github.com/nornir-automation/nornir), a Python framework for network automation, to execute tasks on network devices. 

NornFlow serves two main purposes:
- a CLI-wrapper around Nornir, allowing users to invoke the execution of individual Nornir tasks.
- an Ansible-like workflow automation tool that enables users to build and execute complex workflows through YAML files (or programmatically through its API).


## Why Use NornFlow?

NornFlow provides benefits that make it a compelling choice for network automation for both developers and non-developers alike:

💪 **Real power for developers**: Since NornFlow is built on Nornir, developers can deliver network automation directly in Python by writing Nornir tasks as straightforward Python functions. This eliminates the need for convoluted boilerplate code to create new *'plugins'*.

👍 **Simplicity for end-users**: Engineers who are familiar with Ansible, but not as proficient in Python and network automation development, will find NornFlow’s user experience familiar and accessible. End-users can trigger and define their network automation workflows using intuitive YAML files, much like Ansible playbooks.


For installation and usage, see '*Getting Started*'.

## Quick Start
- [Getting Started](https://github.com/theandrelima/nornflow/tree/main/docs/getting_started.md) 🏁
- [Settings](https://github.com/theandrelima/nornflow/tree/main/docs/nornflow_settings.md) ⚙
- [Nonrflow & Workflows](https://github.com/theandrelima/nornflow/tree/main/docs/nornflow_and_workflows.md) 🆒
- [How to Write Workflows](https://github.com/theandrelima/nornflow/tree/main/docs/how_to_write_workflows.md) ✅
- [Feature Roadmap](https://github.com/theandrelima/nornflow/tree/main/docs/feature_roadmap.md) 🗺️