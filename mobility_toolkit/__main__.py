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
from mobility_toolkit.installer import install_skills

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
    parser_install = subparsers.add_parser("install", help="Register custom skills and MCP server for AI agents")
    parser_install.add_argument("--local", action="store_true", help="Install skills locally in project .agents/skills/")
    parser_install.add_argument("--global-install", action="store_true", help="Force install skills globally in ~/.gemini/config/skills/")

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
            is_local = args.local
            if not args.local and not args.global_install:
                if os.path.isdir(".agents"):
                    is_local = True
            install_skills(is_local)
            sys.exit(0)
        else:
            raise ValueError(f"Unknown command: {args.command}")

        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
