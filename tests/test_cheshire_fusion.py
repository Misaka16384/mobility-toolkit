from dataclasses import replace
from hashlib import sha256

import pytest

from mobility_toolkit.core import Exactness, canonical_json
from mobility_toolkit.defects.cheshire import OpenSegment, RationalFactor
from mobility_toolkit.defects.cheshire_fusion import (
    CheshireDefectNetwork,
    CheshireNetworkEdge,
    CheshireNetworkNode,
    EndpointBinding,
    NetworkNodeKind,
    component_count_topology_guard,
    construct_static_toric_cheshire_fusion,
)
from mobility_toolkit.finite import FlintIntegerBackend
from mobility_toolkit.geometry import rectangular_cubical_complex


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _digest(value):
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def test_two_open_segments_have_exact_static_fusion_but_no_circuit_claim(backend):
    ball = rectangular_cubical_complex((4, 1, 1))
    left = OpenSegment.from_cube_bases(
        ball, "left", ((0, 0, 0), (1, 0, 0))
    )
    right = OpenSegment.from_cube_bases(
        ball, "right", ((2, 0, 0), (3, 0, 0))
    )
    fused = OpenSegment.from_cube_bases(
        ball,
        "fused",
        ((0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)),
    )

    result = construct_static_toric_cheshire_fusion(
        "two-segments-to-one", ball, (left, right), (fused,), backend
    )

    assert result.static_candidate_exactness is Exactness.CERTIFIED_EXACT
    assert result.finite_depth_circuit.status is Exactness.UNSUPPORTED
    assert result.finite_depth_circuit.circuit is None
    assert result.certificate.structurally_verified
    assert result.local_hamiltonian_delta.stratum_coverage_verified
    assert result.fixed_sector_hamiltonian_delta.stratum_coverage_verified
    assert result.logical_counting.local_codespace_ratio_after_over_before == (
        RationalFactor(1, 2)
    )
    assert result.logical_counting.component_only_hypothesis_matches
    assert len(result.defect_algebra_and_termination) == 3
    assert all(
        item.charge_terminates_on_defect
        and not item.magnetic_terminates_on_defect
        for item in result.defect_algebra_and_termination
    )
    assert result.before_local_code.basic_validation_errors() == ()
    assert result.after_local_code.basic_validation_errors() == ()


def test_junction_network_schema_binds_physical_endpoints_without_claiming_completion():
    ball = rectangular_cubical_complex((6, 1, 1))
    lines = tuple(
        OpenSegment.from_cube_bases(
            ball,
            name,
            ((left, 0, 0), (right, 0, 0)),
        ).line
        for name, left, right in (
            ("a", 0, 1),
            ("b", 2, 3),
            ("c", 4, 5),
        )
    )
    junction = CheshireNetworkNode(
        "junction",
        NetworkNodeKind.JUNCTION,
        (lines[0].endpoint_cube_ids[1], lines[1].endpoint_cube_ids[0], lines[2].endpoint_cube_ids[0]),
        (
            EndpointBinding("a", lines[0].endpoint_cube_ids[1]),
            EndpointBinding("b", lines[1].endpoint_cube_ids[0]),
            EndpointBinding("c", lines[2].endpoint_cube_ids[0]),
        ),
    )
    leaves = tuple(
        CheshireNetworkNode(
            f"leaf:{defect_id}",
            NetworkNodeKind.ENDPOINT,
            (cube_id,),
            (EndpointBinding(defect_id, cube_id),),
        )
        for defect_id, cube_id in (
            ("a", lines[0].endpoint_cube_ids[0]),
            ("b", lines[1].endpoint_cube_ids[1]),
            ("c", lines[2].endpoint_cube_ids[1]),
        )
    )
    network = CheshireDefectNetwork(
        leaves + (junction,),
        tuple(
            CheshireNetworkEdge(
                f"edge:{line.defect_id}",
                line.defect_id,
                line.topology,
                (f"leaf:{line.defect_id}", "junction"),
            )
            for line in lines
        ),
        "user-supplied three-leg junction stratum",
    )

    network.validate_against(lines)
    assert network.has_junctions
    assert _digest(network)

    with pytest.raises(ValueError, match="unreferenced nodes"):
        replace(network, edges=network.edges[:-1])


def test_resealed_semantic_counting_tamper_is_rejected_by_replay(backend):
    ball = rectangular_cubical_complex((2, 1, 1))
    before = OpenSegment.from_cube_bases(
        ball, "before", ((0, 0, 0), (1, 0, 0))
    )
    after = OpenSegment.from_cube_bases(
        ball, "after", ((0, 0, 0), (1, 0, 0))
    )
    result = construct_static_toric_cheshire_fusion(
        "semantic-tamper", ball, (before,), (after,), backend
    )
    bad_counting = replace(
        result.logical_counting,
        after_local_codespace_dimension=(
            result.logical_counting.after_local_codespace_dimension * 2
        ),
    )
    bad_counting_hash = _digest(bad_counting)
    transcript = tuple(
        (key, bad_counting_hash if key == "logical_counting" else value)
        for key, value in result.certificate.transcript
    )
    resealed = replace(
        result.certificate,
        logical_counting_hash=bad_counting_hash,
        transcript=transcript,
        transcript_hash=_digest(transcript),
    )
    assert resealed.structurally_verified
    tampered = replace(
        result, logical_counting=bad_counting, certificate=resealed
    )

    with pytest.raises(ValueError, match="semantic replay"):
        tampered.verify_certificate(backend)


def test_topology_guard_refutes_component_count_only_rule_for_exact_finite_counts():
    # These are exact finite logical dimensions already checked by the Phase-4
    # open-segment (2) and noncontractible T^3 loop (4) benchmarks.  The guard
    # deliberately consumes the measured counts instead of re-running their
    # expensive finite stabilizer analyses here.
    actual, predicted, matches = component_count_topology_guard(2, 4, 1, 1)

    assert actual == RationalFactor(2, 1)
    assert predicted == RationalFactor(1, 1)
    assert not matches
