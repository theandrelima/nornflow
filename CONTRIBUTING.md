# Contributing to NornFlow

Thank you for your interest in contributing to NornFlow! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Setting Up Your Development Environment](#setting-up-your-development-environment)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Feature Requests and Bug Reports](#feature-requests-and-bug-reports)

## Code of Conduct

Please be respectful and kind in your interactions with other contributors. We aim to foster an open and welcoming community.

## Setting Up Your Development Environment

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/theandrelima/nornflow.git
   cd nornflow
   ```

2. **Create a virtual environment with Uv**
   ```bash
   uv venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies with Uv**
   ```bash
   uv pip install -e ".[dev]"
   ```

   If you don't have Uv installed yet, you can install it with:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

## Development Workflow

1. **Create a branch for your changes**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make and test your changes locally**

3. **Commit your changes with meaningful commit messages**
   ```bash
   git commit -m "feat: add support for custom processors"
   ```
   
   Starting with `v0.1.3`, we will strive to follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

4. **Push your branch to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a pull request**

## Coding Standards

- We are not hardocre lunatics, but we will strive to adhere to [PEP 8](https://pep8.org/) for Python code style
- Use type hints for all function parameters and return values
- Maximum line length is 110 characters
- Document all functions, classes, and methods with docstrings
- Make sure to run `ruff`, `black` and `isort`.

## Testing

- All new features should include appropriate unit tests
- Run tests before submitting a PR:
  ```bash
  pytest tests/
  ```
- Aim for high test coverage on all new code

## Documentation

- Update documentation for any new features or changes to existing functionality
- Documentation is written in Markdown format in the docs directory
- Examples should be included for new functionality
- Docstrings should follow the Google style guide format

## Submitting a Pull Request

1. Ensure your PR addresses a specific issue or feature
2. Include a clear description of the changes
3. Reference any related issues
4. Make sure all tests pass
5. Update documentation as needed
6. Follow the project's code style

## Feature Requests and Bug Reports

- Use the GitHub issue tracker to report bugs or request features
- Provide detailed information about your environment when reporting bugs
- Include steps to reproduce any issues you encounter
- Ideally, provide print and/or short screen capture videos

<br><br>

**Thank you for contributing to NornFlow!** 🙏🏻