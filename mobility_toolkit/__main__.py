import sys
import json
import argparse
import os
from mobility_toolkit import (
    compute_ext_krull,
    compute_true_mobility_dimension,
    compute_gsd_and_periodicity,
    analyze_fusion_interference,
    solve_sset_fusion,
    search_koszul_models,
    query_vector_db
)
from mobility_toolkit.installer import (
    run_install, run_uninstall, run_status, run_interactive, run_self_update, ALL_TARGETS
)

class JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)

def main():
    parser = JSONArgumentParser(description="Mobility Fusion Generalization Toolkit CLI")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommands")

    # homology
    parser_homology = subparsers.add_parser("homology", help="Compute homology Ext modules and Krull dimension")
    parser_homology.add_argument("--stabilizer", type=str, required=True, help="JSON list of lists of strings")
    parser_homology.add_argument("--qudit-dim", type=int, required=True, help="Qudit dimension")
    parser_homology.add_argument("--p-ext", type=int, default=0, help="Ext parameter p_ext")
    parser_homology.add_argument("--prime-bypass", action="store_true", help="Bypass prime check for qudit dimension")

    # mobility
    parser_mobility = subparsers.add_parser("mobility", help="Compute true mobility dimension")
    parser_mobility.add_argument("--generators", type=str, required=True, help="JSON list of strings")
    parser_mobility.add_argument("--qudit-dim", type=int, required=True, help="Qudit dimension")
    parser_mobility.add_argument("--all-vars", type=str, default=None, help="JSON list of strings")

    # grobner
    parser_grobner = subparsers.add_parser("grobner", help="Compute GSD and periodicity via Grobner bases")
    parser_grobner.add_argument("--stabilizer", type=str, required=True, help="JSON list of lists of strings")
    parser_grobner.add_argument("--Lx", type=int, required=True, help="Torus size Lx")
    parser_grobner.add_argument("--Ly", type=int, required=True, help="Torus size Ly")
    parser_grobner.add_argument("--qudit-dim", type=int, required=True, help="Qudit dimension")

    # fusion-interference
    parser_fi = subparsers.add_parser("fusion-interference", help="Analyze fusion interference under shift vectors")
    parser_fi.add_argument("--stabilizer", type=str, required=True, help="JSON list of lists of strings")
    parser_fi.add_argument("--qudit-dim", type=int, required=True, help="Qudit dimension")
    parser_fi.add_argument("--shifts", type=str, required=True, help="JSON list of lists of ints")

    # sset-fusion
    parser_sf = subparsers.add_parser("sset-fusion", help="Solve SSET fusion rules and characteristic polynomials")
    parser_sf.add_argument("--poly-f", type=str, required=True, help="First polynomial")
    parser_sf.add_argument("--poly-g", type=str, required=True, help="Second polynomial")

    # search
    parser_search = subparsers.add_parser("search", help="Search for Koszul models with target dimension")
    parser_search.add_argument("--qudit-dim", type=int, required=True, help="Qudit dimension")
    parser_search.add_argument("--target-dim", type=int, required=True, help="Target Krull dimension")
    parser_search.add_argument("--max-trials", type=int, default=100, help="Maximum number of trials")

    # db
    parser_db = subparsers.add_parser("db", help="Manage and query the models database")
    parser_db.add_argument("action", choices=["init", "seed", "sync", "query"], help="Database action")
    parser_db.add_argument("--query-str", type=str, default="SELECT * FROM models", help="SQL query string for query action")

    # install
    parser_install = subparsers.add_parser("install", help="Install skills + MCP server into AI agents (project-level by default)")
    parser_install.add_argument(
        "--target", action="append", choices=ALL_TARGETS + ["all"], default=None,
        help="Agent(s) to install for; repeatable. Omit to auto-detect (claude/codex/opencode). Use 'all' to include Antigravity (global).",
    )
    parser_install.add_argument("--project-dir", type=str, default=None, help="Project directory to install into (default: CWD)")
    parser_install.add_argument("--mcp", action="store_true", help="Also wire the MCP server (default: skills-only, scripts called directly)")
    parser_install.add_argument("--antigravity-global", action="store_true", help="Install Antigravity into global ~/.gemini instead of project .agents/")
    parser_install.add_argument("--no-agents-md", action="store_true", help="Do not write/update AGENTS.md")
    parser_install.add_argument("--uninstall", action="store_true", help="Remove installed skills/MCP entries instead of installing")
    parser_install.add_argument("--list", action="store_true", help="Show install status for each agent and exit")
    parser_install.add_argument("-y", "--yes", action="store_true", help="Non-interactive: use detected agents + defaults, no prompts")

    # self-update
    parser_su = subparsers.add_parser(
        "self-update",
        help="Update the toolkit from GitHub, then refresh the current project's skills",
    )
    parser_su.add_argument("--project-dir", type=str, default=None, help="Project to refresh (default: CWD)")
    parser_su.add_argument("--mcp", action="store_true", help="Force-refresh the MCP config too (default: keep the project's existing setup)")
    parser_su.add_argument("--no-refresh", action="store_true", help="Only update the package; don't touch any project")
    parser_su.add_argument("--dry-run", action="store_true", help="Show what would run without changing anything")

    # doctor
    parser_doctor = subparsers.add_parser("doctor", help="Diagnose the Macaulay2 backend on this platform")
    parser_doctor.add_argument("--no-smoke", action="store_true", help="Skip the live M2 '2+2' smoke test")

    try:
        args = parser.parse_args()

        if args.command == "homology":
            stabilizer = json.loads(args.stabilizer)
            result = compute_ext_krull(stabilizer, args.qudit_dim, args.p_ext, args.prime_bypass)
        elif args.command == "mobility":
            generators = json.loads(args.generators)
            all_vars = json.loads(args.all_vars) if args.all_vars is not None else None
            result = compute_true_mobility_dimension(generators, args.qudit_dim, all_vars)
        elif args.command == "grobner":
            stabilizer = json.loads(args.stabilizer)
            result = compute_gsd_and_periodicity(stabilizer, args.Lx, args.Ly, args.qudit_dim)
        elif args.command == "fusion-interference":
            stabilizer = json.loads(args.stabilizer)
            shifts = json.loads(args.shifts)
            result = analyze_fusion_interference(stabilizer, args.qudit_dim, shifts)
        elif args.command == "sset-fusion":
            result = solve_sset_fusion(args.poly_f, args.poly_g)
        elif args.command == "search":
            result = search_koszul_models(args.qudit_dim, args.target_dim, args.max_trials)
        elif args.command == "db":
            if args.action == "query":
                result = query_vector_db(args.action, {"query": args.query_str})
            else:
                result = query_vector_db(args.action)
        elif args.command == "install":
            if args.list:
                run_status(project_dir=args.project_dir)
                sys.exit(0)
            if args.uninstall:
                ok = run_uninstall(targets=args.target, project_dir=args.project_dir)
            else:
                # interactive wizard when in a TTY and the user didn't pin choices
                interactive = (
                    not args.yes
                    and args.target is None
                    and not args.mcp
                    and sys.stdin.isatty()
                )
                if interactive:
                    ok = run_interactive(project_dir=args.project_dir)
                else:
                    ok = run_install(
                        targets=args.target,
                        project_dir=args.project_dir,
                        write_agents=not args.no_agents_md,
                        antigravity_global=args.antigravity_global,
                        with_mcp=args.mcp,
                    )
            sys.exit(0 if ok else 1)
        elif args.command == "self-update":
            ok = run_self_update(
                project_dir=args.project_dir,
                with_mcp=True if args.mcp else None,
                refresh=not args.no_refresh,
                dry_run=args.dry_run,
            )
            sys.exit(0 if ok else 1)
        elif args.command == "doctor":
            from mobility_toolkit.engine import describe_m2_backend, run_macaulay2
            info = describe_m2_backend()
            if not args.no_smoke and info["available"]:
                res = run_macaulay2("2+2", timeout_seconds=20.0)
                info["smoke_test"] = {
                    "ran": True,
                    "ok": res["exit_code"] == 0 and "4" in res["stdout"],
                    "exit_code": res["exit_code"],
                    "stderr": res["stderr"].strip()[:300],
                }
            else:
                info["smoke_test"] = {"ran": False, "ok": None}
            print(json.dumps(info, indent=2))
            sys.exit(0 if info["available"] and info["smoke_test"].get("ok") is not False else 1)
        else:
            raise ValueError(f"Unknown command: {args.command}")

        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
