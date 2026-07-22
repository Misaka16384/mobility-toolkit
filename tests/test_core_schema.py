from dataclasses import dataclass

import pytest

from mobility_toolkit.core import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
    ModuleMap,
    PresentedModule,
    SparseIntMatrix,
    Submodule,
    canonical_hash,
    canonical_json,
)


def test_sparse_matrix_normalizes_duplicate_entries_and_order():
    matrix = SparseIntMatrix(
        2,
        3,
        (
            (1, 2, 5),
            (0, 1, 4),
            (1, 2, -2),
            (0, 1, -4),
            (1, 0, 7),
        ),
    )
    assert matrix.entries == ((1, 0, 7), (1, 2, 3))
    assert matrix.to_rows() == ((0, 0, 0), (7, 0, 3))


def test_sparse_matrix_rejects_nonintegral_and_out_of_bounds_entries():
    with pytest.raises(TypeError):
        SparseIntMatrix(1, 1, ((0, 0, True),))
    with pytest.raises(ValueError):
        SparseIntMatrix(1, 1, ((1, 0, 1),))


def test_sparse_matrix_multiplication_and_transpose():
    left = SparseIntMatrix.from_rows(((1, 2), (0, 3)))
    right = SparseIntMatrix.from_rows(((4,), (5,)))
    assert left.matmul(right).to_rows() == ((14,), (15,))
    assert left.transpose().to_rows() == ((1, 0), (2, 3))


def test_presented_module_invariant_factor_validation():
    module = PresentedModule.from_invariant_factors((2, 4, 12), ("a", "b", "c"))
    assert module.relations.to_rows() == ((2, 0, 0), (0, 4, 0), (0, 0, 12))
    with pytest.raises(ValueError):
        PresentedModule.from_invariant_factors((4, 6))


def test_module_map_relation_witness_is_checked():
    source = PresentedModule.from_invariant_factors((4,), ("x",))
    target = PresentedModule.from_invariant_factors((8,), ("y",))
    valid = ModuleMap(
        source,
        target,
        SparseIntMatrix.from_rows(((2,),)),
        SparseIntMatrix.from_rows(((1,),)),
    )
    assert valid.relations_verified is True
    with pytest.raises(ValueError, match="relation witness"):
        ModuleMap(
            source,
            target,
            SparseIntMatrix.from_rows(((2,),)),
            SparseIntMatrix.from_rows(((2,),)),
        )


def test_submodule_shape_and_labels_are_validated():
    ambient = PresentedModule.from_invariant_factors((2, 4))
    subgroup = Submodule(
        ambient,
        SparseIntMatrix.from_rows(((1,), (2,))),
        ("g",),
    )
    assert subgroup.generators.ncols == 1
    with pytest.raises(ValueError):
        Submodule(ambient, SparseIntMatrix.from_rows(((1,),)))


def test_canonical_json_and_hash_ignore_mapping_and_coo_input_order():
    first = SparseIntMatrix(2, 2, ((1, 0, 3), (0, 1, 2)))
    second = SparseIntMatrix(2, 2, ((0, 1, 2), (1, 0, 3)))
    assert canonical_json({"b": 1, "a": first}) == canonical_json({"a": second, "b": 1})
    assert canonical_hash("test.v1", first) == canonical_hash("test.v1", second)


def test_canonical_serialization_rejects_floats_and_implicit_dataclasses():
    with pytest.raises(TypeError, match="floating-point"):
        canonical_json({"coordinate": 0.5})

    @dataclass
    class AccidentalIdentity:
        value: int

    with pytest.raises(TypeError, match="must define to_canonical_dict"):
        canonical_json(AccidentalIdentity(1))


def test_computation_result_has_stable_metadata_and_input_hash():
    provenance = BackendProvenance(
        backend="internal",
        algorithm="identity",
        version="1",
        parameters=(("mode", "exact"),),
    )
    result = ComputationResult(
        operation="schema-smoke",
        input_data={"b": 2, "a": 1},
        value={"ok": True},
        exactness=Exactness.CERTIFIED_EXACT,
        assumptions=("finite", "finite"),
        certificate_level=CertificateLevel.STANDARD,
        verification=(("checked", True),),
        backend_provenance=provenance,
    )
    reordered = ComputationResult(
        operation="schema-smoke",
        input_data={"a": 1, "b": 2},
        value={"ok": True},
        exactness=Exactness.CERTIFIED_EXACT,
    )
    assert result.canonical_input_hash == reordered.canonical_input_hash
    assert result.assumptions == ("finite",)
    encoded = canonical_json(result)
    assert '"exactness":"certified_exact"' in encoded
    assert result.canonical_input_hash in encoded
