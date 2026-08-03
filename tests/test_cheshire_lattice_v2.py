from dataclasses import replace

import pytest

pytest.importorskip("flint")

from mobility_toolkit.defects import (
    CliffordGate,
    TORIC_SPECIES_ORDER,
    construct_toric_2d_circuit,
    realize_toric_2d_defect,
    verify_toric_2d_circuit,
)
from mobility_toolkit.finite import FlintIntegerBackend


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


@pytest.mark.parametrize("species_id", TORIC_SPECIES_ORDER)
def test_all_six_toric_lattice_realizations_are_exact_and_drawn(
    species_id, backend
):
    realization = realize_toric_2d_defect(species_id, 2, backend)

    assert realization.certificate.verified
    assert realization.evidence_status.value == "bounded_exact"
    assert realization.bulk_hamiltonian_terms
    assert realization.removed_bulk_terms
    assert realization.defect_terms
    assert realization.truncated_bulk_terms == ()
    assert realization.endpoint_term_ids
    assert realization.short_folded_string_lifts
    assert realization.tikz.startswith("\\begin{tikzpicture}")
    assert realization.tikz.rstrip().endswith("\\end{tikzpicture}")
    assert all(
        site_id
        in {site.site_id for site in realization.site_geometry}
        for term in realization.defect_terms
        for site_id in term.support_site_ids
    )


@pytest.mark.parametrize("species_id", TORIC_SPECIES_ORDER)
def test_all_six_creation_templates_replay_exactly(species_id):
    result = construct_toric_2d_circuit("creation", species_id, 3)

    assert result.certificate.exact_pauli_conjugation_verified
    assert verify_toric_2d_circuit(result)
    if species_id in {"S_e", "S_m"}:
        assert result.circuit.provenance_kind == "source_locked"
        assert all(
            gate.gate_kind == "pauli_r"
            for layer in result.circuit.layers
            for gate in layer.gates
        )
    elif species_id != "1":
        assert result.circuit.provenance_kind == (
            "derived_from_source_generators"
        )


@pytest.mark.parametrize("process", ("deformation", "motion"))
def test_motion_and_deformation_have_constant_depth_replay(process):
    result = construct_toric_2d_circuit(process, "S_e", 4)
    assert result.certificate.finite_depth_claim
    assert result.circuit.depth == 3
    assert verify_toric_2d_circuit(result)


def test_fusion_circuit_carries_tqft_coefficient_and_order():
    forward = construct_toric_2d_circuit(
        "fusion", "S_em", 3, right_species_id="S_me"
    )
    reverse = construct_toric_2d_circuit(
        "fusion", "S_me", 3, right_species_id="S_em"
    )

    assert forward.output_species_id == "S_e"
    assert reverse.output_species_id == "S_m"
    assert forward.coefficient.coefficient_id == "1d_z2_gauge_theory"
    assert not forward.coefficient.numeric_scalar
    assert forward.certificate.ancilla_decoupling_verified
    assert forward.certificate.coefficient_sector_codespace_dimension == 2
    assert forward.certificate.fusion_degeneracy_matches_coefficient_shadow
    assert len(forward.coefficient_term_ids) == 2
    assert all(
        set(term.support_site_ids) <= {"b0", "b1", "b2"}
        for term in forward.target_terms
        if term.term_id in forward.coefficient_term_ids
    )
    assert verify_toric_2d_circuit(forward)
    assert verify_toric_2d_circuit(reverse)


def test_trivial_fusion_coefficient_chain_is_uniquely_polarized():
    result = construct_toric_2d_circuit(
        "fusion", "S_psi", 4, right_species_id="S_psi"
    )

    assert result.output_species_id == "1"
    assert result.coefficient.coefficient_id == "1d_trivial"
    assert result.certificate.ancilla_decoupling_verified
    assert result.certificate.coefficient_sector_codespace_dimension == 1
    assert result.certificate.fusion_degeneracy_matches_coefficient_shadow
    assert len(result.coefficient_term_ids) == 4
    assert verify_toric_2d_circuit(result)


def test_tampered_gate_or_target_term_fails_replay():
    result = construct_toric_2d_circuit("creation", "S_e", 3)
    first_layer = result.circuit.layers[0]
    first_site = first_layer.gates[0].site_ids[0]
    tampered_layer = replace(
        first_layer, gates=(CliffordGate("h", (first_site,)),)
    )
    tampered_circuit = replace(
        result.circuit,
        layers=(tampered_layer,) + result.circuit.layers[1:],
    )
    assert not verify_toric_2d_circuit(
        replace(result, circuit=tampered_circuit)
    )

    assert not verify_toric_2d_circuit(
        replace(
            result,
            target_terms=result.target_terms[:-1] + (result.source_terms[-1],),
        )
    )
