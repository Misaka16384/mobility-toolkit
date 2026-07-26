import pytest

from mobility_toolkit.boundary_halfspace import (
    AncillaBound,
    BoundedPeriodicSearchDomain,
    GeneratorSupportBound,
    OrientedHalfSpace,
    PrimitiveNormal,
    ResourceBound,
    SearchSpaceCertificate,
    SearchTermination,
    halfspace_capability_report,
)
from mobility_toolkit.core.canonical import canonical_hash, canonical_json
from mobility_toolkit.core.results import Exactness


def _domain(candidate_families=None):
    kwargs = {}
    if candidate_families is not None:
        kwargs["candidate_families"] = candidate_families
    return BoundedPeriodicSearchDomain(
        half_space=OrientedHalfSpace(PrimitiveNormal.from_integer((2, 3, 5))),
        unit_cell_period=(2, 3),
        support_bound=GeneratorSupportBound(
            tangent_radii=(4, 5), max_inward_depth=6, max_sites_per_term=7
        ),
        completion_depth=8,
        ancilla_bound=AncillaBound(
            max_sites_per_unit_cell=2,
            allowed_local_orders=(4, 2, 4),
            max_cyclic_factors_per_site=3,
        ),
        coefficient_domain="uniform-prime:F2",
        **kwargs,
    )


def test_e2_domain_canonically_records_every_finite_bound_and_exclusion():
    domain = _domain(
        ("local_hamiltonian_completions", "translation_compatible_submodules")
    )
    payload = canonical_json(domain)

    assert '"unit_cell_period":[2,3]' in payload
    assert '"tangent_radii":[4,5]' in payload
    assert '"max_inward_depth":6' in payload
    assert '"completion_depth":8' in payload
    assert '"max_sites_per_unit_cell":2' in payload
    assert "including smaller fundamental periods" in domain.enumerated_scope[1]
    assert "symbolic thermodynamic completeness (E3)" in domain.excluded_scope
    assert "L_H, P_boundary, relative Ext, and quasi-symplectic boundary modules" in (
        domain.excluded_scope
    )


def test_e2_domain_hash_is_independent_of_set_like_input_order():
    first = _domain(
        ("translation_compatible_submodules", "local_hamiltonian_completions")
    )
    second = _domain(
        ("local_hamiltonian_completions", "translation_compatible_submodules")
    )
    assert canonical_hash("e2-domain", first) == canonical_hash("e2-domain", second)


def test_exhausted_certificate_is_bounded_exact_only_for_known_total():
    certificate = SearchSpaceCertificate(
        domain=_domain(),
        enumerator="lexicographic-e2",
        enumerator_version="1",
        candidate_encoding="canonical-generator-matrix-v1",
        enumeration_order="unit-cell/support/phase lexicographic",
        resource_bound=ResourceBound(
            max_candidates=1000,
            max_completions=100,
            max_wall_time_ms=5000,
            max_memory_bytes=1_000_000,
        ),
        termination=SearchTermination.EXHAUSTED,
        visited_candidates=120,
        accepted_candidates=9,
        total_candidates=120,
        completed_shards=("b", "a"),
    )
    assert certificate.exactness == Exactness.BOUNDED_EXACT
    assert certificate.bounded_complete
    assert certificate.pending_shards == ()
    assert "the unvisited remainder" not in certificate.unenumerated_scope
    assert '"exactness":"bounded_exact"' in canonical_json(certificate)

    with pytest.raises(ValueError, match="visited == known total"):
        SearchSpaceCertificate(
            domain=_domain(),
            enumerator="lexicographic-e2",
            enumerator_version="1",
            candidate_encoding="v1",
            enumeration_order="lexicographic",
            resource_bound=ResourceBound(max_candidates=120),
            termination=SearchTermination.EXHAUSTED,
            visited_candidates=119,
            accepted_candidates=9,
            total_candidates=120,
        )


def test_resource_limited_certificate_does_not_claim_search_completeness():
    certificate = SearchSpaceCertificate(
        domain=_domain(),
        enumerator="lexicographic-e2",
        enumerator_version="1",
        candidate_encoding="canonical-generator-matrix-v1",
        enumeration_order="unit-cell/support/phase lexicographic",
        resource_bound=ResourceBound(max_candidates=70),
        termination=SearchTermination.RESOURCE_LIMIT,
        visited_candidates=70,
        accepted_candidates=5,
        total_candidates=120,
        completed_shards=("000",),
        pending_shards=("001", "002"),
    )
    assert certificate.exactness == Exactness.EXPERIMENTAL
    assert not certificate.bounded_complete
    assert certificate.unenumerated_scope[0] == (
        "the unvisited remainder of the declared E2 search domain"
    )


def test_search_domain_validates_tangent_rank_and_ancilla_orders():
    with pytest.raises(ValueError, match="period rank"):
        BoundedPeriodicSearchDomain(
            half_space=OrientedHalfSpace(PrimitiveNormal((1, 0, 0))),
            unit_cell_period=(1,),
            support_bound=GeneratorSupportBound((1, 1), 1, 2),
            completion_depth=1,
            ancilla_bound=AncillaBound(0),
            coefficient_domain="uniform-prime:F2",
        )
    with pytest.raises(ValueError, match="requires"):
        AncillaBound(max_sites_per_unit_cell=1)


def test_phase6_capability_reports_lh_but_not_full_boundary_module_engine():
    report = halfspace_capability_report()
    assert report.exact_lattice_geometry
    assert report.bounded_periodic_domain_schema
    assert not report.bounded_periodic_enumerator
    assert report.uniform_prime_lh_contraction
    assert not report.symbolic_halfspace_modules
    assert set(report.unsupported_symbolic_outputs) >= {
        "P_boundary",
        "relative_Ext",
        "quasi_symplectic_pairing",
    }
    assert "L_H" not in report.unsupported_symbolic_outputs
    payload = canonical_json(report)
    assert '"uniform_prime_lh_contraction":true' in payload
    assert '"symbolic_halfspace_modules":false' in payload
    assert '"bounded_periodic_enumerator":false' in payload
