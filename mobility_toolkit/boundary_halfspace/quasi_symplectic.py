r"""Exact invariants of a supplied free boundary pairing presentation.

This is the algebraic step *after* a boundary module has been constructed.
For a free tangent-Laurent module ``P = A^r`` with anti-hermitian pairing
matrix ``Omega``, it computes

``rad(P) = ker(Omega: P -> P*)``

and the boundary charge module

``E_P = coker(Omega: P -> P*)``.

It does not construct ``P_boundary`` from a bulk stabilizer presentation and
does not infer secondary operators.  Those are separate half-space problems.
The current backend is exact for a uniform prime coefficient field and a
free tangent translation lattice.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from mobility_toolkit.boundary_halfspace.boundary_module import (
    TangentLaurentPolynomial,
    TangentLaurentTerm,
)
from mobility_toolkit.core.canonical import canonical_json
from mobility_toolkit.core.results import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
)
from mobility_toolkit.engine import describe_m2_backend, run_macaulay2
from mobility_toolkit.translate import _parse_laurent_poly
from mobility_toolkit.utils import is_prime


PairingMatrix = Tuple[Tuple[TangentLaurentPolynomial, ...], ...]


def _negate(
    polynomial: TangentLaurentPolynomial,
) -> TangentLaurentPolynomial:
    return TangentLaurentPolynomial(
        polynomial.coefficient_modulus,
        polynomial.tangent_rank,
        tuple(
            TangentLaurentTerm(
                (-term.coefficient) % polynomial.coefficient_modulus,
                term.exponents,
            )
            for term in polynomial.terms
        ),
    )


@dataclass(frozen=True)
class FreeBoundaryPairingPresentation:
    """A free ``A``-module and its anti-hermitian pairing matrix."""

    coefficient_modulus: int
    tangent_rank: int
    pairing_matrix: PairingMatrix
    generator_labels: Tuple[str, ...] = ()
    source_scope: str = "caller-supplied free boundary module"

    SCHEMA_ID = "mobility_toolkit.free_boundary_pairing_presentation.v1"

    def __post_init__(self) -> None:
        modulus = self.coefficient_modulus
        rank = self.tangent_rank
        if isinstance(modulus, bool) or not isinstance(modulus, int):
            raise TypeError("coefficient_modulus must be an integer")
        if modulus <= 1:
            raise ValueError("coefficient_modulus must be greater than one")
        if isinstance(rank, bool) or not isinstance(rank, int):
            raise TypeError("tangent_rank must be an integer")
        if rank < 0:
            raise ValueError("tangent_rank must be nonnegative")
        matrix = tuple(tuple(row) for row in self.pairing_matrix)
        size = len(matrix)
        if any(len(row) != size for row in matrix):
            raise ValueError("pairing_matrix must be square")
        if not matrix:
            raise ValueError("pairing_matrix must be nonempty")
        for row in matrix:
            for entry in row:
                if not isinstance(entry, TangentLaurentPolynomial):
                    raise TypeError(
                        "pairing entries must be TangentLaurentPolynomial"
                    )
                if entry.coefficient_modulus != modulus:
                    raise ValueError("pairing coefficient modulus mismatch")
                if entry.tangent_rank != rank:
                    raise ValueError("pairing tangent rank mismatch")
        labels = tuple(self.generator_labels)
        if labels and len(labels) != size:
            raise ValueError("generator label count must equal pairing rank")
        if labels and (
            len(set(labels)) != len(labels)
            or any(not isinstance(label, str) or not label for label in labels)
        ):
            raise ValueError("generator labels must be distinct nonempty strings")
        if not isinstance(self.source_scope, str) or not self.source_scope:
            raise ValueError("source_scope must be nonempty")
        if not all(
            matrix[row][column]
            == _negate(matrix[column][row].involution())
            for row in range(size)
            for column in range(size)
        ):
            raise ValueError("pairing_matrix is not anti-hermitian")
        if any(
            any(
                term.exponents == (0,) * rank and term.coefficient % modulus
                for term in matrix[index][index].terms
            )
            for index in range(size)
        ):
            raise ValueError(
                "pairing_matrix is not alternating at the physical constant term"
            )
        object.__setattr__(self, "pairing_matrix", matrix)
        object.__setattr__(self, "generator_labels", labels)

    @property
    def module_rank(self) -> int:
        return len(self.pairing_matrix)

    def to_canonical_dict(self) -> dict:
        return {
            "coefficient_modulus": self.coefficient_modulus,
            "generator_labels": self.generator_labels,
            "module_rank": self.module_rank,
            "pairing_matrix": self.pairing_matrix,
            "schema": self.SCHEMA_ID,
            "source_scope": self.source_scope,
            "tangent_rank": self.tangent_rank,
        }


@dataclass(frozen=True)
class FreeBoundaryPairingCertificate:
    presentation_hash: str
    input_antihermitian_verified: bool
    input_alternating_verified: bool
    coefficient_is_prime: bool
    radical_generator_count: int
    boundary_charge_zero: bool
    boundary_charge_krull_dimension: int
    annihilator_generators: Tuple[TangentLaurentPolynomial, ...]
    backend_checks_complete: bool

    SCHEMA_ID = "mobility_toolkit.free_boundary_pairing_certificate.v1"

    @property
    def radical_zero(self) -> bool:
        return self.radical_generator_count == 0

    @property
    def pairing_unimodular(self) -> bool:
        return self.boundary_charge_zero

    @property
    def verified(self) -> bool:
        return (
            bool(self.presentation_hash)
            and self.input_antihermitian_verified
            and self.input_alternating_verified
            and self.coefficient_is_prime
            and self.radical_generator_count >= 0
            and (
                self.boundary_charge_krull_dimension == -1
                if self.boundary_charge_zero
                else self.boundary_charge_krull_dimension >= 0
            )
            and bool(self.annihilator_generators)
            and self.backend_checks_complete
        )

    def to_canonical_dict(self) -> dict:
        return {
            "annihilator_generators": self.annihilator_generators,
            "backend_checks_complete": self.backend_checks_complete,
            "boundary_charge_krull_dimension":
                self.boundary_charge_krull_dimension,
            "boundary_charge_zero": self.boundary_charge_zero,
            "coefficient_is_prime": self.coefficient_is_prime,
            "input_antihermitian_verified":
                self.input_antihermitian_verified,
            "input_alternating_verified": self.input_alternating_verified,
            "pairing_unimodular": self.pairing_unimodular,
            "presentation_hash": self.presentation_hash,
            "radical_generator_count": self.radical_generator_count,
            "radical_zero": self.radical_zero,
            "schema": self.SCHEMA_ID,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class FreeBoundaryPairingInvariants:
    module_rank: int
    radical_generator_count: int
    radical_zero: bool
    boundary_charge_krull_dimension: int
    boundary_charge_zero: bool
    boundary_charge_annihilator: Tuple[TangentLaurentPolynomial, ...]
    pairing_unimodular: bool
    certificate: FreeBoundaryPairingCertificate

    SCHEMA_ID = "mobility_toolkit.free_boundary_pairing_invariants.v1"

    def __post_init__(self) -> None:
        if not self.certificate.verified:
            raise ValueError("free boundary pairing certificate is not verified")

    def to_canonical_dict(self) -> dict:
        return {
            "boundary_charge_annihilator":
                self.boundary_charge_annihilator,
            "boundary_charge_krull_dimension":
                self.boundary_charge_krull_dimension,
            "boundary_charge_zero": self.boundary_charge_zero,
            "certificate": self.certificate,
            "module_rank": self.module_rank,
            "pairing_unimodular": self.pairing_unimodular,
            "radical_generator_count": self.radical_generator_count,
            "radical_zero": self.radical_zero,
            "schema": self.SCHEMA_ID,
        }


def _render_polynomial(polynomial: TangentLaurentPolynomial) -> str:
    if polynomial.is_zero:
        return "0"
    terms = []
    for term in polynomial.terms:
        factors = []
        coefficient = term.coefficient % polynomial.coefficient_modulus
        for index, exponent in enumerate(term.exponents, 1):
            if exponent == 0:
                continue
            variable = f"x{index}" if exponent > 0 else f"t{index}"
            magnitude = abs(exponent)
            factors.append(
                variable if magnitude == 1 else f"{variable}^{magnitude}"
            )
        if coefficient != 1 or not factors:
            factors.insert(0, str(coefficient))
        terms.append("*".join(factors))
    return " + ".join(terms)


def _m2_script(presentation: FreeBoundaryPairingPresentation) -> str:
    variables = [
        variable
        for index in range(1, presentation.tangent_rank + 1)
        for variable in (f"x{index}", f"t{index}")
    ]
    if variables:
        inverse_relations = [
            f"x{index}*t{index}-1"
            for index in range(1, presentation.tangent_rank + 1)
        ]
        ring_lines = (
            f"P = GF({presentation.coefficient_modulus})"
            f"[{','.join(variables)},MonomialOrder=>GRevLex];",
            f"A = P/(ideal({','.join(inverse_relations)}));",
        )
    else:
        ring_lines = (f"A = GF({presentation.coefficient_modulus});",)
    rows = ",".join(
        "{" + ",".join(_render_polynomial(entry) for entry in row) + "}"
        for row in presentation.pairing_matrix
    )
    return "\n".join(
        ring_lines
        + (
            f"Omega = matrix(A,{{{rows}}});",
            "Rad = trim kernel Omega;",
            "E = coker Omega;",
            "I = ann E;",
            "G = mingens I;",
            'print("MT_QS:RADICAL_GENERATORS:" | '
            "toString numColumns gens Rad);",
            'print("MT_QS:CHARGE_DIM:" | toString dim E);',
            'print("MT_QS:ANN_COLS:" | toString numColumns G);',
            "if numColumns G > 0 then "
            "scan(0..numColumns G-1, column -> "
            'print("MT_QS:ANN_ENTRY:" | toString column | ":" | '
            "toString G_(0,column)));",
            'print("MT_QS:BACKEND_COMPLETE:true");',
        )
    )


def _marker(stdout: str, name: str) -> str:
    match = re.search(
        rf"^\s*MT_QS:{re.escape(name)}:(.*)$",
        stdout,
        flags=re.MULTILINE,
    )
    if match is None:
        raise RuntimeError(f"Macaulay2 output is missing marker {name!r}")
    return match.group(1).strip()


def _parse_dimension(value: str) -> int:
    lowered = value.lower()
    if "infinity" in lowered or lowered in {"-inf", "inf"}:
        return -1
    match = re.search(r"-?\d+", value)
    if match is None:
        raise RuntimeError(f"cannot parse Macaulay2 dimension {value!r}")
    return int(match.group(0))


def _parse_annihilator(
    stdout: str,
    presentation: FreeBoundaryPairingPresentation,
) -> Tuple[TangentLaurentPolynomial, ...]:
    count = int(_marker(stdout, "ANN_COLS"))
    expressions: Dict[int, str] = {}
    for match in re.finditer(
        r"^\s*MT_QS:ANN_ENTRY:(\d+):(.*)$",
        stdout,
        flags=re.MULTILINE,
    ):
        expressions[int(match.group(1))] = match.group(2).strip()
    if set(expressions) != set(range(count)):
        raise RuntimeError("Macaulay2 annihilator output is incomplete")
    parsed = []
    for index in range(count):
        terms = _parse_laurent_poly(
            expressions[index],
            presentation.tangent_rank,
            presentation.coefficient_modulus,
        )
        parsed.append(
            TangentLaurentPolynomial(
                presentation.coefficient_modulus,
                presentation.tangent_rank,
                tuple(
                    TangentLaurentTerm(coefficient, exponents)
                    for exponents, coefficient in terms.items()
                ),
            )
        )
    normalized = []
    for polynomial in parsed:
        if polynomial.is_zero:
            normalized.append(polynomial)
            continue
        minimum = tuple(
            min(term.exponents[axis] for term in polynomial.terms)
            for axis in range(presentation.tangent_rank)
        )
        shifted_terms = tuple(
            TangentLaurentTerm(
                term.coefficient,
                tuple(
                    exponent - offset
                    for exponent, offset in zip(term.exponents, minimum)
                ),
            )
            for term in polynomial.terms
        )
        shifted = TangentLaurentPolynomial(
            presentation.coefficient_modulus,
            presentation.tangent_rank,
            shifted_terms,
        )
        leading_coefficient = shifted.terms[0].coefficient
        inverse = pow(
            leading_coefficient,
            presentation.coefficient_modulus - 2,
            presentation.coefficient_modulus,
        )
        normalized.append(
            TangentLaurentPolynomial(
                presentation.coefficient_modulus,
                presentation.tangent_rank,
                tuple(
                    TangentLaurentTerm(
                        term.coefficient * inverse,
                        term.exponents,
                    )
                    for term in shifted.terms
                ),
            )
        )
    canonical = {
        canonical_json(polynomial): polynomial for polynomial in normalized
    }
    return tuple(canonical[key] for key in sorted(canonical))


def analyze_free_boundary_pairing(
    presentation: FreeBoundaryPairingPresentation,
    *,
    timeout_seconds: float = 60.0,
    execute: Optional[Callable[[str, float], dict]] = None,
) -> ComputationResult:
    """Compute exact radical and boundary-charge invariants of ``presentation``."""

    if not isinstance(presentation, FreeBoundaryPairingPresentation):
        raise TypeError(
            "presentation must be FreeBoundaryPairingPresentation"
        )
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or timeout_seconds <= 0
        or not math.isfinite(float(timeout_seconds))
    ):
        raise ValueError("timeout_seconds must be finite and positive")
    if not is_prime(presentation.coefficient_modulus):
        raise NotImplementedError(
            "free boundary pairing invariants currently require a uniform "
            "prime coefficient field"
        )
    script = _m2_script(presentation)
    runner = execute or (
        lambda source, timeout: run_macaulay2(
            source, timeout_seconds=timeout
        )
    )
    backend_result = runner(script, float(timeout_seconds))
    if int(backend_result.get("exit_code", 1)) != 0:
        message = (
            backend_result.get("stderr")
            or backend_result.get("stdout")
            or "Macaulay2 boundary-pairing analysis failed"
        )
        raise RuntimeError(
            f"Macaulay2 boundary-pairing analysis failed: {message}"
        )
    stdout = str(backend_result.get("stdout", ""))
    radical_generators = int(_marker(stdout, "RADICAL_GENERATORS"))
    dimension = _parse_dimension(_marker(stdout, "CHARGE_DIM"))
    annihilator = _parse_annihilator(stdout, presentation)
    backend_complete = _marker(stdout, "BACKEND_COMPLETE").lower() == "true"
    zero = dimension == -1
    from mobility_toolkit.core.canonical import canonical_hash

    certificate = FreeBoundaryPairingCertificate(
        presentation_hash=canonical_hash(
            "free-boundary-pairing-presentation-v1",
            presentation,
        ),
        input_antihermitian_verified=True,
        input_alternating_verified=True,
        coefficient_is_prime=True,
        radical_generator_count=radical_generators,
        boundary_charge_zero=zero,
        boundary_charge_krull_dimension=dimension,
        annihilator_generators=annihilator,
        backend_checks_complete=backend_complete,
    )
    if not certificate.verified:
        raise RuntimeError("boundary pairing invariants failed their certificate")
    value = FreeBoundaryPairingInvariants(
        module_rank=presentation.module_rank,
        radical_generator_count=radical_generators,
        radical_zero=certificate.radical_zero,
        boundary_charge_krull_dimension=dimension,
        boundary_charge_zero=zero,
        boundary_charge_annihilator=annihilator,
        pairing_unimodular=certificate.pairing_unimodular,
        certificate=certificate,
    )
    description = describe_m2_backend()
    return ComputationResult(
        operation="halfspace.analyze_free_boundary_pairing",
        input_data=presentation,
        value=value,
        exactness=Exactness.CERTIFIED_EXACT,
        assumptions=(
            "the supplied boundary module is free over the tangent Laurent ring",
            "uniform prime coefficient field",
            "free tangent translation lattice",
        ),
        theorem_scope=(
            "Exact radical kernel and E_P=coker(Omega) invariants for the "
            "supplied free boundary module.  This operation does not construct "
            "P_boundary, compute secondary closure, or prove that the supplied "
            "presentation comes from a half-space stabilizer code."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=certificate,
        verification=(
            ("antihermitian_input", True),
            ("alternating_input", True),
            ("boundary_charge_zero", zero),
            ("radical_zero", certificate.radical_zero),
        ),
        backend_provenance=BackendProvenance(
            backend="Macaulay2",
            algorithm="free-boundary-pairing-kernel-cokernel-annihilator",
            version=str(description.get("strategy", "unreported")),
            parameters=(
                ("coefficient_modulus", presentation.coefficient_modulus),
                ("module_rank", presentation.module_rank),
                ("tangent_rank", presentation.tangent_rank),
            ),
        ),
        diagnostics=(
            "Boundary charges use E_P=coker(Omega), not a finite-window radical.",
        ),
        warnings=(
            "A nonzero primary boundary charge module does not imply that the "
            "full boundary module has the same charge module when secondaries exist.",
        ),
    )


__all__ = [
    "FreeBoundaryPairingCertificate",
    "FreeBoundaryPairingInvariants",
    "FreeBoundaryPairingPresentation",
    "analyze_free_boundary_pairing",
]
