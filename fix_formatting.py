#!/usr/bin/env python3
"""
Script to fix all formatting issues to match CI environment expectations.
"""

import subprocess
import sys
import os


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd or os.getcwd()
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def main():
    """Main function to fix formatting."""
    print("🔧 Fixing all formatting issues for CI environment...")

    # Run black formatter
    print("📝 Running black formatter...")
    success, stdout, stderr = run_command(
        "python -m black . --line-length 88 --exclude='venv|env|.venv|.env|node_modules|.git'"
    )

    if success:
        print("✅ Black formatting completed")
        if stdout.strip():
            print(f"Output: {stdout}")
    else:
        print(f"❌ Black formatting failed: {stderr}")
        return False

    # Run isort
    print("📝 Running isort...")
    success, stdout, stderr = run_command(
        "python -m isort . --skip-glob='venv/*' --skip-glob='env/*' --skip-glob='.venv/*' --skip-glob='.env/*'"
    )

    if success:
        print("✅ Import sorting completed")
        if stdout.strip():
            print(f"Output: {stdout}")
    else:
        print(f"❌ Import sorting failed: {stderr}")
        return False

    # Verify formatting
    print("🔍 Verifying formatting...")
    success, stdout, stderr = run_command(
        "python -m black . --check --line-length 88 --exclude='venv|env|.venv|.env|node_modules|.git'"
    )

    if success:
        print("✅ All files are properly formatted!")
        print(f"Result: {stdout}")
        return True
    else:
        print(f"❌ Some files still need formatting: {stderr}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
