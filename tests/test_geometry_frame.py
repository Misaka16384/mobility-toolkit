import itertools

import pytest

from mobility_toolkit.geometry import (
    LocalPauliAutomorphism,
    LocalPauliImage,
    LocalPauliMap,
)


def test_identity_and_charge_conjugation_frames():
    identity = LocalPauliAutomorphism.identity((4,))
    conjugation = LocalPauliAutomorphism.cyclic_multipliers((4,), (-1,))
    assert identity.power(17).is_identity
    assert conjugation.power(2).is_identity
    image = conjugation.forward.apply((1,), (2,), phase=3)
    assert image == LocalPauliImage(3, (3,), (2,))
    assert conjugation.power(-1) == conjugation.inverse


@pytest.mark.parametrize("factors", ((2,), (3,), (4,), (2, 4)))
def test_fourier_frame_has_exact_phase_aware_inverse(factors):
    fourier = LocalPauliAutomorphism.fourier(factors)
    assert fourier.forward.then(fourier.inverse).is_identity
    assert fourier.inverse.then(fourier.forward).is_identity
    ranges = [range(factor) for factor in factors]
    for x_values in itertools.product(*ranges):
        for z_values in itertools.product(*ranges):
            image = fourier.forward.apply(x_values, z_values, phase=1)
            recovered = fourier.inverse.apply(
                image.x_exponents, image.z_exponents, image.phase
            )
            assert recovered == LocalPauliImage(1, x_values, z_values)


def test_invalid_nonunit_or_non_symplectic_frames_are_rejected():
    with pytest.raises(ValueError, match="must be a unit"):
        LocalPauliAutomorphism.cyclic_multipliers((4,), (2,))

    bad = (
        LocalPauliImage(0, (1,), (0,)),
        LocalPauliImage(0, (1,), (0,)),
    )
    with pytest.raises(ValueError, match="commutator pairing"):
        LocalPauliMap((3,), bad)


def test_even_dimension_fourier_tracks_normal_order_phase():
    fourier = LocalPauliAutomorphism.fourier((4,))
    image = fourier.forward.apply((1,), (1,))
    assert image.x_exponents == (3,)
    assert image.z_exponents == (1,)
    assert image.phase == 6
