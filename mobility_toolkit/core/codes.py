"""Canonical stabilizer, subsystem, and periodic code specifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Sequence, Tuple

from mobility_toolkit.core.canonical import canonical_json
from mobility_toolkit.core.laurent import TranslationGroup
from mobility_toolkit.core.pauli import LocalPauliTerm, LocalSystem, PauliModule, PauliOperator


def _integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _canonical_operators(
    module: PauliModule, generators: Iterable[PauliOperator]
) -> Tuple[PauliOperator, ...]:
    unique = {}
    for generator in tuple(generators):
        if not isinstance(generator, PauliOperator) or generator.module != module:
            raise ValueError("all generators must belong to the declared Pauli module")
        unique[canonical_json(generator)] = generator
    return tuple(unique[key] for key in sorted(unique))


@dataclass(frozen=True)
class StabilizerCodeSpec:
    """A phase-aware stabilizer generator specification.

    ``basic_validation_errors`` checks local lift obstructions, obvious scalar
    conflicts, and pairwise commutation. Full relation-lattice phase
    consistency is certified by the Phase 2 finite solver.
    """

    pauli_module: PauliModule
    generators: Tuple[PauliOperator, ...]
    assumptions: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.stabilizer_code_spec.v1"

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "generators", _canonical_operators(self.pauli_module, self.generators)
        )
        object.__setattr__(self, "assumptions", tuple(sorted(set(self.assumptions))))

    @property
    def pairwise_commuting(self) -> bool:
        return all(
            left.commutes_with(right)
            for index, left in enumerate(self.generators)
            for right in self.generators[index + 1 :]
        )

    @property
    def individual_lifts_valid(self) -> bool:
        return all(generator.scalar_obstruction == 0 for generator in self.generators)

    @property
    def has_obvious_scalar_conflict(self) -> bool:
        phases_by_projective_key: Dict[tuple, int] = {}
        for generator in self.generators:
            if generator.is_projective_identity and not generator.is_identity:
                return True
            key = generator.projective_key()
            previous = phases_by_projective_key.get(key)
            if previous is not None and previous != generator.phase:
                return True
            phases_by_projective_key[key] = generator.phase
        return False

    def basic_validation_errors(self) -> Tuple[str, ...]:
        errors = []
        if not self.pairwise_commuting:
            errors.append("generators are not pairwise projectively commuting")
        if not self.individual_lifts_valid:
            errors.append("one or more generators has a scalar order obstruction")
        if self.has_obvious_scalar_conflict:
            errors.append("generators contain an obvious nontrivial scalar relation")
        return tuple(errors)

    def to_canonical_dict(self) -> dict:
        return {
            "assumptions": self.assumptions,
            "generators": self.generators,
            "pauli_module": self.pauli_module,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class SubsystemCodeSpec:
    """A possibly noncommuting gauge-generator specification."""

    pauli_module: PauliModule
    gauge_generators: Tuple[PauliOperator, ...]
    assumptions: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.subsystem_code_spec.v1"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gauge_generators",
            _canonical_operators(self.pauli_module, self.gauge_generators),
        )
        object.__setattr__(self, "assumptions", tuple(sorted(set(self.assumptions))))

    def to_canonical_dict(self) -> dict:
        return {
            "assumptions": self.assumptions,
            "gauge_generators": self.gauge_generators,
            "pauli_module": self.pauli_module,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True, order=True)
class OperatorTerm:
    free_offset: Tuple[int, ...]
    species_id: str
    x_exponents: Tuple[int, ...]
    z_exponents: Tuple[int, ...]
    torsion_offset: Tuple[int, ...] = ()

    SCHEMA_ID = "mobility_toolkit.operator_term.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.species_id, str) or not self.species_id:
            raise ValueError("species_id must be a nonempty string")
        object.__setattr__(
            self,
            "free_offset",
            tuple(_integer(value, "free offset") for value in self.free_offset),
        )
        object.__setattr__(
            self,
            "torsion_offset",
            tuple(_integer(value, "torsion offset") for value in self.torsion_offset),
        )
        object.__setattr__(
            self,
            "x_exponents",
            tuple(_integer(value, "X exponent") for value in self.x_exponents),
        )
        object.__setattr__(
            self,
            "z_exponents",
            tuple(_integer(value, "Z exponent") for value in self.z_exponents),
        )

    @classmethod
    def cyclic(
        cls,
        offset: Sequence[int],
        species_id: str,
        x: int = 0,
        z: int = 0,
        torsion_offset: Sequence[int] = (),
    ) -> "OperatorTerm":
        return cls(tuple(offset), species_id, (x,), (z,), tuple(torsion_offset))

    def to_canonical_dict(self) -> dict:
        return {
            "free_offset": self.free_offset,
            "schema": self.SCHEMA_ID,
            "species_id": self.species_id,
            "torsion_offset": self.torsion_offset,
            "x_exponents": self.x_exponents,
            "z_exponents": self.z_exponents,
        }


@dataclass(frozen=True)
class OperatorTemplate:
    phase: int
    terms: Tuple[OperatorTerm, ...]

    SCHEMA_ID = "mobility_toolkit.operator_template.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "phase", _integer(self.phase, "phase"))
        terms = tuple(self.terms)
        if any(not isinstance(term, OperatorTerm) for term in terms):
            raise TypeError("template terms must be OperatorTerm objects")
        object.__setattr__(self, "terms", tuple(sorted(terms)))

    def to_canonical_dict(self) -> dict:
        return {"phase": self.phase, "schema": self.SCHEMA_ID, "terms": self.terms}


def _normalize_template(
    template: OperatorTemplate,
    group: TranslationGroup,
    species: Dict[str, LocalSystem],
    phase_modulus: int,
) -> OperatorTemplate:
    accumulated = {}
    for term in template.terms:
        if len(term.free_offset) != group.free_rank:
            raise ValueError("operator free-offset rank does not match the translation group")
        if len(term.torsion_offset) != len(group.torsion_invariants):
            raise ValueError("operator torsion-offset rank does not match the translation group")
        if term.species_id not in species:
            raise ValueError(f"unknown operator species: {term.species_id}")
        local = species[term.species_id]
        if len(term.x_exponents) != len(local.invariant_factors):
            raise ValueError("operator X exponent count does not match species")
        if len(term.z_exponents) != len(local.invariant_factors):
            raise ValueError("operator Z exponent count does not match species")
        torsion_offset = tuple(
            value % order
            for value, order in zip(term.torsion_offset, group.torsion_invariants)
        )
        key = (term.free_offset, torsion_offset, term.species_id)
        if key not in accumulated:
            accumulated[key] = (
                [0] * len(local.invariant_factors),
                [0] * len(local.invariant_factors),
            )
        x_values, z_values = accumulated[key]
        for index, factor in enumerate(local.invariant_factors):
            x_values[index] = (x_values[index] + term.x_exponents[index]) % factor
            z_values[index] = (z_values[index] + term.z_exponents[index]) % factor
    normalized = []
    for (free_offset, torsion_offset, species_id), (x_values, z_values) in sorted(
        accumulated.items()
    ):
        if any(x_values) or any(z_values):
            normalized.append(
                OperatorTerm(
                    free_offset,
                    species_id,
                    tuple(x_values),
                    tuple(z_values),
                    torsion_offset,
                )
            )
    return OperatorTemplate(template.phase % phase_modulus, tuple(normalized))


@dataclass(frozen=True)
class PeriodicCode:
    translation_group: TranslationGroup
    species: Tuple[LocalSystem, ...]
    stabilizer_templates: Tuple[OperatorTemplate, ...]
    assumptions: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.periodic_code.v1"

    def __post_init__(self) -> None:
        species = tuple(sorted(tuple(self.species), key=lambda item: item.site_id))
        if len({item.site_id for item in species}) != len(species):
            raise ValueError("periodic species IDs must be unique")
        unit_cell = PauliModule(species)
        species_map = {item.site_id: item for item in species}
        templates = tuple(
            _normalize_template(
                template,
                self.translation_group,
                species_map,
                unit_cell.phase_modulus,
            )
            for template in self.stabilizer_templates
        )
        templates_by_json = {canonical_json(template): template for template in templates}
        object.__setattr__(self, "species", species)
        object.__setattr__(
            self,
            "stabilizer_templates",
            tuple(templates_by_json[key] for key in sorted(templates_by_json)),
        )
        object.__setattr__(self, "assumptions", tuple(sorted(set(self.assumptions))))

    @property
    def unit_cell_pauli_module(self) -> PauliModule:
        return PauliModule(self.species)

    def to_canonical_dict(self) -> dict:
        return {
            "assumptions": self.assumptions,
            "schema": self.SCHEMA_ID,
            "species": self.species,
            "stabilizer_templates": self.stabilizer_templates,
            "translation_group": self.translation_group,
        }


__all__ = [
    "OperatorTemplate",
    "OperatorTerm",
    "PeriodicCode",
    "StabilizerCodeSpec",
    "SubsystemCodeSpec",
]
