"""Run the private Seller OS MCP server over standard input/output."""

from __future__ import annotations

from .server import create_server


def main() -> None:
    """Start the MCP stdio transport without opening a network listener."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
