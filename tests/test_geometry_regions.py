import pytest

from mobility_toolkit.core import LocalSystem, TranslationGroup, canonical_hash
from mobility_toolkit.geometry import (
    AxisIdentification,
    FiniteRegion,
    GeometryDisplayMetadata,
    LatticeCoordinate,
    LocalPauliAutomorphism,
    LocalPauliImage,
    LocalPauliMap,
    SiteAddress,
    SiteAlias,
    SiteEmbedding,
    SpeciesFrame,
    box_stratification,
    canonical_physical_site_id,
    rectangular_region,
    region_with_rectangular_holes,
)


def test_open_and_periodic_resolution_are_explicit():
    species = (LocalSystem.cyclic("q", 3),)
    open_region = rectangular_region((2, 3), species)
    outside = SiteAddress(LatticeCoordinate((2, 0)), "q")
    assert open_region.resolve(outside) is None

    cylinder = rectangular_region((2, 3), species, periodic_axes=(0,))
    raw = SiteAddress(LatticeCoordinate((4, 1)), "q")
    resolved = cylinder.resolve(raw)
    expected = SiteAddress(LatticeCoordinate((0, 1)), "q")
    assert resolved.canonical_address == expected
    assert resolved.physical_site_id == canonical_physical_site_id(expected)
    assert resolved.winding == (("free", 0, 2),)
    assert resolved.frame.is_identity


def test_fourier_twisted_periodic_resolution_tracks_central_phase():
    species = (LocalSystem.cyclic("q", 4),)
    twist = LocalPauliAutomorphism.fourier((4,))
    region = rectangular_region(
        (3,), species, periodic_axes=(0,), twists={(0, "q"): twist}
    )
    resolved = region.resolve(SiteAddress(LatticeCoordinate((3,)), "q"))
    image = resolved.frame.apply((1,), (1,))
    assert image == LocalPauliImage(6, (3,), (1,))
    inverse = region.resolve(SiteAddress(LatticeCoordinate((-1,)), "q"))
    recovered = inverse.frame.apply(image.x_exponents, image.z_exponents, image.phase)
    assert recovered == LocalPauliImage(0, (1,), (1,))


def test_path_dependent_axis_holonomy_is_rejected():
    factors = (4,)
    fourier = LocalPauliAutomorphism.fourier(factors)
    phase_forward = LocalPauliMap(
        factors,
        (
            LocalPauliImage(2, (1,), (0,)),
            LocalPauliImage(0, (0,), (1,)),
        ),
    )
    phase_inverse = LocalPauliMap(
        factors,
        (
            LocalPauliImage(-2, (1,), (0,)),
            LocalPauliImage(0, (0,), (1,)),
        ),
    )
    phase_twist = LocalPauliAutomorphism(phase_forward, phase_inverse)
    species = (LocalSystem.cyclic("q", 4),)
    with pytest.raises(ValueError, match="path dependent"):
        rectangular_region(
            (2, 2),
            species,
            periodic_axes=(0, 1),
            twists={(0, "q"): fourier, (1, "q"): phase_twist},
        )


def test_explicit_site_gluing_is_not_a_branch_cut():
    species = (LocalSystem.cyclic("q", 2),)
    target = SiteAddress(LatticeCoordinate((0,)), "q")
    source = SiteAddress(LatticeCoordinate((1,)), "q")
    site_id = canonical_physical_site_id(target)
    region = FiniteRegion(
        TranslationGroup(1),
        species,
        (target.coordinate, source.coordinate),
        (LocalSystem.cyclic(site_id, 2),),
        (
            SiteEmbedding(
                target, site_id, LocalPauliAutomorphism.identity((2,))
            ),
        ),
        (),
        (
            SiteAlias(
                source,
                target,
                LocalPauliAutomorphism.identity((2,)),
                "explicit-site-gluing",
            ),
        ),
    )
    resolved = region.resolve(source)
    assert resolved.physical_site_id == site_id
    assert resolved.seams == ("explicit-site-gluing",)
    assert len(region.physical_systems) == 1


def test_gluing_mismatched_local_dimensions_is_rejected():
    q2 = LocalSystem.cyclic("q2", 2)
    q4 = LocalSystem.cyclic("q4", 4)
    source = SiteAddress(LatticeCoordinate((0,)), "q2")
    target = SiteAddress(LatticeCoordinate((1,)), "q4")
    with pytest.raises(ValueError, match="changes local invariant factors"):
        FiniteRegion(
            TranslationGroup(1),
            (q2, q4),
            (source.coordinate, target.coordinate),
            (LocalSystem.cyclic("physical", 4),),
            (
                SiteEmbedding(
                    target,
                    "physical",
                    LocalPauliAutomorphism.identity((4,)),
                ),
            ),
            (),
            (
                SiteAlias(
                    source,
                    target,
                    LocalPauliAutomorphism.identity((2,)),
                ),
            ),
        )


def test_box_strata_distinguish_patches_hinges_and_corners():
    strata = box_stratification((3, 3, 3), (LocalSystem.cyclic("q", 2),))
    by_role = {}
    for stratum in strata.strata:
        by_role.setdefault(stratum.role, []).append(stratum)
    assert len(by_role["surface"]) == 6
    assert len(by_role["hinge"]) == 12
    assert len(by_role["corner"]) == 8
    assert len(by_role["bulk"]) == 1
    assert all(len(stratum.parent_ids) == 2 for stratum in by_role["hinge"])
    assert all(len(stratum.parent_ids) == 3 for stratum in by_role["corner"])


def test_holes_and_display_metadata_do_not_change_math_identity():
    species = (LocalSystem.cyclic("q", 2),)
    region = region_with_rectangular_holes(
        (5, 3), (((1, 1), (1, 1)), ((3, 1), (1, 1))), species
    )
    assert len(region.anchor_coordinates) == 13
    before = canonical_hash("region", region)
    display = GeometryDisplayMetadata(
        positions=((region.physical_systems[0].site_id, (0.125, 9.5)),),
        labels=((region.physical_systems[0].site_id, "pretty label"),),
    )
    assert display.positions
    assert canonical_hash("region", region) == before
