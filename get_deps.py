# .github/scripts/full_dependency_test_runner.py
import ast
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

try:
    from importlib import metadata
except ImportError:
    # Fallback for older Python versions
    pass  # type: ignore


class FullDependencyAnalyzer:
    def __init__(self, project_root: Path = Path(".")):
        self.project_root = project_root
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)
        self.module_to_tests: Dict[str, Set[str]] = defaultdict(set)
        self._python_files: Set[str] = set()

        # Cache installed package names for performance
        self._installed_packages: Set[str] = self._get_installed_packages()

        # Build the complete dependency graph
        self._scan_project()
        self._build_dependency_graph()
        self._map_tests_to_modules()

    def _get_installed_packages(self) -> Set[str]:
        """Get a set of all installed package names using importlib.metadata."""
        try:
            # Get all installed distributions and extract their names
            return {dist.metadata["name"].lower() for dist in metadata.distributions()}
        except Exception:
            # Fallback to empty set if metadata access fails
            return set()

    def _scan_project(self):
        """Scan project for all Python files."""
        for py_file in self.project_root.rglob("*.py"):
            # Skip virtual environments and build directories
            if any(skip in str(py_file) for skip in ["venv", ".venv", "build", "dist", ".git", "__pycache__"]):
                continue
            self._python_files.add(str(py_file.relative_to(self.project_root)))

    def _build_dependency_graph(self):
        """Build complete forward and reverse dependency graphs."""
        for py_file in self._python_files:
            dependencies = self._extract_dependencies(Path(py_file))
            self.dependency_graph[py_file] = dependencies

            # Build reverse graph (who depends on this file)
            for dep in dependencies:
                self.reverse_graph[dep].add(py_file)

    def _extract_dependencies(self, file_path: Path) -> Set[str]:
        """Extract all dependencies from a Python file."""
        dependencies = set()
        try:
            full_path = self.project_root / file_path
            with open(full_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        deps = self._resolve_import(alias.name, file_path)
                        dependencies.update(deps)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        if node.level > 0:  # Relative import
                            deps = self._resolve_relative_import(node.module, node.level, file_path)
                        else:  # Absolute import
                            deps = self._resolve_import(node.module, file_path)
                        dependencies.update(deps)
                    elif node.level > 0:  # from . import something
                        deps = self._resolve_relative_import("", node.level, file_path)
                        dependencies.update(deps)

                # Also check for dynamic imports
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in ["__import__", "importlib.import_module"]:
                        # Handle dynamic imports if needed
                        pass

        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")

        return dependencies

    def _resolve_import(self, module_name: str, from_file: Path) -> Set[str]:
        """Resolve an absolute import to file paths."""
        resolved = set()
        parts = module_name.split(".")

        # Check if it's a standard library or third-party module
        if self._is_external_module(parts[0]):
            return resolved

        # Try different combinations
        for i in range(len(parts), 0, -1):
            module_parts = parts[:i]

            # Try as a module file
            module_path = "/".join(module_parts) + ".py"
            if module_path in self._python_files:
                resolved.add(module_path)

            # Try as a package
            init_path = "/".join(module_parts) + "/__init__.py"
            if init_path in self._python_files:
                resolved.add(init_path)

                # If we're importing from a package, include all specified submodules
                if i < len(parts):
                    submodule_path = "/".join(parts[: i + 1]) + ".py"
                    if submodule_path in self._python_files:
                        resolved.add(submodule_path)

        return resolved

    def _resolve_relative_import(self, module_name: str, level: int, from_file: Path) -> Set[str]:
        """Resolve relative imports."""
        resolved = set()

        # Get the package containing from_file
        current_path = from_file.parent

        # Go up 'level' directories
        for _ in range(level - 1):
            current_path = current_path.parent

        if module_name:
            # from ..module import something
            target_path = current_path / module_name.replace(".", "/")

            # Check for module.py
            module_file = str(target_path) + ".py"
            if module_file in self._python_files:
                resolved.add(module_file)

            # Check for module/__init__.py
            init_file = str(target_path / "__init__.py")
            if init_file in self._python_files:
                resolved.add(init_file)
        else:
            # from .. import something
            init_file = str(current_path / "__init__.py")
            if init_file in self._python_files:
                resolved.add(init_file)

        return resolved

    def _is_external_module(self, module_name: str) -> bool:
        """Check if a module is external (stdlib or third-party)."""
        # Use sys.stdlib_module_names to check for standard library modules (Python 3.10+)
        if module_name in sys.stdlib_module_names:
            return True

        # Check if it's an installed third-party package
        if module_name.lower() in self._installed_packages:
            return True

        # Check if it's a file in our project
        if any(f.startswith(module_name) for f in self._python_files):
            return False

        # Assume it's external if not found in project
        return True

    def _map_tests_to_modules(self):
        """Map test files to the modules they test."""
        test_files = [f for f in self._python_files if self._is_test_file(f)]

        for test_file in test_files:
            # Get all dependencies of this test file (recursively)
            all_deps = self._get_all_dependencies(test_file)

            for dep in all_deps:
                if not self._is_test_file(dep):
                    self.module_to_tests[dep].add(test_file)

    def _is_test_file(self, file_path: str) -> bool:
        """Check if a file is a test file."""
        return "test_" in file_path or "_test.py" in file_path or "/tests/" in file_path or "/test/" in file_path

    def _get_all_dependencies(self, file_path: str, visited: Set[str] = None) -> Set[str]:
        """Recursively get all dependencies of a file."""
        if visited is None:
            visited = set()

        if file_path in visited:
            return set()

        visited.add(file_path)
        all_deps = set()

        # Get direct dependencies
        direct_deps = self.dependency_graph.get(file_path, set())
        all_deps.update(direct_deps)

        # Recursively get dependencies of dependencies
        for dep in direct_deps:
            all_deps.update(self._get_all_dependencies(dep, visited))

        return all_deps

    def _get_all_dependents(self, file_path: str, visited: Set[str] = None) -> Set[str]:
        """Recursively get all files that depend on this file."""
        if visited is None:
            visited = set()

        if file_path in visited:
            return set()

        visited.add(file_path)
        all_dependents = set()

        # Get direct dependents
        direct_dependents = self.reverse_graph.get(file_path, set())
        all_dependents.update(direct_dependents)

        # Recursively get dependents of dependents
        for dep in direct_dependents:
            all_dependents.update(self._get_all_dependents(dep, visited))

        return all_dependents

    def get_affected_tests(self, changed_files: List[str]) -> Set[str]:
        """Get all tests affected by the changed files."""
        affected_tests = set()

        for changed_file in changed_files:
            # If it's a test file itself, include it
            if self._is_test_file(changed_file):
                affected_tests.add(changed_file)

            # Get all files that depend on this changed file (transitively)
            all_dependents = self._get_all_dependents(changed_file)

            # Filter for test files
            test_dependents = {f for f in all_dependents if self._is_test_file(f)}
            affected_tests.update(test_dependents)

            # Also check module_to_tests mapping
            if changed_file in self.module_to_tests:
                affected_tests.update(self.module_to_tests[changed_file])

        return affected_tests

    def print_dependency_info(self, changed_files: List[str]):
        """Print detailed dependency information for debugging."""
        print("\n=== Dependency Analysis ===")
        for changed_file in changed_files:
            print(f"\nChanged file: {changed_file}")

            # Show what this file depends on
            deps = self.dependency_graph.get(changed_file, set())
            if deps:
                print(f"  Dependencies: {deps}")

            # Show what depends on this file
            dependents = self._get_all_dependents(changed_file)
            if dependents:
                print(f"  Files that depend on this: {dependents}")

            # Show affected tests
            tests = self.module_to_tests.get(changed_file, set())
            if tests:
                print(f"  Direct test coverage: {tests}")


def get_changed_files() -> List[str]:
    """Get list of changed Python files in the PR."""
    # if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
    #     base_ref = os.environ.get("GITHUB_BASE_REF", "main")
    #     cmd = f"git diff --name-only origin/{base_ref}...HEAD"
    # else:
    #     cmd = "git diff --name-only HEAD~1...HEAD"

    # Use same git command as GitHub Actions workflow
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        cmd = "git diff --name-only origin/main...HEAD"
    else:
        cmd = "git diff --name-only origin/main"

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Git command failed: {result.stderr}")
        return []

    changed_files = result.stdout.strip().split("\n")
    # Filter for Python files that exist
    return [f for f in changed_files if f.endswith(".py") and os.path.exists(f)]


def main():
    print("Starting full dependency analysis...")

    # Get changed files
    changed_files = get_changed_files()
    if not changed_files:
        print("No Python files changed.")
        sys.exit(0)

    print(f"\nChanged files: {changed_files}")

    # Analyze dependencies
    analyzer = FullDependencyAnalyzer()

    # Print dependency information for debugging
    if os.environ.get("DEBUG"):
        analyzer.print_dependency_info(changed_files)

    # Get affected tests
    affected_tests = analyzer.get_affected_tests(changed_files)

    if not affected_tests:
        print("\nNo tests are affected by these changes.")
        print("This might indicate missing test coverage.")
        sys.exit(0)

    print(f"\nFound {len(affected_tests)} affected tests:")
    for test in sorted(affected_tests):
        print(f"  - {test}")

    # Run the tests
    print("\nRunning affected tests...")
    cmd = ["poetry", "run", "pytest", "-v", "--tb=short", "-n", "auto"] + list(sorted(affected_tests))

    try:
        # Set timeout to 25 minutes (GitHub Actions has 30 minute timeout)
        result = subprocess.run(cmd, cwd=Path.cwd(), timeout=600)
        sys.exit(result.returncode)
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out after 25 minutes")
        sys.exit(1)
    except KeyboardInterrupt:
        print("❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
