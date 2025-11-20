#!/usr/bin/env python3
"""Run all example scripts and report results.

This script auto-discovers all Python example files in the examples/ directory,
runs them sequentially, and reports success or failure. It stops on the first
failure (fail-fast behavior).
"""

import subprocess
import sys
from pathlib import Path


def find_examples(examples_dir: Path) -> list[Path]:
    """Find all example Python files, sorted by name.

    Args:
        examples_dir: Path to the examples directory

    Returns:
        Sorted list of example file paths
    """
    # Find all .py files, exclude __init__.py
    examples = [f for f in examples_dir.glob("*.py") if f.name != "__init__.py"]
    return sorted(examples)


def run_example(example_path: Path) -> bool:
    """Run a single example script.

    Args:
        example_path: Path to the example script

    Returns:
        True if example succeeded, False otherwise
    """
    print(f"Running: {example_path.name}...", flush=True)

    try:
        result = subprocess.run(
            [sys.executable, str(example_path)],
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout per example
        )

        if result.returncode == 0:
            print(f"{example_path.name} passed\n")
            # Print output for visibility
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"✗ {example_path.name} FAILED")
            print(f"Exit code: {result.returncode}")
            if result.stdout:
                print("STDOUT:")
                print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print(f"✗ {example_path.name} TIMED OUT (>60s)")
        return False
    except Exception as e:
        print(f"✗ {example_path.name} ERROR: {e}")
        return False


def main() -> int:
    """Main entry point.

    Returns:
        0 if all examples passed, 1 if any failed
    """
    # Find project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    examples_dir = project_root / "examples"

    if not examples_dir.exists():
        print(f"Error: Examples directory not found: {examples_dir}")
        return 1

    # Discover examples
    examples = find_examples(examples_dir)

    if not examples:
        print(f"Warning: No example files found in {examples_dir}")
        return 0

    print(f"Found {len(examples)} example(s) to run\n")
    print("=" * 60)

    # Run each example sequentially
    passed = []
    for example in examples:
        if run_example(example):
            passed.append(example)
        else:
            # Fail-fast: stop on first failure
            print("=" * 60)
            print(f"\nFAILED after {len(passed)}/{len(examples)} examples")
            print(f"Failed example: {example.name}\n")
            return 1

    # All passed
    print("=" * 60)
    print(f"\nAll {len(examples)} example(s) passed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
