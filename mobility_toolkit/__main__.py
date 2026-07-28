"""Command-line transport for canonical services and explicit administration."""

from __future__ import annotations

import argparse
import json
import sys

from mobility_toolkit import __version__
from mobility_toolkit.installer import (
    ALL_TARGETS,
    run_install,
    run_interactive,
    run_self_update,
    run_status,
    run_uninstall,
)
from mobility_toolkit.registry import query_vector_db
from mobility_toolkit.services import (
    default_service_catalog,
    execute_service_payload,
    stream_service_payload,
)


class JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def _build_parser() -> JSONArgumentParser:
    parser = JSONArgumentParser(
        description=(
            "mobility_toolkit canonical service transport. Computational "
            "requests use one versioned JSON ServiceRequest."
        )
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"mobility-toolkit {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    service = subparsers.add_parser(
        "service",
        help="Execute one canonical ServiceRequest (JSON in / JSON out)",
    )
    service.add_argument(
        "--request",
        required=True,
        help="ServiceRequest JSON object, or '-' to read stdin",
    )
    subparsers.add_parser(
        "service-catalog",
        help="Print the machine-readable canonical operation catalog",
    )
    stream = subparsers.add_parser(
        "service-stream",
        help="Emit resumable ServiceExecution pages as newline-delimited JSON",
    )
    stream.add_argument(
        "--request",
        required=True,
        help="Streamable ServiceRequest JSON object, or '-' to read stdin",
    )
    stream.add_argument(
        "--max-pages",
        type=int,
        default=1000,
        help="Transport page ceiling; the last page retains its checkpoint",
    )

    database = subparsers.add_parser(
        "db", help="Explicitly manage the personal model registry"
    )
    database.add_argument(
        "action", choices=["init", "seed", "sync", "query"]
    )
    database.add_argument(
        "--query-str",
        default="SELECT * FROM models",
        help="SQL query for the explicit query action",
    )

    install = subparsers.add_parser(
        "install", help="Install canonical skills and optional MCP transport"
    )
    install.add_argument(
        "--target",
        action="append",
        choices=ALL_TARGETS + ["all"],
        default=None,
    )
    install.add_argument("--project-dir", default=None)
    install.add_argument("--mcp", action="store_true")
    install.add_argument("--antigravity-global", action="store_true")
    install.add_argument("--no-agents-md", action="store_true")
    install.add_argument("--uninstall", action="store_true")
    install.add_argument("--list", action="store_true")
    install.add_argument("-y", "--yes", action="store_true")

    update = subparsers.add_parser(
        "self-update",
        help="Update the package and refresh installed canonical skills",
    )
    update.add_argument("--project-dir", default=None)
    update.add_argument("--mcp", action="store_true")
    update.add_argument("--no-refresh", action="store_true")
    update.add_argument("--dry-run", action="store_true")

    doctor = subparsers.add_parser(
        "doctor", help="Diagnose the Macaulay2 backend"
    )
    doctor.add_argument("--no-smoke", action="store_true")
    return parser


def main() -> None:
    parser = _build_parser()
    try:
        args = parser.parse_args()
        if args.command == "service":
            encoded = (
                sys.stdin.read() if args.request == "-" else args.request
            )
            result = execute_service_payload(json.loads(encoded))
        elif args.command == "service-catalog":
            result = default_service_catalog()
        elif args.command == "service-stream":
            encoded = (
                sys.stdin.read() if args.request == "-" else args.request
            )
            for page in stream_service_payload(
                json.loads(encoded), max_pages=args.max_pages
            ):
                print(json.dumps(page, sort_keys=True), flush=True)
            raise SystemExit(0)
        elif args.command == "db":
            result = (
                query_vector_db("query", {"query": args.query_str})
                if args.action == "query"
                else query_vector_db(args.action)
            )
        elif args.command == "install":
            if args.list:
                run_status(project_dir=args.project_dir)
                raise SystemExit(0)
            if args.uninstall:
                ok = run_uninstall(
                    targets=args.target, project_dir=args.project_dir
                )
            else:
                interactive = (
                    not args.yes
                    and args.target is None
                    and not args.mcp
                    and sys.stdin.isatty()
                )
                ok = (
                    run_interactive(project_dir=args.project_dir)
                    if interactive
                    else run_install(
                        targets=args.target,
                        project_dir=args.project_dir,
                        write_agents=not args.no_agents_md,
                        antigravity_global=args.antigravity_global,
                        with_mcp=args.mcp,
                    )
                )
            raise SystemExit(0 if ok else 1)
        elif args.command == "self-update":
            ok = run_self_update(
                project_dir=args.project_dir,
                with_mcp=True if args.mcp else None,
                refresh=not args.no_refresh,
                dry_run=args.dry_run,
            )
            raise SystemExit(0 if ok else 1)
        elif args.command == "doctor":
            from mobility_toolkit.engine import (
                describe_m2_backend,
                run_macaulay2,
            )

            result = describe_m2_backend()
            if not args.no_smoke and result["available"]:
                smoke = run_macaulay2("2+2", timeout_seconds=20.0)
                result["smoke_test"] = {
                    "ran": True,
                    "ok": (
                        smoke["exit_code"] == 0 and "4" in smoke["stdout"]
                    ),
                    "exit_code": smoke["exit_code"],
                    "stderr": smoke["stderr"].strip()[:300],
                }
            else:
                result["smoke_test"] = {"ran": False, "ok": None}
            print(json.dumps(result, sort_keys=True))
            ok = result["available"] and (
                result["smoke_test"].get("ok") is not False
            )
            raise SystemExit(0 if ok else 1)
        else:
            raise ValueError(f"unknown command: {args.command}")

        print(json.dumps(result, sort_keys=True))
        raise SystemExit(0)
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
