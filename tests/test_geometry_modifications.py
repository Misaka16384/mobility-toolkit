import pytest

pytest.importorskip("flint")

from mobility_toolkit.core import (
    LocalPauliTerm,
    LocalSystem,
    OperatorTemplate,
    OperatorTerm,
    PeriodicCode,
    TranslationGroup,
    canonical_hash,
)
from mobility_toolkit.finite import FlintIntegerBackend, analyze_finite_stabilizer
from mobility_toolkit.geometry import (
    CrossingPolicy,
    ExplicitOperatorSpec,
    InstanceSelector,
    LatticeCoordinate,
    LocalModification,
    LocalPauliAutomorphism,
    SiteAddress,
    SupportAliasPolicy,
    TermFrameRewrite,
    canonical_physical_site_id,
    compile_periodic_code,
    rectangular_region,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _compile(code, region, backend, modifications=(), crossing=CrossingPolicy.ERROR_ON_CROSSING):
    return compile_periodic_code(
        code,
        region,
        crossing_policy=crossing,
        support_alias_policy=SupportAliasPolicy.REJECT_SUPPORT_ALIAS,
        backend=backend,
        modifications=modifications,
    )


def test_branch_cut_frame_rewrite_changes_terms_without_gluing_sites(backend):
    species = (LocalSystem.cyclic("q", 4),)
    template = OperatorTemplate(0, (OperatorTerm.cyclic((0,), "q", x=1),))
    code = PeriodicCode(TranslationGroup(1), species, (template,))
    region = rectangular_region((2,), species)
    template_hash = canonical_hash(OperatorTemplate.SCHEMA_ID, template)
    raw = SiteAddress(LatticeCoordinate((1,)), "q")
    modification = LocalModification(
        "fourier-branch-cut",
        frame_rewrites=(
            TermFrameRewrite(
                "cross-cut",
                template_hash,
                LatticeCoordinate((1,)),
                raw,
                LocalPauliAutomorphism.fourier((4,)),
            ),
        ),
    )
    compiled = _compile(code, region, backend, (modification,))
    assert len(compiled.pauli_module.local_systems) == 2
    by_site = {
        record.operator.terms[0].site_id: record.operator.terms[0]
        for record in compiled.compiled_generators
    }
    site0 = canonical_physical_site_id(SiteAddress(LatticeCoordinate((0,)), "q"))
    site1 = canonical_physical_site_id(raw)
    assert by_site[site0].x_exponents == (1,)
    assert by_site[site1].z_exponents == (1,)
    assert any(
        target.frame_rewrite_ids == ("cross-cut",)
        for record in compiled.compiled_generators
        for source in record.sources
        if hasattr(source, "targets")
        for target in source.targets
    )


def test_crossing_instance_can_be_explicitly_replaced(backend):
    species = (LocalSystem.cyclic("q", 2),)
    template = OperatorTemplate(
        0,
        (
            OperatorTerm.cyclic((0,), "q", z=1),
            OperatorTerm.cyclic((1,), "q", z=1),
        ),
    )
    code = PeriodicCode(TranslationGroup(1), species, (template,))
    region = rectangular_region((2,), species)
    boundary_site = canonical_physical_site_id(
        SiteAddress(LatticeCoordinate((1,)), "q")
    )
    modification = LocalModification(
        "right-boundary-rewrite",
        remove_instances=(
            InstanceSelector(
                canonical_hash(OperatorTemplate.SCHEMA_ID, template),
                LatticeCoordinate((1,)),
            ),
        ),
        add_operators=(
            ExplicitOperatorSpec(
                "right-boundary-z",
                0,
                (LocalPauliTerm.cyclic(boundary_site, z=1),),
            ),
        ),
    )
    compiled = _compile(
        code,
        region,
        backend,
        (modification,),
        CrossingPolicy.REQUIRE_LOCAL_REWRITE,
    )
    assert compiled.is_stabilizer_code
    assert any(
        source.disposition == "removed_by_local_modification"
        for source in compiled.compilation_certificate.omitted_instances
    )
    assert any(
        getattr(source, "operator_id", "") == "right-boundary-z"
        for record in compiled.compiled_generators
        for source in record.sources
    )


def test_auxiliary_qudit_is_added_before_explicit_operator_validation(backend):
    species = (LocalSystem.cyclic("q", 2),)
    code = PeriodicCode(TranslationGroup(1), species, ())
    region = rectangular_region((1,), species)
    modification = LocalModification(
        "add-boundary-ancilla",
        additional_systems=(LocalSystem.cyclic("ancilla", 2),),
        add_operators=(
            ExplicitOperatorSpec(
                "pin-ancilla-z", 0, (LocalPauliTerm.cyclic("ancilla", z=1),)
            ),
        ),
    )
    compiled = _compile(code, region, backend, (modification,))
    assert len(compiled.pauli_module.local_systems) == 2
    result = analyze_finite_stabilizer(compiled.pauli_module, compiled.generators, backend)
    assert result.codespace_dimension == 2


def test_overlapping_modification_actions_are_rejected(backend):
    species = (LocalSystem.cyclic("q", 2),)
    template = OperatorTemplate(0, (OperatorTerm.cyclic((0,), "q", z=1),))
    code = PeriodicCode(TranslationGroup(1), species, (template,))
    region = rectangular_region((1,), species)
    selector = InstanceSelector(
        canonical_hash(OperatorTemplate.SCHEMA_ID, template), LatticeCoordinate((0,))
    )
    first = LocalModification("first", remove_instances=(selector,))
    second = LocalModification("second", remove_instances=(selector,))
    with pytest.raises(ValueError, match="same generator instance"):
        _compile(code, region, backend, (first, second))
