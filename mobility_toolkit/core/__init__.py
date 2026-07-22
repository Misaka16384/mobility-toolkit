"""Canonical algebraic contracts shared by finite and periodic backends."""

from mobility_toolkit.core.canonical import canonical_hash, canonical_json, canonicalize
from mobility_toolkit.core.integer import (
    MatrixEntry,
    ModuleMap,
    PresentedModule,
    SparseIntMatrix,
    Submodule,
)
from mobility_toolkit.core.pauli import LocalPauliTerm, LocalSystem, PauliModule, PauliOperator
from mobility_toolkit.core.results import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
)

__all__ = [
    "BackendProvenance",
    "CertificateLevel",
    "ComputationResult",
    "Exactness",
    "LocalPauliTerm",
    "LocalSystem",
    "MatrixEntry",
    "ModuleMap",
    "PresentedModule",
    "PauliModule",
    "PauliOperator",
    "SparseIntMatrix",
    "Submodule",
    "canonical_hash",
    "canonical_json",
    "canonicalize",
]
