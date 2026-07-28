import pytest

pytest.importorskip("flint")

from mobility_toolkit.core import (
    LocalSystem,
    OperatorTemplate,
    OperatorTerm,
    PeriodicCode,
    TranslationGroup,
)
from mobility_toolkit.finite import FlintIntegerBackend, analyze_finite_stabilizer
from mobility_toolkit.geometry import (
    CrossingPolicy,
    CrossingTermError,
    LocalRewriteRequired,
    SupportAliasError,
    SupportAliasPolicy,
    cellular_homology,
    compile_periodic_code,
    explicit_coordinate_region,
    rectangular_cubical_complex,
    rectangular_region,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _compile(code, region, backend, crossing, alias=SupportAliasPolicy.REJECT_SUPPORT_ALIAS):
    return compile_periodic_code(
        code,
        region,
        crossing_policy=crossing,
        support_alias_policy=alias,
        backend=backend,
    )


def test_crossing_policies_are_explicit_and_certified(backend):
    species = (LocalSystem.cyclic("q", 2),)
    code = PeriodicCode(
        TranslationGroup(1),
        species,
        (
            OperatorTemplate(
                0,
                (
                    OperatorTerm.cyclic((0,), "q", z=1),
                    OperatorTerm.cyclic((1,), "q", z=1),
                ),
            ),
        ),
    )
    region = rectangular_region((3,), species)
    with pytest.raises(CrossingTermError):
        _compile(code, region, backend, CrossingPolicy.ERROR_ON_CROSSING)
    with pytest.raises(LocalRewriteRequired):
        _compile(code, region, backend, CrossingPolicy.REQUIRE_LOCAL_REWRITE)

    omitted = _compile(code, region, backend, CrossingPolicy.OMIT_WHOLE_INSTANCE)
    assert len(omitted.compiled_generators) == 2
    assert omitted.compilation_certificate.expected_instance_count == 3
    assert omitted.compilation_certificate.compiled_instance_count == 2
    assert len(omitted.compilation_certificate.omitted_instances) == 1

    truncated = _compile(code, region, backend, CrossingPolicy.TRUNCATE_MISSING_TERMS)
    assert len(truncated.compiled_generators) == 3
    assert any(
        source.disposition == "compiled_truncated"
        for record in truncated.compiled_generators
        for source in record.sources
    )


def test_support_alias_rejection_and_phase_aware_pushforward(backend):
    species = (LocalSystem.cyclic("q", 4),)
    code = PeriodicCode(
        TranslationGroup(1),
        species,
        (
            OperatorTemplate(
                0,
                (
                    OperatorTerm.cyclic((0,), "q", z=1),
                    OperatorTerm.cyclic((1,), "q", x=1),
                ),
            ),
        ),
    )
    region = rectangular_region((1,), species, periodic_axes=(0,))
    with pytest.raises(SupportAliasError):
        _compile(code, region, backend, CrossingPolicy.ERROR_ON_CROSSING)
    pushed = _compile(
        code,
        region,
        backend,
        CrossingPolicy.ERROR_ON_CROSSING,
        SupportAliasPolicy.NORMAL_FORM_PUSHFORWARD,
    )
    operator = pushed.generators[0]
    assert operator.phase == 2
    assert operator.terms[0].x_exponents == (1,)
    assert operator.terms[0].z_exponents == (1,)
    assert pushed.compiled_generators[0].sources[0].support_alias_site_ids


def test_small_period_dedup_preserves_all_source_instances(backend):
    species = (LocalSystem.cyclic("q", 2),)
    code = PeriodicCode(
        TranslationGroup(1),
        species,
        (
            OperatorTemplate(
                0,
                (
                    OperatorTerm.cyclic((0,), "q", x=1),
                    OperatorTerm.cyclic((1,), "q", x=1),
                ),
            ),
        ),
    )
    region = rectangular_region((2,), species, periodic_axes=(0,))
    compiled = _compile(
        code,
        region,
        backend,
        CrossingPolicy.ERROR_ON_CROSSING,
        SupportAliasPolicy.NORMAL_FORM_PUSHFORWARD,
    )
    assert len(compiled.compiled_generators) == 1
    assert len(compiled.compiled_generators[0].sources) == 2
    assert compiled.compilation_certificate.compiled_instance_count == 2


def _periodic_toric_code(modulus):
    species = (LocalSystem.cyclic("h", modulus), LocalSystem.cyclic("v", modulus))
    star = OperatorTemplate(
        0,
        (
            OperatorTerm.cyclic((-1, 0), "h", x=1),
            OperatorTerm.cyclic((0, 0), "h", x=-1),
            OperatorTerm.cyclic((0, -1), "v", x=1),
            OperatorTerm.cyclic((0, 0), "v", x=-1),
        ),
    )
    plaquette = OperatorTemplate(
        0,
        (
            OperatorTerm.cyclic((0, 0), "h", z=1),
            OperatorTerm.cyclic((0, 1), "h", z=-1),
            OperatorTerm.cyclic((0, 0), "v", z=-1),
            OperatorTerm.cyclic((1, 0), "v", z=1),
        ),
    )
    return PeriodicCode(
        TranslationGroup(2),
        species,
        (star, plaquette),
        ("oriented Z_N toric code with qudits on edges",),
    )


@pytest.mark.parametrize("modulus", (2, 3, 4))
def test_periodic_toric_compiler_matches_cellular_homology(backend, modulus):
    code = _periodic_toric_code(modulus)
    region = rectangular_region((2, 2), code.species, periodic_axes=(0, 1))
    compiled = _compile(code, region, backend, CrossingPolicy.ERROR_ON_CROSSING)
    assert compiled.is_stabilizer_code
    result = analyze_finite_stabilizer(compiled.pauli_module, compiled.generators, backend)
    cellular = rectangular_cubical_complex((2, 2), periodic_axes=(0, 1))
    homology = cellular_homology(cellular.chain_complex, 1, modulus, backend)
    assert homology.order == modulus**2
    assert result.codespace_dimension == homology.order
    assert result.logical_projective_order == modulus**4


def test_torsion_translation_offsets_are_compiled(backend):
    group = TranslationGroup(0, (3,))
    species = (LocalSystem.cyclic("q", 2),)
    code = PeriodicCode(
        group,
        species,
        (
            OperatorTemplate(
                0,
                (
                    OperatorTerm.cyclic((), "q", z=1, torsion_offset=(1,)),
                ),
            ),
        ),
    )
    region = explicit_coordinate_region(group, ((),), species)
    compiled = _compile(code, region, backend, CrossingPolicy.ERROR_ON_CROSSING)
    assert len(compiled.generators) == 3
    assert compiled.compilation_certificate.compiled_instance_count == 3


def test_compiler_requires_policy_enums(backend):
    code = _periodic_toric_code(2)
    region = rectangular_region((2, 2), code.species, periodic_axes=(0, 1))
    with pytest.raises(TypeError, match="explicit CrossingPolicy"):
        compile_periodic_code(
            code,
            region,
            crossing_policy="error_on_crossing",
            support_alias_policy=SupportAliasPolicy.REJECT_SUPPORT_ALIAS,
            backend=backend,
        )
