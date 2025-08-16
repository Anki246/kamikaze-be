#!/usr/bin/env python3
"""
Force exact CI formatting - applies the EXACT changes CI wants
"""

import os
import subprocess
import sys


def apply_exact_ci_formatting():
    """Apply the exact formatting changes that CI expects"""

    print("🔧 Applying EXACT CI formatting requirements...")

    # 1. Fix binance_fastmcp_server.py - move pydantic import AFTER FastMCP comment
    binance_file = "src/mcp_servers/binance_fastmcp_server.py"
    print(f"📝 Fixing {binance_file}...")

    with open(binance_file, "r") as f:
        content = f.read()

    # Replace the import section with exact CI format
    old_imports = """import aiohttp
import numpy as np
from pydantic import BaseModel, Field

# FastMCP imports
from fastmcp import FastMCP"""

    new_imports = """import aiohttp
import numpy as np

# FastMCP imports
from fastmcp import FastMCP
from pydantic import BaseModel, Field"""

    if old_imports in content:
        content = content.replace(old_imports, new_imports)
        with open(binance_file, "w") as f:
            f.write(content)
        print(f"✅ Fixed {binance_file}")
    else:
        print(f"⚠️  Pattern not found in {binance_file}")

    # 2. Fix fastmcp_client.py - move transports import AFTER Client import
    client_file = "src/agents/fluxtrader/fastmcp_client.py"
    print(f"📝 Fixing {client_file}...")

    with open(client_file, "r") as f:
        content = f.read()

    # Replace the import section with exact CI format
    old_imports = """from fastmcp.client.transports import StdioTransport

# FastMCP imports
from fastmcp import Client"""

    new_imports = """# FastMCP imports
from fastmcp import Client
from fastmcp.client.transports import StdioTransport"""

    if old_imports in content:
        content = content.replace(old_imports, new_imports)
        with open(client_file, "w") as f:
            f.write(content)
        print(f"✅ Fixed {client_file}")
    else:
        print(f"⚠️  Pattern not found in {client_file}")

    print("✅ Applied exact CI formatting requirements")


def verify_formatting():
    """Verify that formatting matches CI expectations"""
    print("🔍 Verifying formatting...")

    # Check black
    result = subprocess.run(
        ["python", "-m", "black", "--check", "--diff", "."],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("✅ Black formatting: PASSED")
    else:
        print("❌ Black formatting: FAILED")
        print(result.stdout)
        return False

    # Check isort
    result = subprocess.run(
        ["python", "-m", "isort", "--check-only", "--diff", "."],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("✅ isort import ordering: PASSED")
    else:
        print("❌ isort import ordering: FAILED")
        print(result.stdout)
        return False

    return True


if __name__ == "__main__":
    apply_exact_ci_formatting()

    if verify_formatting():
        print("🎉 All formatting checks PASSED!")
        sys.exit(0)
    else:
        print("💥 Formatting checks FAILED!")
        sys.exit(1)
