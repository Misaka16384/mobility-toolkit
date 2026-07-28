from mobility_toolkit.core import LocalPauliTerm, PauliModule
from mobility_toolkit.defects import HamiltonianTerm, pauli_syndrome


def test_qutrit_syndrome_preserves_signed_phase_exponent():
    module = PauliModule.from_dimensions((3,), ("q",))
    check = module.operator((LocalPauliTerm.cyclic("q", z=1),))
    probe = module.operator((LocalPauliTerm.cyclic("q", x=1),))
    terms = (
        HamiltonianTerm("first", "test", ("q",), check),
        HamiltonianTerm("duplicate-name-independent", "test", ("q",), check),
    )
    report = pauli_syndrome(probe, terms)
    assert tuple(entry.phase_exponent for entry in report.entries) == (2, 2)
    assert report.violated_term_ids == ("first", "duplicate-name-independent")


def test_composite_ququart_syndrome_uses_full_phase_modulus():
    module = PauliModule.from_dimensions((4,), ("q",))
    check = module.operator((LocalPauliTerm.cyclic("q", z=1),))
    probe = module.operator((LocalPauliTerm.cyclic("q", x=2),))
    report = pauli_syndrome(
        probe, (HamiltonianTerm("z", "test", ("q",), check),)
    )
    assert report.entries[0].phase_modulus == 8
    assert report.entries[0].phase_exponent == 4
    assert report.entries[0].violated
