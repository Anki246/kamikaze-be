#!/usr/bin/env python3
"""
Script to fix all formatting issues to match CI environment expectations.
Uses exact same versions as CI: black==23.3.0, isort==5.11.5
"""

import os
import subprocess
import sys


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd or os.getcwd()
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def install_exact_versions():
    """Install exact same versions as CI environment."""
    print("🔧 Installing exact CI versions...")

    # Install exact versions
    success, stdout, stderr = run_command("pip install black==23.3.0 isort==5.11.5")

    if success:
        print("✅ Installed exact CI versions")
    else:
        print(f"❌ Failed to install versions: {stderr}")
        return False

    return True


def main():
    """Main function to fix formatting."""
    print("🔧 Fixing all formatting issues for CI environment...")

    # Install exact versions first
    if not install_exact_versions():
        return False

    # Run black formatter with exact CI parameters
    print("📝 Running black formatter (exact CI parameters)...")
    success, stdout, stderr = run_command("python -m black .")

    if success:
        print("✅ Black formatting completed")
        if stdout.strip():
            print(f"Output: {stdout}")
    else:
        print(f"❌ Black formatting failed: {stderr}")
        return False

    # Run isort with exact CI parameters
    print("📝 Running isort (exact CI parameters)...")
    success, stdout, stderr = run_command("python -m isort .")

    if success:
        print("✅ Import sorting completed")
        if stdout.strip():
            print(f"Output: {stdout}")
    else:
        print(f"❌ Import sorting failed: {stderr}")
        return False

    # Verify formatting with exact CI parameters
    print("🔍 Verifying formatting (exact CI parameters)...")
    success, stdout, stderr = run_command("python -m black --check --diff .")

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
