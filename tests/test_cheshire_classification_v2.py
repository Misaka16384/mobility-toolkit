from dataclasses import replace

import pytest

pytest.importorskip("flint")

from mobility_toolkit.anyons2d import (
    CondensateEnumerationBudget,
    FiniteMetricGroup,
    color_code_metric_model,
    double_semion_metric_model,
    three_fermion_metric_model,
    zd_toric_metric_model,
)
from mobility_toolkit.defects import (
    AlgebraMultiplicationEntry,
    EvidenceStatus,
    PointedAssociatorEntry,
    PointedCategoryCochainData,
    PointedFusionRule,
    TORIC_ORIENTATION_REVERSE,
    TORIC_SPECIES_ORDER,
    classify_abelian_interfaces,
    fuse_toric_2d_species,
    pointed_algebra_coboundary_equivalent,
    toric_2d_defect_classification,
    toric_2d_fusion_table,
    verify_pointed_algebra_cochain,
)
from mobility_toolkit.finite import FiniteAbelianGroup, FlintIntegerBackend


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def test_toric_six_species_come_from_exhaustive_folded_enumerator(backend):
    classification = toric_2d_defect_classification(backend)

    assert classification.certificate.classification_complete
    assert classification.certificate.toric_literature_crosswalk_verified
    assert classification.certificate.enumeration.certified_complete
    assert classification.certificate.enumeration.lagrangian_subgroups == 6
    assert tuple(item.species_id for item in classification.species) == (
        TORIC_SPECIES_ORDER
    )
    assert {
        item.species_id: item.orientation_reverse_id
        for item in classification.species
    } == TORIC_ORIENTATION_REVERSE
    assert {
        item.species_id for item in classification.species if item.invertible
    } == {"1", "S_psi"}
    assert {
        item.species_id
        for item in classification.species
        if item.species_kind == "cheshire_condensate"
    } == {"S_e", "S_m"}
    assert all(
        item.algebra is not None
        and item.algebra.certificate.associativity_verified
        and item.algebra.certificate.obstruction_free
        for item in classification.species
    )


def test_toric_direct_algebra_crosswalk_and_anyon_action_match_eq_638(backend):
    species = {
        item.species_id: item
        for item in toric_2d_defect_classification(backend).species
    }
    assert {
        item.algebra.algebra_id: tuple(
            label for label, _ in item.algebra.simple_object_multiplicities
        )
        for item in species.values()
    } == {
        "A_1": ("1",),
        "A_1_plus_e": ("1", "e"),
        "A_1_plus_m": ("1", "m"),
        "A_1_plus_psi": ("1", "psi"),
        "A_full_mu0": ("1", "e", "m", "psi"),
        "A_full_mu1": ("1", "e", "m", "psi"),
    }
    assert {
        action.input_sector: action.output_sectors
        for action in species["S_em"].bulk_sector_action
    } == {
        "1": (("1", 1), ("e", 1)),
        "e": (),
        "m": (("1", 1), ("e", 1)),
        "psi": (),
    }
    assert {
        action.input_sector: action.output_sectors
        for action in species["S_psi"].bulk_sector_action
    }["e"] == (("m", 1),)


def test_complete_ordered_fusion_table_matches_source_minimal_rules():
    table = {
        (item.left_species_id, item.right_species_id): item
        for item in toric_2d_fusion_table()
    }
    assert len(table) == 36
    assert table[("S_psi", "S_psi")].terms[0].output_species_id == "1"
    assert table[("S_em", "S_me")].terms[0].output_species_id == "S_e"
    assert table[("S_me", "S_em")].terms[0].output_species_id == "S_m"
    assert table[("S_e", "S_e")].terms[0].coefficient.coefficient_id == (
        "1d_z2_gauge_theory"
    )
    assert not table[
        ("S_e", "S_e")
    ].terms[0].coefficient.numeric_scalar
    assert all(item.ordered and item.verified for item in table.values())


@pytest.mark.parametrize(
    "model_factory,expected",
    (
        (lambda backend: zd_toric_metric_model(2, backend), 6),
        (lambda backend: zd_toric_metric_model(4, backend), 22),
        (double_semion_metric_model, 2),
        (three_fermion_metric_model, 6),
    ),
)
def test_generic_pointed_interface_literature_counts(
    model_factory, expected, backend
):
    model = model_factory(backend)
    classification = classify_abelian_interfaces(
        model.metric, model.metric, backend
    )
    assert classification.certificate.classification_complete
    assert len(classification.species) == expected


def test_two_toric_interface_has_270_exact_folded_lagrangians(backend):
    model = color_code_metric_model(backend)
    classification = classify_abelian_interfaces(
        model.metric, model.metric, backend
    )
    assert classification.certificate.classification_complete
    assert len(classification.species) == 270
    assert classification.certificate.enumeration.lagrangian_subgroups == 270


def test_interrupted_classification_resumes_to_one_shot_transcript(backend):
    metric = zd_toric_metric_model(2, backend).metric
    one_shot = classify_abelian_interfaces(metric, metric, backend)
    budget = CondensateEnumerationBudget(
        max_work_units=100,
        max_results=2,
        max_elements=100,
        max_subgroups=1_000,
    )
    checkpoint = None
    resumed = None
    for _ in range(100):
        resumed = classify_abelian_interfaces(
            metric,
            metric,
            backend,
            budget=budget,
            checkpoint=checkpoint,
            max_pages=1,
        )
        checkpoint = resumed.next_checkpoint
        if checkpoint is None:
            break
    else:
        raise AssertionError("bounded interface classification did not terminate")

    assert resumed is not None
    assert resumed.certificate.classification_complete
    assert resumed.certificate.transcript_hash == (
        one_shot.certificate.transcript_hash
    )
    assert tuple(item.species_id for item in resumed.species) == tuple(
        item.species_id for item in one_shot.species
    )


def test_morita_species_ids_ignore_generator_display_labels(backend):
    metric = zd_toric_metric_model(2, backend).metric
    relabeled_group = FiniteAbelianGroup(
        metric.group.relation_lattice_basis,
        metric.group.invariant_factors,
        ("electric_generator", "magnetic_generator"),
    )
    relabeled_metric = FiniteMetricGroup.create(
        relabeled_group,
        metric.phase_modulus,
        metric.braiding_matrix,
        metric.generator_spins,
        backend,
    )
    original = classify_abelian_interfaces(metric, metric, backend)
    relabeled = classify_abelian_interfaces(
        relabeled_metric, relabeled_metric, backend
    )

    assert {
        item.species_id for item in original.species
    } == {item.species_id for item in relabeled.species}
    assert {
        (item.species_id, item.orientation_reverse_id)
        for item in original.species
    } == {
        (item.species_id, item.orientation_reverse_id)
        for item in relabeled.species
    }


def _z2_pointed_category():
    objects = ("1", "g")
    fusion = tuple(
        PointedFusionRule(left, right, "g" if (left != right) else "1")
        for left in objects
        for right in objects
    )
    associator = tuple(
        PointedAssociatorEntry(first, second, third, 0)
        for first in objects
        for second in objects
        for third in objects
    )
    return PointedCategoryCochainData(
        objects,
        "1",
        4,
        fusion,
        associator,
        "exact Z2 pointed test presentation",
    )


def _z2_algebra_cochain(gg_phase):
    return (
        AlgebraMultiplicationEntry("1", "1", "1", 0, 4),
        AlgebraMultiplicationEntry("1", "g", "g", 0, 4),
        AlgebraMultiplicationEntry("g", "1", "g", 0, 4),
        AlgebraMultiplicationEntry("g", "g", "1", gg_phase, 4),
    )


def test_pointed_cochain_checker_and_explicit_coboundary_gauge():
    category = _z2_pointed_category()
    mu0 = _z2_algebra_cochain(0)
    mu_coboundary = _z2_algebra_cochain(2)

    assert verify_pointed_algebra_cochain(
        category, ("1", "g"), mu0
    ).verified
    assert verify_pointed_algebra_cochain(
        category, ("1", "g"), mu_coboundary
    ).verified
    assert pointed_algebra_coboundary_equivalent(
        category,
        ("1", "g"),
        mu0,
        mu_coboundary,
        (("1", 0), ("g", 1)),
    )

    obstructed_category = replace(
        category,
        associator=tuple(
            replace(item, phase_exponent=1)
            if (
                item.first_object,
                item.second_object,
                item.third_object,
            )
            == ("g", "g", "g")
            else item
            for item in category.associator
        ),
    )
    certificate = verify_pointed_algebra_cochain(
        obstructed_category, ("1", "g"), mu0
    )
    assert certificate.evidence_status is EvidenceStatus.UNSUPPORTED
    assert not certificate.associator_cocycle_verified
    assert not certificate.verified


def test_unknown_generic_fusion_does_not_fabricate_a_result():
    with pytest.raises(ValueError, match="unknown toric"):
        fuse_toric_2d_species("not-a-species", "1")
