from dataclasses import replace

import pytest

from mobility_toolkit.core import canonical_json
from mobility_toolkit.defects.cheshire import ClosedLoop, OpenSegment
from mobility_toolkit.defects.cheshire_synthesis import (
    CondensationCandidate,
    FiniteTubeLineDefectFamily,
    StaticRadiusSample,
    enumerate_cheshire_species,
    synthesize_tubular_to_line,
    toric_cheshire_condensation_candidate,
    verify_cheshire_species_enumeration,
    verify_tubular_to_line_synthesis,
)
from mobility_toolkit.finite import FlintIntegerBackend
from mobility_toolkit.geometry import rectangular_cubical_complex


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


@pytest.fixture(scope="module")
def toric_references(backend):
    open_ball = rectangular_cubical_complex((2, 1, 1))
    segment = OpenSegment.from_cube_bases(
        open_ball, "open", ((0, 0, 0), (1, 0, 0))
    )
    loop_ball = rectangular_cubical_complex((2, 2, 1))
    loop = ClosedLoop.from_cube_bases(
        loop_ball,
        "loop",
        ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)),
    )
    return (
        toric_cheshire_condensation_candidate(
            open_ball, (segment,), backend, "open"
        ),
        toric_cheshire_condensation_candidate(
            loop_ball, (loop,), backend, "closed"
        ),
    )


def test_source_locked_open_and_closed_toric_species_are_reproduced(toric_references):
    result = enumerate_cheshire_species(toric_references, (0,))

    assert result.certificate.bounded_complete
    assert tuple(item.candidate_id for item in result.syntheses) == ("open", "closed")
    assert all(item.finite_invariants_preserved for item in result.syntheses)
    assert all(not item.circuit_constructed for item in result.syntheses)
    assert all(not item.phase_equivalence_claimed for item in result.syntheses)
    assert verify_cheshire_species_enumeration(result)
    assert "thermodynamic" in result.certificate.theorem_scope
    assert "cheshire_species_search_certificate" in canonical_json(result)


def test_finite_radius_scaling_preserves_only_declared_static_invariants(
    toric_references,
):
    candidate = toric_references[0]
    # On this finite patch radius one saturates the same exact tube support as
    # radius zero; the reference builder reuses the certified analysis while
    # still recording both finite radius samples.
    result = synthesize_tubular_to_line(candidate, (1, 0))

    assert result.finite_invariants_preserved
    assert tuple(snapshot.radius_lattice_steps for snapshot in result.snapshots) == (
        1,
        0,
    )
    assert result.adjacent_certificates[0].verified
    assert verify_tubular_to_line_synthesis(result)
    assert "phase equivalence" in result.theorem_scope


def test_explicit_finite_family_entry_point_matches_candidate_route(toric_references):
    analysis = toric_references[0].builder(0)
    family = FiniteTubeLineDefectFamily(
        "explicit-open",
        (StaticRadiusSample(0, analysis),),
    )
    result = synthesize_tubular_to_line(family)

    assert result.finite_invariants_preserved
    assert result.snapshots[0].charge_termination == (True,)
    assert result.snapshots[0].magnetic_termination == (False,)


def test_tampered_snapshot_and_resealed_search_decision_fail_semantic_replay(
    toric_references,
):
    synthesis = synthesize_tubular_to_line(toric_references[0], (0,))
    bad_snapshot = replace(
        synthesis.snapshots[0],
        defect_local_invariant_factors=(),
    )
    tampered = replace(synthesis, snapshots=(bad_snapshot,))
    assert not verify_tubular_to_line_synthesis(tampered)

    search = enumerate_cheshire_species((toric_references[0],), (0,))
    decision = replace(
        search.certificate.decisions[0],
        synthesis_hash="0" * 64,
    )
    domain = search.certificate.domain
    bad_certificate = replace(
        search.certificate,
        decisions=(decision,),
    )
    bad_search = replace(search, certificate=bad_certificate)
    assert not verify_cheshire_species_enumeration(bad_search)
    assert domain.candidate_list_complete_by_declaration


def test_invalid_termination_candidate_is_rejected_with_complete_list_certificate(
    toric_references,
):
    source = toric_references[0]
    invalid = CondensationCandidate(
        "wrong-magnetic-claim",
        source.builder,
        expected_magnetic_termination=True,
    )
    result = enumerate_cheshire_species((source, invalid), (0,))

    assert result.certificate.bounded_complete
    assert tuple(decision.accepted for decision in result.certificate.decisions) == (
        True,
        False,
    )
    assert "radius-step certificates failed" in (
        result.certificate.decisions[1].rejection_reason
    )
    assert verify_cheshire_species_enumeration(result)


@pytest.mark.parametrize("radii", ((), (1,), (0, 1), (1, 1, 0), (-1,)))
def test_tubular_to_line_radius_domain_is_explicit_and_strict(
    toric_references, radii
):
    with pytest.raises(ValueError):
        synthesize_tubular_to_line(toric_references[0], radii)


def test_boundary_search_evidence_does_not_replace_condensation_builder():
    class CompleteE2:
        bounded_complete = True

    with pytest.raises(TypeError, match="builder"):
        CondensationCandidate(
            "missing-builder",
            None,
            boundary_search_certificate=CompleteE2(),
        )
