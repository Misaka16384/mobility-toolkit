"""Thin JSON transport for the unified finite-boundary service."""

from __future__ import annotations

import json
import sys

import mobility_toolkit.services as services


def run(payload):
    """Pass one canonical request to the shared service executor."""

    return services.execute_service_payload(payload)


def main():
    response = run(json.load(sys.stdin))
    json.dump(response, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
