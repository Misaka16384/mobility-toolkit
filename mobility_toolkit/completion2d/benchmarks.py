"""Source-locked finite toric-code cut completions used as physics benchmarks."""

from __future__ import annotations

from dataclasses import dataclass

from mobility_toolkit.anyons2d import zd_toric_metric_model
from mobility_toolkit.completion2d.local import (
    CondensateStringLift,
    FiniteBoundaryLocalityDomain,
    LocalBoundaryCompletionRequest,
    NamedPauliTerm,
)
from mobility_toolkit.core import LocalPauliTerm, PauliModule
from mobility_toolkit.finite import FiniteIntegerBackend
from mobility_toolkit.geometry import (
    cellular_stabilizer_code,
    rectangular_cubical_complex,
)


@dataclass(frozen=True)
class ToricCutCompletionBenchmark:
    """One finite Bravyi--Kitaev rough or smooth cut completion."""

    modulus: int
    boundary_kind: str
    request: LocalBoundaryCompletionRequest
    source: str

    SCHEMA_ID = "mobility_toolkit.toric_cut_completion_benchmark_2d.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "boundary_kind": self.boundary_kind,
            "modulus": self.modulus,
            "request": self.request,
            "schema": self.SCHEMA_ID,
            "source": self.source,
        }


def _support(operator) -> set:
    return {term.site_id for term in operator.terms}


def _project_operator(operator, module, retained_sites):
    return module.operator(
        tuple(term for term in operator.terms if term.site_id in retained_sites),
        phase=operator.phase,
    )


def zd_toric_cut_completion_benchmark(
    modulus: int,
    boundary_kind: str,
    backend: FiniteIntegerBackend,
) -> ToricCutCompletionBenchmark:
    """Build an explicit left-square cut of a 2-by-1 cellular toric patch.

    ``rough`` retains the projected Z-type cut checks and supplies a terminating
    electric Z string. ``smooth`` retains projected X-type cut checks and
    supplies a terminating magnetic X string.
    """

    if boundary_kind not in {"rough", "smooth"}:
        raise ValueError("boundary_kind must be rough or smooth")
    parent = rectangular_cubical_complex((2, 1))
    cellular = cellular_stabilizer_code(parent.chain_complex, 1, modulus)
    retained_cells = tuple(
        cell
        for cell in parent.cells_by_dimension[1]
        if cell.base[0] + (1 if 0 in cell.varying_axes else 0) <= 1
    )
    retained_site_ids = {cell.cell_id for cell in retained_cells}
    retained_module = PauliModule(
        tuple(
            cellular.code.pauli_module.system(site_id)
            for site_id in sorted(retained_site_ids)
        )
    )
    retained_records = tuple(
        record
        for record in cellular.check_records
        if _support(record.operator) <= retained_site_ids
    )
    cut_records = tuple(
        record
        for record in cellular.check_records
        if _support(record.operator) & retained_site_ids
        and not _support(record.operator) <= retained_site_ids
    )
    bulk_terms = tuple(
        NamedPauliTerm(
            f"bulk:{record.pauli_kind}:{record.cell_id}",
            _project_operator(record.operator, retained_module, retained_site_ids),
        )
        for record in retained_records
    )
    retained_kind = "z" if boundary_kind == "rough" else "x"
    boundary_terms = tuple(
        NamedPauliTerm(
            f"boundary:{record.pauli_kind}:{record.cell_id}",
            _project_operator(record.operator, retained_module, retained_site_ids),
        )
        for record in cut_records
        if record.pauli_kind == retained_kind
        and _project_operator(
            record.operator, retained_module, retained_site_ids
        ).terms
    )
    if not boundary_terms:
        raise ArithmeticError("toric cut did not produce a boundary completion term")

    if boundary_kind == "rough":
        string_cell = next(
            cell
            for cell in retained_cells
            if cell.varying_axes == (0,) and cell.base == (0, 0)
        )
        anyon = (1, 0)
        string_operator = retained_module.operator(
            (LocalPauliTerm.cyclic(string_cell.cell_id, z=1),)
        )
        string_label = "electric_e_to_rough_boundary"
    else:
        string_cell = next(
            cell
            for cell in retained_cells
            if cell.varying_axes == (1,) and cell.base == (1, 0)
        )
        anyon = (0, 1)
        string_operator = retained_module.operator(
            (LocalPauliTerm.cyclic(string_cell.cell_id, x=1),)
        )
        string_label = "magnetic_m_to_smooth_boundary"

    completed_terms = bulk_terms + boundary_terms
    remote = tuple(
        item.term_id
        for item in completed_terms
        if not string_operator.commutes_with(item.operator)
    )
    if len(remote) != 1 or not remote[0].startswith("bulk:"):
        raise ArithmeticError(
            "the finite toric benchmark string does not have one remote bulk endpoint"
        )

    coordinates = []
    depths = []
    for cell in retained_cells:
        coordinate = tuple(
            2 * cell.base[axis] + (1 if axis in cell.varying_axes else 0)
            for axis in range(2)
        )
        coordinates.append((cell.cell_id, coordinate))
        depths.append((cell.cell_id, abs(2 - coordinate[0])))
    boundary_site_ids = tuple(
        sorted(site_id for site_id, depth in depths if depth <= 1)
    )
    max_boundary_support = max(len(_support(item.operator)) for item in boundary_terms)
    coordinate_map = dict(coordinates)
    max_boundary_diameter = max(
        (
            max(
                max(
                    abs(
                        coordinate_map[left][axis]
                        - coordinate_map[right][axis]
                    )
                    for axis in range(2)
                )
                for left in _support(item.operator)
                for right in _support(item.operator)
            )
            if len(_support(item.operator)) > 1
            else 0
        )
        for item in boundary_terms
    )
    locality = FiniteBoundaryLocalityDomain(
        window_label=f"z{modulus}-left-square-of-2x1-parent-{boundary_kind}",
        site_coordinates=tuple(coordinates),
        boundary_site_ids=boundary_site_ids,
        site_depths=tuple(depths),
        max_completion_depth=1,
        max_boundary_term_sites=max_boundary_support,
        max_boundary_term_diameter=max_boundary_diameter,
        max_short_string_sites=1,
    )
    request = LocalBoundaryCompletionRequest(
        metric=zd_toric_metric_model(modulus, backend).metric,
        pauli_module=retained_module,
        bulk_terms=bulk_terms,
        boundary_terms=boundary_terms,
        string_lifts=(
            CondensateStringLift(
                string_label,
                anyon,
                string_operator,
                remote,
            ),
        ),
        locality_domain=locality,
        source_scope=(
            "Bravyi--Kitaev cellular Z_d toric code on a 2x1 parent patch, "
            "literally cut to its closed left square; mutually commuting cut "
            f"checks selected for the {boundary_kind} completion"
        ),
        assumptions=(
            "finite cellular patch",
            "uniform composite or prime Z_d Pauli model",
        ),
    )
    return ToricCutCompletionBenchmark(
        modulus,
        boundary_kind,
        request,
        "Bravyi--Kitaev quant-ph/9811052; generalized Z_d finite cellular realization",
    )


__all__ = [
    "ToricCutCompletionBenchmark",
    "zd_toric_cut_completion_benchmark",
]
