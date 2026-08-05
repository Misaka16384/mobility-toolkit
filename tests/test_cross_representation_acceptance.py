"""Acceptance checks across the geometry, topology, and finite-Pauli layers.

These tests deliberately compare semantic objects through explicit maps.  Raw
coordinate origins and physical-site strings are presentation data, while a
relative homology group and a logical Pauli group are related but not the same
object.
"""

import pytest

pytest.importorskip("flint")

from mobility_toolkit.core import (
    LocalPauliTerm,
    LocalSystem,
    OperatorTemplate,
    OperatorTerm,
    PeriodicCode,
    SparseIntMatrix,
    TranslationGroup,
    canonical_json,
)
from mobility_toolkit.finite import FlintIntegerBackend, analyze_finite_stabilizer
from mobility_toolkit.geometry import (
    CrossingPolicy,
    FiniteCellComplex,
    FiniteRegion,
    LatticeCoordinate,
    LocalPauliAutomorphism,
    RelativeCellularPair,
    SiteAddress,
    SiteEmbedding,
    SupportAliasPolicy,
    cellular_stabilizer_code,
    compile_periodic_code,
    construct_relative_chain_complex,
    relative_cellular_homology,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _labelled_open_line_region(origin, physical_site_ids, species):
    """Build canonical region IR with an intentionally noncanonical ID spelling."""

    coordinates = tuple(
        LatticeCoordinate((origin + offset,)) for offset in range(len(physical_site_ids))
    )
    physical_systems = tuple(
        LocalSystem.cyclic(site_id, species[0].invariant_factors[0])
        for site_id in physical_site_ids
    )
    embeddings = tuple(
        SiteEmbedding(
            SiteAddress(coordinate, species[0].site_id),
            site_id,
            LocalPauliAutomorphism.identity(species[0].invariant_factors),
        )
        for coordinate, site_id in zip(coordinates, physical_site_ids)
    )
    return FiniteRegion(
        translation_group=TranslationGroup(1),
        source_species=species,
        anchor_coordinates=coordinates,
        physical_systems=physical_systems,
        embeddings=embeddings,
        assumptions=("explicit open line used for representation-invariance testing",),
    )


def _transport_generators(generators, target_module, site_bijection):
    """Push Pauli operators through an explicit site-labelled module isomorphism."""

    transported = []
    for operator in generators:
        transported.append(
            target_module.operator(
                tuple(
                    LocalPauliTerm(
                        site_bijection[term.site_id],
                        term.x_exponents,
                        term.z_exponents,
                    )
                    for term in operator.terms
                ),
                phase=operator.phase,
            )
        )
    return tuple(sorted(transported, key=canonical_json))


def test_compiler_is_invariant_under_origin_translation_and_explicit_site_relabel(
    backend,
):
    """Equivalent canonical IRs define the same finite Pauli subquotients.

    The second region is translated by +11 and uses site IDs whose lexical
    order is unrelated to their coordinate order.  We compare the compiled
    groups only after applying the declared site bijection.
    """

    species = (LocalSystem.cyclic("q", 4),)
    code = PeriodicCode(
        TranslationGroup(1),
        species,
        (
            OperatorTemplate(
                0,
                (
                    OperatorTerm.cyclic((0,), "q", z=1),
                    OperatorTerm.cyclic((1,), "q", z=-1),
                ),
            ),
        ),
        ("open Z_4 repetition-style stabilizer template",),
    )
    base_ids = ("left", "middle", "right")
    shifted_ids = ("omega", "alpha", "kappa")
    base_region = _labelled_open_line_region(0, base_ids, species)
    shifted_region = _labelled_open_line_region(11, shifted_ids, species)

    def compile_(region):
        return compile_periodic_code(
            code,
            region,
            crossing_policy=CrossingPolicy.OMIT_WHOLE_INSTANCE,
            support_alias_policy=SupportAliasPolicy.REJECT_SUPPORT_ALIAS,
            backend=backend,
        )

    base = compile_(base_region)
    shifted = compile_(shifted_region)
    explicit_relabel = dict(zip(shifted_ids, base_ids))
    shifted_on_base_module = _transport_generators(
        shifted.generators,
        base.pauli_module,
        explicit_relabel,
    )

    # The canonical semantic generator relation agrees after transport; raw
    # physical site IDs and raw source coordinates are intentionally unequal.
    assert tuple(sorted(base.generators, key=canonical_json)) == shifted_on_base_module
    assert base.region.anchor_coordinates != shifted.region.anchor_coordinates
    assert base.pauli_module != shifted.pauli_module

    base_analysis = analyze_finite_stabilizer(
        base.pauli_module, base.generators, backend
    )
    transported_analysis = analyze_finite_stabilizer(
        base.pauli_module, shifted_on_base_module, backend
    )
    assert base_analysis.stabilizer == transported_analysis.stabilizer
    assert base_analysis.centralizer == transported_analysis.centralizer
    assert (
        base_analysis.logical_invariant_factors
        == transported_analysis.logical_invariant_factors
        == (4, 4)
    )
    assert base_analysis.codespace_dimension == transported_analysis.codespace_dimension == 4


def _relative_interval_with_both_endpoints():
    interval = FiniteCellComplex(
        (("v0", "v1"), ("e01",)),
        (
            SparseIntMatrix.zero(0, 2),
            SparseIntMatrix.from_rows(((-1,), (1,))),
        ),
        ("oriented unit interval",),
    )
    return RelativeCellularPair.create(interval, (("v0", "v1"), ()))


@pytest.mark.parametrize("modulus", (2, 4))
def test_relative_homology_matches_independent_css_logical_quotient(
    backend, modulus
):
    """Cross-check the homology-to-CSS dictionary for one exact relative pair.

    Dictionary for this test:

    * one physical Z_N qudit is placed on each relative 1-cell;
    * X checks come from relative 2-boundaries and Z checks from the relative
      1-boundary map;
    * ``H_1(X,A; Z_N)`` labels logical basis sectors, so its order equals the
      codespace dimension;
    * ``C(S)/S`` is the *doubled symplectic logical Pauli group*, not H_1
      itself.  For this one-free-relative-edge pair it is
      ``Z_N (logical X) + Z_N (logical Z)``.

    The relative homology and finite symplectic quotient are computed by
    independent backend paths from the same certified quotient chain complex.
    """

    pair = _relative_interval_with_both_endpoints()
    relative = relative_cellular_homology(pair, 1, modulus, backend)
    quotient_complex = construct_relative_chain_complex(pair).chain_complex
    css = cellular_stabilizer_code(quotient_complex, 1, modulus)
    finite = analyze_finite_stabilizer(
        css.code.pauli_module,
        css.code.generators,
        backend,
    )

    assert relative.invariant_factors == (modulus,)
    assert relative.order == modulus
    assert finite.codespace_dimension == relative.order
    assert finite.logical_invariant_factors == (modulus, modulus)
    assert finite.logical_projective_order == relative.order**2

