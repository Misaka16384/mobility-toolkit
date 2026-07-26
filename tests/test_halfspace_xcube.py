from dataclasses import replace
from fractions import Fraction

from mobility_toolkit.boundary_halfspace import (
    BoundaryToBulkBehavior,
    PrimitiveNormal,
    XCUBE_RUBA_YANG_EQ140_ROWS,
    XCUBE_RUBA_YANG_SOURCE,
    xcube_orientation_benchmark,
)
from mobility_toolkit.core import Exactness, canonical_json


def test_xcube_source_lock_freezes_eq140_literal_presentation():
    result = xcube_orientation_benchmark(PrimitiveNormal((0, 0, 1)))
    certificate = result.certificate

    assert tuple(sorted(certificate.observed_presentation_rows)) == tuple(
        sorted(XCUBE_RUBA_YANG_EQ140_ROWS)
    )
    assert XCUBE_RUBA_YANG_SOURCE.expected_presentation_rows == (
        XCUBE_RUBA_YANG_EQ140_ROWS
    )
    assert XCUBE_RUBA_YANG_SOURCE.arxiv_id == "2509.10418"
    assert XCUBE_RUBA_YANG_SOURCE.example == "Example 54"
    assert {"Eq. (138)", "Eq. (140)", "Eq. (144)"} <= set(
        XCUBE_RUBA_YANG_SOURCE.equations
    )
    assert certificate.equation_lock_verified
    assert certificate.verified


def test_axial_halfspace_records_explicit_non_surjectivity_witness():
    result = xcube_orientation_benchmark(PrimitiveNormal((0, 0, 1)))
    value = result.value

    assert result.exactness is Exactness.EXPERIMENTAL
    assert value.behavior is BoundaryToBulkBehavior.NOT_SURJECTIVE
    assert value.half_space.normal.components == (0, 0, 1)
    assert value.obstruction_witness.representative_family == "[<x^m y^n z>]"
    assert value.obstruction_witness.parameters == ("m in Z", "n in Z")
    assert "not surjective" in value.conclusion
    assert not value.constructs_full_boundary_module
    assert ("analytic_conclusion_recomputed", False) in result.verification


def test_slanted_111_halfspace_records_only_the_eq144_isomorphism():
    normal = PrimitiveNormal.from_rational(
        (Fraction(1, 3), Fraction(1, 3), Fraction(1, 3))
    )
    result = xcube_orientation_benchmark(normal)
    value = result.value

    assert normal.components == (1, 1, 1)
    assert value.behavior is BoundaryToBulkBehavior.ISOMORPHISM
    assert value.obstruction_witness is None
    assert "a+b+c >= 0" in value.conclusion
    assert value.certificate.expected_source_equation == "Eq. (144)"
    assert value.certificate.orientation_lock_verified
    assert not value.constructs_full_boundary_module


def test_registered_cases_use_certified_adapted_one_sided_support():
    for components in ((0, 0, 1), (1, 1, 1)):
        result = xcube_orientation_benchmark(PrimitiveNormal(components))
        certificate = result.certificate
        descriptor = certificate.one_sided_support

        assert certificate.basis_change.certificate.verified
        assert certificate.one_sided_support_verified
        assert descriptor.depth_interval[0] == 0
        assert all(
            descriptor.semigroup.contains_displacement(displacement)
            for displacement in descriptor.ambient_displacements
        )
        assert certificate.registered_normal.dot(
            certificate.support_translation
        ) == max(0, -certificate.original_depth_interval[0])


def test_unregistered_and_opposite_directions_are_not_extrapolated():
    for components in ((1, 1, 0), (0, 0, -1), (1, 0, 0)):
        result = xcube_orientation_benchmark(PrimitiveNormal(components))

        assert result.exactness is Exactness.UNSUPPORTED
        assert result.value is None
        assert result.certificate is None
        assert ("requested_normal", components) in result.verification
        assert any("no conclusion is extrapolated" in item for item in result.warnings)


def test_orientation_certificate_rejects_direction_claim_tampering():
    axial = xcube_orientation_benchmark(PrimitiveNormal((0, 0, 1))).certificate
    wrong_behavior = replace(
        axial,
        expected_behavior=BoundaryToBulkBehavior.ISOMORPHISM,
    )
    wrong_equation = replace(axial, expected_source_equation="Eq. (144)")

    assert not wrong_behavior.orientation_lock_verified
    assert not wrong_behavior.verified
    assert not wrong_equation.orientation_lock_verified
    assert not wrong_equation.verified


def test_result_serialization_keeps_scope_and_non_computation_warning():
    result = xcube_orientation_benchmark(PrimitiveNormal((1, 1, 1)))
    payload = canonical_json(result)

    assert '"exactness":"experimental"' in payload
    assert '["analytic_conclusion_recomputed",false]' in payload
    assert '"full_boundary_module_constructed":false' in payload
    assert "does not independently re-prove" in payload
