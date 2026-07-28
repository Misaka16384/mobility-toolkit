from dataclasses import replace

import pytest

pytest.importorskip("flint")

from mobility_toolkit.core import SparseIntMatrix
from mobility_toolkit.finite import FlintIntegerBackend
from mobility_toolkit.geometry import (
    FiniteCellComplex,
    RelativeCellularPair,
    cellular_homology,
    construct_relative_chain_complex,
    relative_cellular_homology,
    verify_relative_homology_result,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _interval():
    return FiniteCellComplex(
        (("v0", "v1"), ("e01",)),
        (
            SparseIntMatrix.zero(0, 2),
            SparseIntMatrix.from_rows(((-1,), (1,))),
        ),
        ("oriented unit interval",),
    )


def _triangular_disk():
    # e01=v1-v0, e12=v2-v1, e20=v0-v2 and df=e01+e12+e20.
    return FiniteCellComplex(
        (("v0", "v1", "v2"), ("e01", "e12", "e20"), ("f012",)),
        (
            SparseIntMatrix.zero(0, 3),
            SparseIntMatrix.from_rows(
                (
                    (-1, 0, 1),
                    (1, -1, 0),
                    (0, 1, -1),
                )
            ),
            SparseIntMatrix.from_rows(((1,), (1,), (1,))),
        ),
        ("oriented triangular disk",),
    )


@pytest.mark.parametrize("modulus", (2, 3, 4, 6))
def test_interval_relative_endpoints_has_h1_z_n(backend, modulus):
    pair = RelativeCellularPair.create(_interval(), (("v1", "v0"), ()))
    result = relative_cellular_homology(pair, 1, modulus, backend)
    assert result.invariant_factors == (modulus,)
    assert result.order == modulus
    assert result.relative_chain_complex.chain_complex.cell_counts == (0, 1)


@pytest.mark.parametrize("modulus", (2, 3, 4, 6))
def test_disk_relative_full_boundary_has_h2_z_n(backend, modulus):
    pair = RelativeCellularPair.create(
        _triangular_disk(),
        (("v2", "v0", "v1"), ("e20", "e01", "e12"), ()),
    )
    result = relative_cellular_homology(pair, 2, modulus, backend)
    assert result.invariant_factors == (modulus,)
    assert result.order == modulus
    assert result.relative_chain_complex.chain_complex.cell_counts == (0, 0, 1)


@pytest.mark.parametrize("degree", (0, 1, 2))
def test_empty_subcomplex_agrees_with_absolute_homology(backend, degree):
    ambient = _triangular_disk()
    pair = RelativeCellularPair.create(ambient, ((), (), ()))
    relative = relative_cellular_homology(pair, degree, 4, backend)
    absolute = cellular_homology(ambient, degree, 4, backend)
    assert relative.invariant_factors == absolute.invariant_factors
    assert relative.order == absolute.order
    assert (
        relative.relative_chain_complex.chain_complex.cell_ids_by_dimension
        == ambient.cell_ids_by_dimension
    )
    assert (
        relative.relative_chain_complex.chain_complex.boundary_maps
        == ambient.boundary_maps
    )


def test_malformed_non_subcomplex_is_rejected():
    with pytest.raises(ValueError, match="not boundary closed"):
        RelativeCellularPair.create(
            _triangular_disk(),
            (("v0",), ("e01",), ()),
        )


def test_unknown_subcomplex_cell_is_rejected():
    with pytest.raises(ValueError, match="unknown cells"):
        RelativeCellularPair.create(_interval(), (("not-a-vertex",), ()))


def test_canonical_identity_and_quotient_do_not_depend_on_input_order():
    ambient = _triangular_disk()
    left = RelativeCellularPair.create(
        ambient,
        (("v0", "v1", "v2"), ("e01", "e12", "e20"), ()),
    )
    right = RelativeCellularPair.create(
        ambient,
        (("v2", "v1", "v0"), ("e20", "e12", "e01"), ()),
    )
    assert left == right
    assert left.canonical_identity == right.canonical_identity
    assert (
        construct_relative_chain_complex(left).certificate
        == construct_relative_chain_complex(right).certificate
    )


def test_relative_homology_certificate_and_semantic_replay_reject_tampering(backend):
    pair = RelativeCellularPair.create(_interval(), (("v0", "v1"), ()))
    result = relative_cellular_homology(pair, 1, 4, backend)
    verify_relative_homology_result(result, backend)

    with pytest.raises(ValueError, match="certificate disagrees"):
        replace(
            result,
            certificate=replace(result.certificate, order=8),
        )

    different = RelativeCellularPair.create(_interval(), ((), ()))
    resealed = replace(
        result,
        relative_chain_complex=construct_relative_chain_complex(different),
        certificate=replace(
            result.certificate,
            pair_identity=different.canonical_identity,
            relative_complex_identity=construct_relative_chain_complex(
                different
            ).certificate.relative_complex_identity,
        ),
    )
    with pytest.raises(ValueError, match="semantic replay"):
        verify_relative_homology_result(resealed, backend)
