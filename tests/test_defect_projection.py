import pytest

from mobility_toolkit.core import LocalPauliTerm, PauliModule
from mobility_toolkit.defects import project_pinned_z_subsystems
from mobility_toolkit.finite import FlintIntegerBackend


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def test_explicit_z_pinned_qubit_deletes_with_exact_logical_certificate(backend):
    module = PauliModule.from_dimensions((2, 2), ("kept", "pinned"))
    pin = module.operator((LocalPauliTerm.cyclic("pinned", z=1),))
    correlated_z = module.operator(
        (
            LocalPauliTerm.cyclic("kept", z=1),
            LocalPauliTerm.cyclic("pinned", z=1),
        )
    )
    result = project_pinned_z_subsystems(
        module,
        (("pin", pin), ("correlated", correlated_z)),
        ("pinned",),
        ("pin",),
        backend,
    )
    assert result.certificate.verified
    assert result.direct_analysis.codespace_dimension == 1
    assert result.projected_analysis.codespace_dimension == 1
    assert tuple(system.site_id for system in result.projected_code.pauli_module.local_systems) == (
        "kept",
    )


def test_projection_rejects_x_support_on_deleted_site(backend):
    module = PauliModule.from_dimensions((2,), ("q",))
    z = module.operator((LocalPauliTerm.cyclic("q", z=1),))
    x = module.operator((LocalPauliTerm.cyclic("q", x=1),))
    with pytest.raises(ValueError, match="X support"):
        project_pinned_z_subsystems(
            module,
            (("pin", z), ("bad", x)),
            ("q",),
            ("pin",),
            backend,
        )


def test_projection_rescales_physical_phase_when_phase_modulus_shrinks(backend):
    module = PauliModule.from_dimensions((2, 3), ("delete-qubit", "keep-qutrit"))
    pin = module.operator((LocalPauliTerm.cyclic("delete-qubit", z=1),))
    qutrit_sector = module.operator(
        (LocalPauliTerm.cyclic("keep-qutrit", z=1),), phase=4
    )
    result = project_pinned_z_subsystems(
        module,
        (("pin", pin), ("qutrit-sector", qutrit_sector)),
        ("delete-qubit",),
        ("pin",),
        backend,
    )
    projected = next(
        term.operator
        for term in result.projected_terms
        if term.term_id == "qutrit-sector"
    )
    assert module.phase_modulus == 12
    assert projected.module.phase_modulus == 6
    assert projected.phase == 2
