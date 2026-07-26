"""Experimental composite/nonuniform Laurent resolution benchmarks.

These services intentionally do *not* implement generic composite Ext.  They
machine-check explicit resolutions from, or directly motivated by, Ruba--Yang
2204.06023.  The distinction matters because Macaulay2 1.22 cannot construct
``ZZ/4[x,...]`` directly and its ordinary finite free ``Ext`` path does not
discover the paper's infinite periodic resolution.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Sequence, Tuple

from mobility_toolkit.core.canonical import canonical_hash, canonical_json
from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.core.laurent import LaurentPolynomial, TranslationGroup
from mobility_toolkit.core.results import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
)
from mobility_toolkit.engine import describe_m2_backend, run_macaulay2
from mobility_toolkit.finite.backend import FlintIntegerBackend
from mobility_toolkit.finite.groups import FiniteAbelianGroup, FiniteGroupHomomorphism
from mobility_toolkit.periodic.laurent import (
    GroupRingMonomial,
    parse_legacy_laurent,
    polynomial_from_terms,
    render_m2_laurent,
)


def _integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


@dataclass(frozen=True)
class LaurentMatrix:
    """Sparse matrix over one canonical finite-coefficient group ring."""

    coefficient_modulus: int
    translation_group: TranslationGroup
    nrows: int
    ncols: int
    entries: Tuple[Tuple[int, int, LaurentPolynomial], ...] = ()

    SCHEMA_ID = "mobility_toolkit.laurent_matrix.v1"

    def __post_init__(self) -> None:
        modulus = _integer(self.coefficient_modulus, "coefficient_modulus")
        nrows = _integer(self.nrows, "nrows")
        ncols = _integer(self.ncols, "ncols")
        if modulus <= 1:
            raise ValueError("coefficient_modulus must be greater than one")
        if nrows < 0 or ncols < 0:
            raise ValueError("matrix dimensions must be nonnegative")
        accumulated: Dict[Tuple[int, int], LaurentPolynomial] = {}
        for row, column, polynomial in tuple(self.entries):
            row = _integer(row, "matrix row")
            column = _integer(column, "matrix column")
            if not 0 <= row < nrows or not 0 <= column < ncols:
                raise ValueError("Laurent matrix entry is out of bounds")
            if not isinstance(polynomial, LaurentPolynomial):
                raise TypeError("Laurent matrix coefficients must be LaurentPolynomial objects")
            if polynomial.coefficient_modulus != modulus:
                raise ValueError("Laurent matrix coefficient has the wrong modulus")
            if polynomial.translation_group != self.translation_group:
                raise ValueError("Laurent matrix coefficient has the wrong translation group")
            key = (row, column)
            previous = accumulated.get(key)
            accumulated[key] = polynomial if previous is None else previous + polynomial
        normalized = tuple(
            (row, column, polynomial)
            for (row, column), polynomial in sorted(accumulated.items())
            if not polynomial.is_zero
        )
        object.__setattr__(self, "coefficient_modulus", modulus)
        object.__setattr__(self, "nrows", nrows)
        object.__setattr__(self, "ncols", ncols)
        object.__setattr__(self, "entries", normalized)

    @classmethod
    def zero(
        cls,
        modulus: int,
        group: TranslationGroup,
        nrows: int,
        ncols: int,
    ) -> "LaurentMatrix":
        return cls(modulus, group, nrows, ncols)

    @classmethod
    def from_rows(
        cls,
        modulus: int,
        group: TranslationGroup,
        rows: Sequence[Sequence[LaurentPolynomial]],
    ) -> "LaurentMatrix":
        rows = tuple(tuple(row) for row in rows)
        ncols = len(rows[0]) if rows else 0
        if any(len(row) != ncols for row in rows):
            raise ValueError("Laurent matrix rows must have equal length")
        return cls(
            modulus,
            group,
            len(rows),
            ncols,
            tuple(
                (row_index, column_index, polynomial)
                for row_index, row in enumerate(rows)
                for column_index, polynomial in enumerate(row)
                if not polynomial.is_zero
            ),
        )

    def _entry_map(self) -> Dict[Tuple[int, int], LaurentPolynomial]:
        return {(row, column): polynomial for row, column, polynomial in self.entries}

    def coefficient(self, row: int, column: int) -> LaurentPolynomial:
        row = _integer(row, "row")
        column = _integer(column, "column")
        if not 0 <= row < self.nrows or not 0 <= column < self.ncols:
            raise IndexError("Laurent matrix coordinate is out of bounds")
        return self._entry_map().get(
            (row, column),
            LaurentPolynomial.zero(self.coefficient_modulus, self.translation_group),
        )

    def _require_composable(self, other: "LaurentMatrix") -> None:
        if not isinstance(other, LaurentMatrix):
            raise TypeError("expected LaurentMatrix")
        if self.ncols != other.nrows:
            raise ValueError("Laurent matrices are not composable")
        if (
            self.coefficient_modulus != other.coefficient_modulus
            or self.translation_group != other.translation_group
        ):
            raise ValueError("Laurent matrices belong to different group rings")

    def matmul(self, other: "LaurentMatrix") -> "LaurentMatrix":
        self._require_composable(other)
        left_by_inner: Dict[int, list] = {}
        right_by_inner: Dict[int, list] = {}
        for row, inner, polynomial in self.entries:
            left_by_inner.setdefault(inner, []).append((row, polynomial))
        for inner, column, polynomial in other.entries:
            right_by_inner.setdefault(inner, []).append((column, polynomial))
        products = []
        for inner in sorted(set(left_by_inner).intersection(right_by_inner)):
            for row, left in left_by_inner[inner]:
                for column, right in right_by_inner[inner]:
                    products.append((row, column, left * right))
        return LaurentMatrix(
            self.coefficient_modulus,
            self.translation_group,
            self.nrows,
            other.ncols,
            tuple(products),
        )

    def involution_transpose(self) -> "LaurentMatrix":
        return LaurentMatrix(
            self.coefficient_modulus,
            self.translation_group,
            self.ncols,
            self.nrows,
            tuple(
                (column, row, polynomial.involution())
                for row, column, polynomial in self.entries
            ),
        )

    @property
    def is_zero(self) -> bool:
        return not self.entries

    def render_m2_rows(self) -> str:
        rows = []
        for row in range(self.nrows):
            rows.append(
                "{" + ",".join(
                    render_m2_laurent(self.coefficient(row, column))
                    for column in range(self.ncols)
                ) + "}"
            )
        return "{" + ",".join(rows) + "}"

    def to_canonical_dict(self) -> dict:
        return {
            "coefficient_modulus": self.coefficient_modulus,
            "entries": self.entries,
            "ncols": self.ncols,
            "nrows": self.nrows,
            "schema": self.SCHEMA_ID,
            "translation_group": self.translation_group,
        }


def _constant(modulus: int, group: TranslationGroup, value: int) -> LaurentPolynomial:
    return GroupRingMonomial.identity(group).as_polynomial(modulus, value)


def _poly(
    modulus: int,
    group: TranslationGroup,
    terms: Iterable[Tuple[int, Tuple[int, ...]]],
) -> LaurentPolynomial:
    return polynomial_from_terms(
        modulus,
        group,
        tuple(
            (coefficient, GroupRingMonomial(group, exponents))
            for coefficient, exponents in terms
        ),
    )


@dataclass(frozen=True)
class RubaYangZ4Resolution:
    sigma: LaurentMatrix
    tau: LaurentMatrix
    epsilon: LaurentMatrix
    tau_dagger: LaurentMatrix

    SCHEMA_ID = "mobility_toolkit.ruba_yang_z4_resolution.v1"

    def chain_identities(self) -> Tuple[Tuple[str, bool], ...]:
        return (
            ("sigma_tau", self.sigma.matmul(self.tau).is_zero),
            ("tau_tau", self.tau.matmul(self.tau).is_zero),
            ("tau_dagger_epsilon", self.tau_dagger.matmul(self.epsilon).is_zero),
            ("tau_dagger_squared", self.tau_dagger.matmul(self.tau_dagger).is_zero),
        )

    def to_canonical_dict(self) -> dict:
        return {
            "epsilon": self.epsilon,
            "schema": self.SCHEMA_ID,
            "sigma": self.sigma,
            "tau": self.tau,
            "tau_dagger": self.tau_dagger,
        }


def ruba_yang_z4_resolution() -> RubaYangZ4Resolution:
    """Return Sec. 7.8 Eqs. (99)--(102) as canonical matrices."""

    modulus = 4
    group = TranslationGroup(2, free_generator_names=("x", "y"))
    zero = LaurentPolynomial.zero(modulus, group)
    two = _constant(modulus, group, 2)
    sigma = LaurentMatrix.from_rows(
        modulus,
        group,
        (
            (_poly(modulus, group, ((2, (0, 0)), (2, (-1, 0)))), zero, zero, zero),
            (_poly(modulus, group, ((2, (0, 0)), (2, (0, -1)))), zero, zero, zero),
            (zero, _poly(modulus, group, ((1, (0, 0)), (-1, (0, 1)))), two, zero),
            (zero, _poly(modulus, group, ((1, (0, 0)), (-1, (1, 0)))), zero, two),
        ),
    )
    tau = LaurentMatrix.from_rows(
        modulus,
        group,
        (
            (two, zero, zero, zero),
            (zero, two, zero, zero),
            (zero, _poly(modulus, group, ((1, (0, 0)), (-1, (0, 1)))), two, zero),
            (zero, _poly(modulus, group, ((1, (0, 0)), (-1, (1, 0)))), zero, two),
        ),
    )
    lambda_matrix = LaurentMatrix.from_rows(
        modulus,
        group,
        (
            (zero, zero, _constant(modulus, group, -1), zero),
            (zero, zero, zero, _constant(modulus, group, -1)),
            (_constant(modulus, group, 1), zero, zero, zero),
            (zero, _constant(modulus, group, 1), zero, zero),
        ),
    )
    epsilon = sigma.involution_transpose().matmul(lambda_matrix)
    tau_dagger = tau.involution_transpose()
    resolution = RubaYangZ4Resolution(sigma, tau, epsilon, tau_dagger)
    if not all(value for _, value in resolution.chain_identities()):
        raise ArithmeticError("Ruba--Yang Z4 canonical matrices fail d^2=0")
    return resolution


@dataclass(frozen=True)
class FiniteResolutionCheck:
    periods: Tuple[int, ...]
    chain_squared_zero: bool
    h1_invariant_factors: Tuple[int, ...]

    SCHEMA_ID = "mobility_toolkit.finite_resolution_check.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "chain_squared_zero": self.chain_squared_zero,
            "h1_invariant_factors": self.h1_invariant_factors,
            "periods": self.periods,
            "schema": self.SCHEMA_ID,
        }


def specialize_laurent_matrix(
    matrix: LaurentMatrix,
    periods: Sequence[int],
) -> SparseIntMatrix:
    """Evaluate a Laurent matrix on a finite periodic translation set."""

    periods = tuple(_integer(value, "period") for value in periods)
    if len(periods) != matrix.translation_group.free_rank:
        raise ValueError("period count must match the free translation rank")
    if matrix.translation_group.torsion_invariants:
        raise ValueError("finite specialization currently expects a free translation group")
    if any(value < 1 for value in periods):
        raise ValueError("periods must be positive")
    cells = tuple(itertools.product(*(range(value) for value in periods)))
    cell_index = {coordinate: index for index, coordinate in enumerate(cells)}
    cell_count = len(cells)
    entries = []
    for row, column, polynomial in matrix.entries:
        for term in polynomial.terms:
            for source_coordinate in cells:
                target_coordinate = tuple(
                    (coordinate + shift) % period
                    for coordinate, shift, period in zip(
                        source_coordinate, term.free_exponents, periods
                    )
                )
                target_row = row * cell_count + cell_index[target_coordinate]
                source_column = column * cell_count + cell_index[source_coordinate]
                entries.append((target_row, source_column, term.coefficient))
    return SparseIntMatrix(
        matrix.nrows * cell_count,
        matrix.ncols * cell_count,
        tuple(entries),
    )


def finite_resolution_check(
    resolution: RubaYangZ4Resolution,
    periods: Sequence[int],
    backend: Optional[FlintIntegerBackend] = None,
) -> FiniteResolutionCheck:
    backend = backend or FlintIntegerBackend()
    epsilon = specialize_laurent_matrix(resolution.epsilon, periods)
    tau_dagger = specialize_laurent_matrix(resolution.tau_dagger, periods)
    chain_zero = all(
        value % 4 == 0
        for _, _, value in tau_dagger.matmul(epsilon).entries
    )
    rank = epsilon.nrows
    middle = FiniteAbelianGroup.from_coordinate_orders((4,) * rank, backend)
    previous = FiniteGroupHomomorphism.create(middle, middle, epsilon, backend)
    following = FiniteGroupHomomorphism.create(middle, middle, tau_dagger, backend)
    numerator = following.kernel(backend)
    denominator = previous.image(backend)
    if not numerator.contains_subgroup(denominator, backend):
        raise ArithmeticError("finite specialized image is not contained in the kernel")
    quotient = numerator.quotient_by(denominator, backend)
    return FiniteResolutionCheck(
        tuple(periods),
        chain_zero,
        quotient.invariant_factors,
    )


@dataclass(frozen=True)
class RubaYangZ4BenchmarkValue:
    additive_invariant_factors: Tuple[int, ...]
    annihilator_generators: Tuple[LaurentPolynomial, ...]
    higher_charge_degrees_tested_zero: Tuple[int, ...]
    all_higher_zero_conditional_on_paper_resolution: bool
    explicit_generators: Tuple[str, ...]
    explicit_generators_are_cycles: bool
    explicit_nonzero_classes: Tuple[str, ...]
    explicit_generators_span_h1: bool
    native_composite_polynomial_ring_supported: bool
    integer_quotient_ring_workaround: bool
    finite_specializations: Tuple[FiniteResolutionCheck, ...]
    generic_composite_ext_promoted: bool = False

    SCHEMA_ID = "mobility_toolkit.ruba_yang_z4_benchmark_value.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "additive_invariant_factors": self.additive_invariant_factors,
            "annihilator_generators": self.annihilator_generators,
            "explicit_generators": self.explicit_generators,
            "explicit_generators_are_cycles": self.explicit_generators_are_cycles,
            "explicit_generators_span_h1": self.explicit_generators_span_h1,
            "explicit_nonzero_classes": self.explicit_nonzero_classes,
            "finite_specializations": self.finite_specializations,
            "generic_composite_ext_promoted": self.generic_composite_ext_promoted,
            "higher_charge_degrees_tested_zero": self.higher_charge_degrees_tested_zero,
            "integer_quotient_ring_workaround": self.integer_quotient_ring_workaround,
            "native_composite_polynomial_ring_supported": self.native_composite_polynomial_ring_supported,
            "all_higher_zero_conditional_on_paper_resolution": self.all_higher_zero_conditional_on_paper_resolution,
            "schema": self.SCHEMA_ID,
        }


def _m2_ring_definition(group: TranslationGroup, modulus: int) -> str:
    variables = []
    inverse_relations = []
    for index in range(1, group.free_rank + 1):
        variables.extend((f"x{index}", f"t{index}"))
        inverse_relations.append(f"x{index}*t{index}-1")
    return (
        f"A = ZZ[{','.join(variables)}]\n"
        f"R = A / ideal({modulus},{','.join(inverse_relations)})"
    )


def _marker_payload(stdout: str, marker: str) -> str:
    lines = [line.strip() for line in stdout.splitlines()]
    try:
        position = lines.index(marker)
    except ValueError as exc:
        raise RuntimeError(f"Macaulay2 output is missing marker {marker!r}") from exc
    for line in lines[position + 1 :]:
        if not line or re.match(r"^[io]\d+\s*[:=]", line):
            continue
        return line
    raise RuntimeError(f"Macaulay2 output has no payload after {marker!r}")


def _m2_bool(stdout: str, marker: str) -> bool:
    payload = _marker_payload(stdout, marker).lower()
    if payload not in {"true", "false"}:
        raise RuntimeError(f"expected Boolean after {marker}, found {payload!r}")
    return payload == "true"


def _m2_version(stderr: str) -> str:
    match = re.search(r"Macaulay2, version\s+([^\s]+)", stderr)
    return match.group(1) if match else "unreported"


def _native_composite_probe(timeout_seconds: float) -> Tuple[bool, str]:
    probe = run_macaulay2("R = ZZ/4[x1]\n", timeout_seconds)
    output = (probe["stderr"] + "\n" + probe["stdout"]).lower()
    if probe["exit_code"] == 0:
        return True, "native ZZ/4 polynomial ring constructed"
    if "not implemented yet for composite" in output:
        return False, "Macaulay2 reports ZZ/n polynomial rings unimplemented for composite n"
    raise RuntimeError("unexpected native composite-ring probe failure: " + output.strip())


def _z4_benchmark_script(resolution: RubaYangZ4Resolution) -> str:
    ring = _m2_ring_definition(resolution.sigma.translation_group, 4)
    return f"""{ring}
F = R^4
sigma = map(F,F,matrix(R,{resolution.sigma.render_m2_rows()}))
tau = map(F,F,matrix(R,{resolution.tau.render_m2_rows()}))
epsilon = map(F,F,matrix(R,{resolution.epsilon.render_m2_rows()}))
tauDagger = map(F,F,matrix(R,{resolution.tau_dagger.render_m2_rows()}))
print "VALUE:SIGMA_TAU_ZERO"
print (sigma*tau == 0*sigma)
print "VALUE:TAU_TAU_ZERO"
print (tau*tau == 0*tau)
print "VALUE:DUAL_ZERO"
print (tauDagger*epsilon == 0*epsilon)
print "VALUE:PERIODIC_DUAL_ZERO"
print (tauDagger*tauDagger == 0*tauDagger)
H1 = prune homology(tauDagger,epsilon)
print "VALUE:H1_NUMGENS"
print numgens H1
print "VALUE:H1_ANN"
print toString(generators gb ann H1)
H2 = prune homology(tauDagger,tauDagger)
print "VALUE:H2_NUMGENS"
print numgens H2
K = kernel tauDagger
B = image epsilon
G = image map(F,R^2,matrix(R,{{{{2,0}},{{0,2}},{{0,0}},{{0,0}}}}))
E = image map(F,R^1,matrix(R,{{{{2}},{{0}},{{0}},{{0}}}}))
M = image map(F,R^1,matrix(R,{{{{0}},{{2}},{{0}},{{0}}}}))
EM = image map(F,R^1,matrix(R,{{{{2}},{{2}},{{0}},{{0}}}}))
print "VALUE:GENERATORS_CYCLES"
print isSubset(G,K)
print "VALUE:E_BOUNDARY"
print isSubset(E,B)
print "VALUE:M_BOUNDARY"
print isSubset(M,B)
print "VALUE:EM_BOUNDARY"
print isSubset(EM,B)
print "VALUE:GENERATORS_SPAN"
print (numgens prune (K/(B+G)) == 0)
"""


def _parse_annihilator(
    payload: str,
    group: TranslationGroup,
) -> Tuple[LaurentPolynomial, ...]:
    match = re.search(r"matrix\s*\{\{(.*)\}\}", payload)
    if not match:
        raise RuntimeError(f"could not parse annihilator matrix: {payload!r}")
    generators = tuple(
        parse_legacy_laurent(item.strip(), 4, group)
        for item in match.group(1).split(",")
        if item.strip()
    )
    canonical = {canonical_json(item): item for item in generators}
    return tuple(canonical[key] for key in sorted(canonical))


def run_ruba_yang_z4_resolution_benchmark(
    finite_periods: Sequence[Sequence[int]] = ((1, 1), (2, 1), (2, 2)),
    timeout_seconds: float = 120.0,
) -> ComputationResult:
    """Run the fixed Sec. 7.8 resolution benchmark, never generic Ext."""

    resolution = ruba_yang_z4_resolution()
    input_data = {
        "model": "ruba-yang-2204.06023v3-sec7.8-eq99-103",
        "resolution": resolution,
        "finite_periods": tuple(tuple(period) for period in finite_periods),
    }
    if not describe_m2_backend()["available"]:
        return ComputationResult(
            operation="periodic.experimental.paper_resolution_z4",
            input_data=input_data,
            value=None,
            exactness=Exactness.UNSUPPORTED,
            theorem_scope="Fixed Ruba--Yang Sec. 7.8 benchmark only.",
            diagnostics=("Macaulay2 backend is unavailable",),
        )
    native_supported, native_diagnostic = _native_composite_probe(timeout_seconds)
    execution = run_macaulay2(_z4_benchmark_script(resolution), timeout_seconds)
    if execution["exit_code"] != 0:
        raise RuntimeError(
            "Macaulay2 paper-resolution benchmark failed: "
            + (execution["stderr"] or execution["stdout"])
        )
    stdout = execution["stdout"]
    chain_checks = {
        "sigma_tau": _m2_bool(stdout, "VALUE:SIGMA_TAU_ZERO"),
        "tau_tau": _m2_bool(stdout, "VALUE:TAU_TAU_ZERO"),
        "tau_dagger_epsilon": _m2_bool(stdout, "VALUE:DUAL_ZERO"),
        "tau_dagger_squared": _m2_bool(stdout, "VALUE:PERIODIC_DUAL_ZERO"),
    }
    h1_numgens = int(_marker_payload(stdout, "VALUE:H1_NUMGENS"))
    h2_numgens = int(_marker_payload(stdout, "VALUE:H2_NUMGENS"))
    cycles = _m2_bool(stdout, "VALUE:GENERATORS_CYCLES")
    boundaries = {
        "e": _m2_bool(stdout, "VALUE:E_BOUNDARY"),
        "m": _m2_bool(stdout, "VALUE:M_BOUNDARY"),
        "e+m": _m2_bool(stdout, "VALUE:EM_BOUNDARY"),
    }
    spans = _m2_bool(stdout, "VALUE:GENERATORS_SPAN")
    annihilator = _parse_annihilator(
        _marker_payload(stdout, "VALUE:H1_ANN"),
        resolution.sigma.translation_group,
    )
    finite_checks = tuple(
        finite_resolution_check(resolution, period) for period in finite_periods
    )
    failures = []
    if not all(chain_checks.values()):
        failures.append("Macaulay2 rejected one or more chain identities")
    if h1_numgens != 2:
        failures.append(f"H^1 has {h1_numgens} generators instead of two")
    if h2_numgens != 0:
        failures.append("periodic H^2 is nonzero")
    if not cycles or any(boundaries.values()) or not spans:
        failures.append("explicit e,m class witness failed")
    if any(
        not check.chain_squared_zero or check.h1_invariant_factors != (2, 2)
        for check in finite_checks
    ):
        failures.append("independent finite FGA specialization disagrees with Z2+Z2")
    if failures:
        raise ArithmeticError("; ".join(failures))
    value = RubaYangZ4BenchmarkValue(
        additive_invariant_factors=(2, 2),
        annihilator_generators=annihilator,
        higher_charge_degrees_tested_zero=(1,),
        all_higher_zero_conditional_on_paper_resolution=True,
        explicit_generators=("e=(2,0,0,0)", "m=(0,2,0,0)"),
        explicit_generators_are_cycles=cycles,
        explicit_nonzero_classes=tuple(name for name, is_boundary in boundaries.items() if not is_boundary),
        explicit_generators_span_h1=spans,
        native_composite_polynomial_ring_supported=native_supported,
        integer_quotient_ring_workaround=True,
        finite_specializations=finite_checks,
    )
    return ComputationResult(
        operation="periodic.experimental.paper_resolution_z4",
        input_data=input_data,
        value=value,
        exactness=Exactness.EXPERIMENTAL,
        assumptions=(
            "the explicit infinite periodic resolution in 2204.06023v3 Eq. (101) is exact",
            "Macaulay2 integer quotient ring models Z4 Laurent coefficients",
        ),
        theorem_scope=(
            "Fixed Ruba--Yang Sec. 7.8 Eqs. (99)--(103) benchmark; "
            "does not validate generic composite Ext."
        ),
        certificate_level=CertificateLevel.STANDARD,
        certificate={
            "canonical_resolution_hash": canonical_hash(resolution.SCHEMA_ID, resolution),
            "chain_identities_python": dict(resolution.chain_identities()),
            "chain_identities_macaulay2": chain_checks,
            "explicit_class_witness": {
                "cycles": cycles,
                "boundaries": boundaries,
                "spans": spans,
            },
            "all_higher_zero_statement": (
                "If the infinite periodic sequence in 2204.06023v3 Eq. (101) is an "
                "exact resolution, the repeated verified H^2 computation proves Q^i=0 "
                "for every i>0."
            ),
            "finite_fga_specializations": finite_checks,
        },
        verification=(
            ("h1_generator_count", h1_numgens),
            ("h2_generator_count", h2_numgens),
            ("native_composite_ring_probe", native_diagnostic),
        ),
        backend_provenance=BackendProvenance(
            backend="Macaulay2",
            algorithm="explicit-periodic-resolution-homology",
            version=_m2_version(execution["stderr"]),
            parameters=(("coefficient_model", "ZZ-polynomial-quotient-by-4"),),
        ),
        warnings=tuple(
            warning
            for warning in (
                (
                    "Native composite polynomial rings were unavailable in the probed Macaulay2; "
                    "an integer quotient ring is used."
                    if not native_supported
                    else "The benchmark still uses the independently checked integer quotient-ring model."
                ),
                "All-higher-degree vanishing is conditional on exactness of the paper's explicit infinite periodic resolution.",
                "General composite and nonuniform Ext remain outside this benchmark.",
            )
        ),
    )


@dataclass(frozen=True)
class NonuniformQuasiFreeToyValue:
    local_orders: Tuple[int, ...]
    coefficient_modulus: int
    ext_degrees_tested_zero: Tuple[int, ...]
    finite_additive_checks: Tuple[Tuple[int, Tuple[int, ...]], ...]
    generic_nonuniform_ext_supported: bool
    blocker: str

    SCHEMA_ID = "mobility_toolkit.nonuniform_quasi_free_toy_value.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "blocker": self.blocker,
            "coefficient_modulus": self.coefficient_modulus,
            "ext_degrees_tested_zero": self.ext_degrees_tested_zero,
            "finite_additive_checks": self.finite_additive_checks,
            "generic_nonuniform_ext_supported": self.generic_nonuniform_ext_supported,
            "local_orders": self.local_orders,
            "schema": self.SCHEMA_ID,
        }


def _nonuniform_toy_script() -> str:
    return """A = ZZ[x1,t1]
R = A / ideal(4,x1*t1-1)
F0 = R^2
F1 = R^1
d1dual = map(F1,F0,matrix(R,{{2,0}}))
d2dual = map(F1,F1,matrix(R,{{2}}))
print "VALUE:TOY_D2_ZERO"
print (d2dual*d1dual == 0*d1dual)
H1 = prune homology(d2dual,d1dual)
H2 = prune homology(d2dual,d2dual)
print "VALUE:TOY_H1_NUMGENS"
print numgens H1
print "VALUE:TOY_H2_NUMGENS"
print numgens H2
"""


def _finite_nonuniform_toy_check(backend: FlintIntegerBackend) -> Tuple[int, ...]:
    source = FiniteAbelianGroup.from_coordinate_orders((4, 4), backend)
    middle = FiniteAbelianGroup.from_coordinate_orders((4,), backend)
    d1 = FiniteGroupHomomorphism.create(
        source,
        middle,
        SparseIntMatrix.from_rows(((2, 0),)),
        backend,
    )
    d2 = FiniteGroupHomomorphism.create(
        middle,
        middle,
        SparseIntMatrix.from_rows(((2,),)),
        backend,
    )
    numerator = d2.kernel(backend)
    denominator = d1.image(backend)
    return numerator.quotient_by(denominator, backend).invariant_factors


def run_nonuniform_quasi_free_toy_benchmark(
    timeout_seconds: float = 120.0,
) -> ComputationResult:
    """Test Lemma 20 on ``Z2[Lambda] + Z4[Lambda]`` over a Z4 group ring."""

    input_data = {
        "module": "Z2[Lambda] direct-sum Z4[Lambda]",
        "local_orders": (2, 4),
        "coefficient_modulus": 4,
        "resolution": "R --2--> R --2--> R for the Z2 summand; Z4 summand free",
    }
    if not describe_m2_backend()["available"]:
        return ComputationResult(
            operation="periodic.experimental.nonuniform_quasi_free_toy",
            input_data=input_data,
            value=None,
            exactness=Exactness.UNSUPPORTED,
            theorem_scope="Fixed Lemma 20 quasi-free toy module.",
            diagnostics=("Macaulay2 backend is unavailable",),
        )
    execution = run_macaulay2(_nonuniform_toy_script(), timeout_seconds)
    if execution["exit_code"] != 0:
        raise RuntimeError(
            "Macaulay2 nonuniform toy benchmark failed: "
            + (execution["stderr"] or execution["stdout"])
        )
    stdout = execution["stdout"]
    chain_zero = _m2_bool(stdout, "VALUE:TOY_D2_ZERO")
    h1_numgens = int(_marker_payload(stdout, "VALUE:TOY_H1_NUMGENS"))
    h2_numgens = int(_marker_payload(stdout, "VALUE:TOY_H2_NUMGENS"))
    finite_factors = _finite_nonuniform_toy_check(FlintIntegerBackend())
    if not chain_zero or h1_numgens or h2_numgens or finite_factors:
        raise ArithmeticError("nonuniform quasi-free toy resolution failed exactness checks")
    blocker = (
        "No validated algorithm constructs a quasi-free resolution of a general "
        "nonuniform stabilizer quotient or its dual symplectic differential; this "
        "fixed Lemma 20 toy cannot promote generic nonuniform Ext."
    )
    value = NonuniformQuasiFreeToyValue(
        local_orders=(2, 4),
        coefficient_modulus=4,
        ext_degrees_tested_zero=(1, 2),
        finite_additive_checks=((1, finite_factors),),
        generic_nonuniform_ext_supported=False,
        blocker=blocker,
    )
    return ComputationResult(
        operation="periodic.experimental.nonuniform_quasi_free_toy",
        input_data=input_data,
        value=value,
        exactness=Exactness.EXPERIMENTAL,
        assumptions=("Ruba--Yang Lemma 20 periodic resolution",),
        theorem_scope=(
            "Fixed quasi-free module Z2[Lambda] direct-sum Z4[Lambda]; "
            "not a generic stabilizer charge-module computation."
        ),
        certificate_level=CertificateLevel.STANDARD,
        certificate={
            "dual_chain_squared_zero": chain_zero,
            "macaulay2_h1_numgens": h1_numgens,
            "macaulay2_h2_numgens": h2_numgens,
            "finite_fga_h1_invariants": finite_factors,
        },
        verification=(("generic_nonuniform_ext_supported", False),),
        backend_provenance=BackendProvenance(
            backend="Macaulay2+python-flint",
            algorithm="fixed-quasi-free-periodic-resolution",
            version=_m2_version(execution["stderr"]),
        ),
        warnings=(blocker,),
    )


__all__ = [
    "FiniteResolutionCheck",
    "LaurentMatrix",
    "NonuniformQuasiFreeToyValue",
    "RubaYangZ4BenchmarkValue",
    "RubaYangZ4Resolution",
    "finite_resolution_check",
    "ruba_yang_z4_resolution",
    "run_nonuniform_quasi_free_toy_benchmark",
    "run_ruba_yang_z4_resolution_benchmark",
    "specialize_laurent_matrix",
]
