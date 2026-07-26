"""MCP transport for the canonical mobility-toolkit service envelope.

This module remains importable without the optional FastMCP dependency so
schema-parity tests and Python clients do not need to install the MCP extra.
Running it as a server still requires FastMCP.
"""

from __future__ import annotations

import sys
from typing import Any, Dict

from mobility_toolkit.services import (
    default_service_catalog,
    execute_service_payload,
)

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover - exercised only without the optional extra
    FastMCP = None


def service(request: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the same versioned ServiceRequest used by Python and the CLI."""

    return execute_service_payload(request)


def service_catalog() -> Dict[str, Any]:
    """Return exactness, certificate, input, backend, and cache capabilities."""

    return default_service_catalog()


if FastMCP is not None:
    mcp = FastMCP("mobility-toolkit")
    mcp.tool()(service)
    mcp.tool()(service_catalog)
else:
    mcp = None


def main() -> None:
    if mcp is None:
        print(
            "Error: the optional FastMCP dependency is required to run the MCP server.",
            file=sys.stderr,
        )
        print('Install it with: pip install "mobility-toolkit[mcp]"', file=sys.stderr)
        raise SystemExit(1)
    mcp.run()


if __name__ == "__main__":
    main()


__all__ = ["main", "mcp", "service", "service_catalog"]
