#!/usr/bin/env python3
"""Main CLI interface for tidyanki."""

import logging
import sys

from tidyapp.cli_adapter import cli_main
from tidyapp.registry import REGISTRY

# Import commands to register them
import tidyanki.commands  # noqa: F401


def main():
    """Main CLI entry point."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler(sys.stderr)]
    )
    
    # Get all registered functions and create CLI
    functions = [func_desc.function for func_desc in REGISTRY.functions]
    cli_main(functions)


if __name__ == "__main__":
    main()