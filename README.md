# 🚀 Smart Test Runner

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.7+">
  <img src="https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-brightgreen" alt="GitHub Actions">
  <img src="https://img.shields.io/badge/test%20framework-pytest-orange" alt="pytest">
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black">
</p>

## 🧠 What is this?

**Stop wasting time running your entire test suite!** 

This intelligent test runner analyzes your Python codebase's dependency graph to determine exactly which tests need to run based on what files you've changed. It's like having a smart assistant that knows your codebase inside out.

### ✨ Key Features

- **🎯 Surgical Precision**: Only runs tests affected by your changes
- **🔍 Deep Dependency Analysis**: Tracks imports, relative imports, and transitive dependencies
- **⚡ Lightning Fast**: Dramatically reduces CI/CD time by skipping irrelevant tests
- **🧩 Zero Configuration**: Works out of the box with any Python project structure
- **📊 Dependency Visualization**: Debug mode shows the full dependency graph

## 🎬 How It Works

```mermaid
graph LR
    A[Changed Files] --> B[Dependency Analyzer]
    B --> C[Build Import Graph]
    C --> D[Find Affected Modules]
    D --> E[Identify Related Tests]
    E --> F[Run Only Those Tests]
    
    style A fill:#ff6b6b
    style F fill:#51cf66
```

The script performs a sophisticated analysis:

1. **🔎 Scans** your entire project for Python files
2. **🕸️ Maps** all import relationships (including dynamic and relative imports)
3. **📈 Builds** both forward and reverse dependency graphs
4. **🎯 Identifies** which tests cover which modules
5. **⚡ Executes** only the tests that could be affected by your changes

## 🚀 Usage

### In GitHub Actions

```yaml
name: Smart Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Important for git diff
      
      - name: Run affected tests
        run: python .github/scripts/full_dependency_test_runner.py
```

### Locally

```bash
# Run tests for current changes
python .github/scripts/full_dependency_test_runner.py

# Enable debug mode to see dependency graph
DEBUG=1 python .github/scripts/full_dependency_test_runner.py
```

## 🔧 Configuration

The script intelligently handles:

- **Test Detection**: Recognizes `test_*.py`, `*_test.py`, and files in `test/` or `tests/` directories
- **Import Resolution**: Handles absolute, relative, and dynamic imports
- **External Packages**: Distinguishes between project code and third-party dependencies
- **Virtual Environments**: Automatically skips `venv`, `.venv`, and other build directories

## 📊 Example Output

```
Starting full dependency analysis...

Changed files: ['src/models/user.py']

=== Dependency Analysis ===

Changed file: src/models/user.py
  Dependencies: {'src/utils/validators.py', 'src/db/connection.py'}
  Files that depend on this: {'src/api/endpoints.py', 'src/services/user_service.py'}
  Direct test coverage: {'tests/test_user.py', 'tests/test_api.py'}

Found 4 affected tests:
  - tests/test_user.py
  - tests/test_api.py
  - tests/test_user_service.py
  - tests/integration/test_user_flow.py

Running affected tests...
```

## 🎯 Real-World Impact

Imagine a project with 500 test files that takes 30 minutes to run:

- **Traditional CI**: Every push runs all 500 tests = 30 minutes ⏰
- **Smart Test Runner**: Average push affects 20 tests = 1.2 minutes 🚀

That's a **96% reduction** in test time! 

## 🤝 Contributing

Found a bug? Have a feature idea? PRs welcome! The code is designed to be:

- **Readable**: Clear variable names and comprehensive comments
- **Extensible**: Easy to add new import detection patterns
- **Robust**: Handles edge cases and parsing errors gracefully

## 📝 License

MIT - Use it, love it, contribute to it!

---

<p align="center">
  Made with ❤️ for developers who value their time
</p>
