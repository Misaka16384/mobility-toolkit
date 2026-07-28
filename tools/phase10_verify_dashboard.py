"""Validate and optionally execute the Phase 10 research-release dashboard.

The verifier is deliberately standard-library only.  It enforces an
operation-scoped promotion rule: every production claim must cite executable
evidence in correctness, literature, cross-backend, and scale layers.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


SCHEMA_VERSION = "mobility_toolkit.research_dashboard.v1"
LAYER_NAMES = ("correctness", "literature", "cross_backend", "scale")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_manifest() -> Path:
    return _repo_root() / "tests" / "research_gates" / "phase10_capabilities.json"


def load_dashboard(path: Path) -> Mapping[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("dashboard root must be a JSON object")
    return value


def _as_string_list(value: object, label: str, errors: List[str]) -> List[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        errors.append("%s must be a list of non-empty strings" % label)
        return []
    return list(value)


def _evidence_path(root: Path, nodeid: str) -> Path:
    return root / nodeid.split("::", 1)[0]


def validate_dashboard(
    dashboard: Mapping[str, object],
    root: Path,
) -> List[str]:
    errors: List[str] = []
    if dashboard.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be %s" % SCHEMA_VERSION)

    policy = dashboard.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be an object")
        policy = {}
    required_layers = _as_string_list(
        policy.get("production_required_layers"),
        "policy.production_required_layers",
        errors,
    )
    if set(required_layers) != set(LAYER_NAMES):
        errors.append(
            "production_required_layers must contain exactly %s"
            % ", ".join(LAYER_NAMES)
        )
    allowed_statuses = set(
        _as_string_list(
            policy.get("allowed_statuses"),
            "policy.allowed_statuses",
            errors,
        )
    )
    allowed_exactness = set(
        _as_string_list(
            policy.get("allowed_exactness"),
            "policy.allowed_exactness",
            errors,
        )
    )
    forbidden_phrases = [
        item.lower()
        for item in _as_string_list(
            policy.get("forbidden_production_phrases"),
            "policy.forbidden_production_phrases",
            errors,
        )
    ]

    layers = dashboard.get("ci_layers")
    if not isinstance(layers, dict):
        errors.append("ci_layers must be an object")
        layers = {}
    if set(layers) != set(LAYER_NAMES):
        errors.append("ci_layers must contain exactly %s" % ", ".join(LAYER_NAMES))
    for layer_name in LAYER_NAMES:
        layer = layers.get(layer_name)
        if not isinstance(layer, dict):
            errors.append("ci_layers.%s must be an object" % layer_name)
            continue
        if not isinstance(layer.get("description"), str) or not layer["description"]:
            errors.append("ci_layers.%s.description is required" % layer_name)
        command = _as_string_list(
            layer.get("smoke_command"),
            "ci_layers.%s.smoke_command" % layer_name,
            errors,
        )
        command_text = " ".join(command).lower()
        if "pytest" not in command_text:
            errors.append("ci_layers.%s must be executable pytest" % layer_name)
        if "m2" in command_text or "macaulay" in command_text:
            errors.append(
                "ci_layers.%s bounded smoke command must not require Macaulay2"
                % layer_name
            )

    evidence_rows = dashboard.get("evidence")
    if not isinstance(evidence_rows, list):
        errors.append("evidence must be a list")
        evidence_rows = []
    evidence: Dict[str, Mapping[str, object]] = {}
    for index, item in enumerate(evidence_rows):
        label = "evidence[%d]" % index
        if not isinstance(item, dict):
            errors.append("%s must be an object" % label)
            continue
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str) or not evidence_id:
            errors.append("%s.id is required" % label)
            continue
        if evidence_id in evidence:
            errors.append("duplicate evidence id %s" % evidence_id)
            continue
        evidence[evidence_id] = item
        layer = item.get("layer")
        if layer not in LAYER_NAMES:
            errors.append("%s.layer is invalid" % label)
        nodeid = item.get("nodeid")
        if not isinstance(nodeid, str) or "::test_" not in nodeid:
            errors.append("%s.nodeid must name an executable pytest test" % label)
        else:
            path = _evidence_path(root, nodeid)
            if not path.is_file():
                errors.append("%s.nodeid path does not exist: %s" % (label, path))
            else:
                test_name = nodeid.split("::", 1)[1].split("[", 1)[0]
                source = path.read_text(encoding="utf-8")
                if ("def %s(" % test_name) not in source:
                    errors.append(
                        "%s.nodeid test function is not present: %s"
                        % (label, nodeid)
                    )
        if not isinstance(item.get("assertion"), str) or not item["assertion"]:
            errors.append("%s.assertion is required" % label)
        dependencies = item.get("dependencies")
        if not isinstance(dependencies, list) or not all(
            isinstance(value, str) for value in dependencies
        ):
            errors.append("%s.dependencies must be a string list" % label)
        if dependencies and "macaulay2" in {
            str(value).lower() for value in dependencies
        }:
            errors.append("%s must not require unavailable Macaulay2" % label)

    capabilities = dashboard.get("capabilities")
    if not isinstance(capabilities, list):
        errors.append("capabilities must be a list")
        capabilities = []
    capability_ids = set()
    for index, item in enumerate(capabilities):
        label = "capabilities[%d]" % index
        if not isinstance(item, dict):
            errors.append("%s must be an object" % label)
            continue
        capability_id = item.get("id")
        if not isinstance(capability_id, str) or not capability_id:
            errors.append("%s.id is required" % label)
            continue
        if capability_id in capability_ids:
            errors.append("duplicate capability id %s" % capability_id)
        capability_ids.add(capability_id)
        status = item.get("status")
        if status not in allowed_statuses:
            errors.append("%s.status is invalid" % label)
        scope = item.get("operation_scope")
        if not isinstance(scope, str) or not scope.strip():
            errors.append("%s.operation_scope is required" % label)
            scope = ""
        limitations = _as_string_list(
            item.get("limitations"),
            "%s.limitations" % label,
            errors,
        )
        exactness = set(
            _as_string_list(
                item.get("exactness"),
                "%s.exactness" % label,
                errors,
            )
        )
        unknown_exactness = exactness - allowed_exactness
        if unknown_exactness:
            errors.append(
                "%s has invalid exactness: %s"
                % (label, ", ".join(sorted(unknown_exactness)))
            )
        evidence_ids = _as_string_list(
            item.get("evidence"),
            "%s.evidence" % label,
            errors,
        )
        unknown_evidence = set(evidence_ids) - set(evidence)
        if unknown_evidence:
            errors.append(
                "%s cites unknown evidence: %s"
                % (label, ", ".join(sorted(unknown_evidence)))
            )
        if status == "production":
            covered_layers = {
                evidence[evidence_id]["layer"]
                for evidence_id in evidence_ids
                if evidence_id in evidence
            }
            missing_layers = set(required_layers) - covered_layers
            if missing_layers:
                errors.append(
                    "production capability %s lacks evidence layers: %s"
                    % (capability_id, ", ".join(sorted(missing_layers)))
                )
            if not limitations:
                errors.append(
                    "production capability %s must state limitations" % capability_id
                )
            claim_text = " ".join(
                [
                    str(item.get("title", "")),
                    scope,
                    " ".join(limitations),
                ]
            ).lower()
            for phrase in forbidden_phrases:
                if phrase in claim_text:
                    errors.append(
                        "production capability %s contains forbidden broad claim %r"
                        % (capability_id, phrase)
                    )
            if exactness & {"experimental", "unsupported"}:
                errors.append(
                    "production capability %s cannot advertise experimental or "
                    "unsupported exactness" % capability_id
                )
        elif status == "unsupported":
            if exactness != {"unsupported"}:
                errors.append(
                    "unsupported capability %s must have exactness unsupported"
                    % capability_id
                )

    return errors


def run_layer(
    dashboard: Mapping[str, object],
    layer: str,
    root: Path,
) -> int:
    layers = dashboard["ci_layers"]
    command = layers[layer]["smoke_command"]
    print("running %s: %s" % (layer, " ".join(command)))
    return subprocess.run(command, cwd=str(root), check=False).returncode


def _print_commands(dashboard: Mapping[str, object]) -> None:
    layers = dashboard["ci_layers"]
    for layer in LAYER_NAMES:
        print("%s: %s" % (layer, " ".join(layers[layer]["smoke_command"])))


def main(argv: Sequence[str] = ()) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=_default_manifest(),
        help="machine-readable dashboard JSON",
    )
    parser.add_argument(
        "--run-layer",
        choices=LAYER_NAMES,
        action="append",
        default=[],
        help="run one bounded CI layer after validation; may be repeated",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="print the four layer commands without running them",
    )
    args = parser.parse_args(list(argv))
    manifest = args.manifest.resolve()
    root = _repo_root()
    try:
        dashboard = load_dashboard(manifest)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("dashboard load failed: %s" % error, file=sys.stderr)
        return 2
    errors = validate_dashboard(dashboard, root)
    if errors:
        for error in errors:
            print("ERROR: %s" % error, file=sys.stderr)
        return 1
    print(
        "dashboard valid: %d capabilities, %d evidence records"
        % (len(dashboard["capabilities"]), len(dashboard["evidence"]))
    )
    if args.list:
        _print_commands(dashboard)
    for layer in args.run_layer:
        returncode = run_layer(dashboard, layer, root)
        if returncode:
            return returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
