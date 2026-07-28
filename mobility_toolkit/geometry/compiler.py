"""Certified compilation of periodic operator templates onto finite regions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence, Tuple

from mobility_toolkit.core.canonical import canonical_hash, canonical_json
from mobility_toolkit.core.codes import (
    OperatorTemplate,
    OperatorTerm,
    PeriodicCode,
    StabilizerCodeSpec,
    SubsystemCodeSpec,
)
from mobility_toolkit.core.pauli import LocalPauliTerm, PauliModule, PauliOperator
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.finite.stabilizer import StabilizerValidation, validate_stabilizer_generators
from mobility_toolkit.geometry.frame import LocalPauliImage
from mobility_toolkit.geometry.frame import LocalPauliAutomorphism
from mobility_toolkit.geometry.model import (
    FiniteRegion,
    LatticeCoordinate,
    ResolvedSite,
    SiteAddress,
)


class CrossingPolicy(str, Enum):
    ERROR_ON_CROSSING = "error_on_crossing"
    OMIT_WHOLE_INSTANCE = "omit_whole_instance"
    TRUNCATE_MISSING_TERMS = "truncate_missing_terms"
    REQUIRE_LOCAL_REWRITE = "require_local_rewrite"


class SupportAliasPolicy(str, Enum):
    REJECT_SUPPORT_ALIAS = "reject_support_alias"
    NORMAL_FORM_PUSHFORWARD = "normal_form_pushforward"


class GeometryCompilationError(ValueError):
    pass


class CrossingTermError(GeometryCompilationError):
    pass


class LocalRewriteRequired(GeometryCompilationError):
    pass


class SupportAliasError(GeometryCompilationError):
    pass


@dataclass(frozen=True)
class CompiledTarget:
    term: OperatorTerm
    raw_address: SiteAddress
    resolved: Optional[ResolvedSite]
    mapped_image: Optional[LocalPauliImage]
    frame_rewrite_ids: Tuple[str, ...] = ()

    def to_canonical_dict(self) -> dict:
        return {
            "mapped_image": self.mapped_image,
            "raw_address": self.raw_address,
            "resolved": self.resolved,
            "frame_rewrite_ids": self.frame_rewrite_ids,
            "term": self.term,
        }


@dataclass(frozen=True)
class GeneratorInstanceProvenance:
    template_index: int
    template_hash: str
    anchor: LatticeCoordinate
    targets: Tuple[CompiledTarget, ...]
    missing_addresses: Tuple[SiteAddress, ...]
    support_alias_site_ids: Tuple[str, ...]
    crossing_policy: CrossingPolicy
    support_alias_policy: SupportAliasPolicy
    disposition: str
    final_operator_hash: str = ""

    SCHEMA_ID = "mobility_toolkit.generator_instance_provenance.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "anchor": self.anchor,
            "crossing_policy": self.crossing_policy,
            "disposition": self.disposition,
            "final_operator_hash": self.final_operator_hash,
            "missing_addresses": self.missing_addresses,
            "schema": self.SCHEMA_ID,
            "support_alias_policy": self.support_alias_policy,
            "support_alias_site_ids": self.support_alias_site_ids,
            "targets": self.targets,
            "template_hash": self.template_hash,
            "template_index": self.template_index,
        }


@dataclass(frozen=True)
class CompiledGenerator:
    operator: PauliOperator
    sources: Tuple[object, ...]

    SCHEMA_ID = "mobility_toolkit.compiled_generator.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "operator": self.operator,
            "schema": self.SCHEMA_ID,
            "sources": self.sources,
        }


@dataclass(frozen=True)
class CompilationCertificate:
    expected_instance_count: int
    compiled_instance_count: int
    omitted_instances: Tuple[GeneratorInstanceProvenance, ...]
    crossing_policy: CrossingPolicy
    support_alias_policy: SupportAliasPolicy

    SCHEMA_ID = "mobility_toolkit.compilation_certificate.v1"

    def __post_init__(self) -> None:
        if self.expected_instance_count != (
            self.compiled_instance_count + len(self.omitted_instances)
        ):
            raise ValueError("compilation certificate does not account for every instance")

    def to_canonical_dict(self) -> dict:
        return {
            "compiled_instance_count": self.compiled_instance_count,
            "crossing_policy": self.crossing_policy,
            "expected_instance_count": self.expected_instance_count,
            "omitted_instances": self.omitted_instances,
            "schema": self.SCHEMA_ID,
            "support_alias_policy": self.support_alias_policy,
        }


@dataclass(frozen=True)
class InstanceSelector:
    template_hash: str
    anchor: LatticeCoordinate

    SCHEMA_ID = "mobility_toolkit.instance_selector.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "anchor": self.anchor,
            "schema": self.SCHEMA_ID,
            "template_hash": self.template_hash,
        }


@dataclass(frozen=True)
class TermFrameRewrite:
    rewrite_id: str
    template_hash: str
    anchor: LatticeCoordinate
    raw_address: SiteAddress
    frame: LocalPauliAutomorphism

    SCHEMA_ID = "mobility_toolkit.term_frame_rewrite.v1"

    def __post_init__(self) -> None:
        if not self.rewrite_id:
            raise ValueError("frame rewrite ID must be nonempty")
        if not isinstance(self.frame, LocalPauliAutomorphism):
            raise TypeError("term frame rewrite needs a LocalPauliAutomorphism")

    def to_canonical_dict(self) -> dict:
        return {
            "anchor": self.anchor,
            "frame": self.frame,
            "raw_address": self.raw_address,
            "rewrite_id": self.rewrite_id,
            "schema": self.SCHEMA_ID,
            "template_hash": self.template_hash,
        }


@dataclass(frozen=True)
class ExplicitOperatorSpec:
    operator_id: str
    phase: int
    terms: Tuple[LocalPauliTerm, ...]

    SCHEMA_ID = "mobility_toolkit.explicit_operator_spec.v1"

    def __post_init__(self) -> None:
        if not self.operator_id:
            raise ValueError("explicit operator ID must be nonempty")
        object.__setattr__(self, "terms", tuple(self.terms))

    def to_canonical_dict(self) -> dict:
        return {
            "operator_id": self.operator_id,
            "phase": self.phase,
            "schema": self.SCHEMA_ID,
            "terms": self.terms,
        }


@dataclass(frozen=True)
class LocalModification:
    modification_id: str
    additional_systems: Tuple[object, ...] = ()
    remove_instances: Tuple[InstanceSelector, ...] = ()
    frame_rewrites: Tuple[TermFrameRewrite, ...] = ()
    add_operators: Tuple[ExplicitOperatorSpec, ...] = ()
    assumptions: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.local_modification.v1"

    def __post_init__(self) -> None:
        from mobility_toolkit.core.pauli import LocalSystem

        if not self.modification_id:
            raise ValueError("local modification ID must be nonempty")
        if any(not isinstance(system, LocalSystem) for system in self.additional_systems):
            raise TypeError("additional systems must be LocalSystem objects")
        object.__setattr__(
            self, "additional_systems", tuple(sorted(self.additional_systems, key=lambda item: item.site_id))
        )
        object.__setattr__(
            self,
            "remove_instances",
            tuple(sorted(set(self.remove_instances), key=lambda item: (item.anchor, item.template_hash))),
        )
        object.__setattr__(
            self,
            "frame_rewrites",
            tuple(
                sorted(
                    self.frame_rewrites,
                    key=lambda item: (item.anchor, item.template_hash, item.raw_address),
                )
            ),
        )
        object.__setattr__(
            self, "add_operators", tuple(sorted(self.add_operators, key=lambda item: item.operator_id))
        )
        object.__setattr__(self, "assumptions", tuple(sorted(set(self.assumptions))))

    def to_canonical_dict(self) -> dict:
        return {
            "add_operators": self.add_operators,
            "additional_systems": self.additional_systems,
            "assumptions": self.assumptions,
            "frame_rewrites": self.frame_rewrites,
            "modification_id": self.modification_id,
            "remove_instances": self.remove_instances,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class LocalGeneratorProvenance:
    modification_id: str
    operator_id: str
    final_operator_hash: str

    SCHEMA_ID = "mobility_toolkit.local_generator_provenance.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "final_operator_hash": self.final_operator_hash,
            "modification_id": self.modification_id,
            "operator_id": self.operator_id,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class FiniteCode:
    region: FiniteRegion
    pauli_module: PauliModule
    compiled_generators: Tuple[CompiledGenerator, ...]
    validation: StabilizerValidation
    compilation_certificate: CompilationCertificate
    modifications: Tuple[LocalModification, ...] = ()
    assumptions: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.finite_code.v1"

    @property
    def generators(self) -> Tuple[PauliOperator, ...]:
        return tuple(record.operator for record in self.compiled_generators)

    @property
    def is_stabilizer_code(self) -> bool:
        return self.validation.valid

    def as_stabilizer_spec(self) -> StabilizerCodeSpec:
        if not self.validation.valid:
            raise ValueError("compiled finite code fails stabilizer validation")
        return StabilizerCodeSpec(self.pauli_module, self.generators, self.assumptions)

    def as_subsystem_spec(self) -> SubsystemCodeSpec:
        return SubsystemCodeSpec(self.pauli_module, self.generators, self.assumptions)

    def to_canonical_dict(self) -> dict:
        return {
            "assumptions": self.assumptions,
            "compilation_certificate": self.compilation_certificate,
            "compiled_generators": self.compiled_generators,
            "modifications": self.modifications,
            "pauli_module": self.pauli_module,
            "region": self.region,
            "schema": self.SCHEMA_ID,
            "validation": self.validation,
        }


def _raw_address(anchor: LatticeCoordinate, term: OperatorTerm) -> SiteAddress:
    coordinate = anchor.translated(term.free_offset, term.torsion_offset)
    return SiteAddress(coordinate, term.species_id)


def _alias_site_ids(targets: Sequence[CompiledTarget]) -> Tuple[str, ...]:
    counts = {}
    for target in targets:
        if target.resolved is not None:
            site_id = target.resolved.physical_site_id
            counts[site_id] = counts.get(site_id, 0) + 1
    return tuple(sorted(site_id for site_id, count in counts.items() if count > 1))


def _instantiate(
    template: OperatorTemplate,
    template_index: int,
    anchor: LatticeCoordinate,
    region: FiniteRegion,
    module: PauliModule,
    crossing_policy: CrossingPolicy,
    support_alias_policy: SupportAliasPolicy,
    frame_rewrites: Sequence[TermFrameRewrite] = (),
    force_remove: bool = False,
) -> Tuple[Optional[PauliOperator], GeneratorInstanceProvenance]:
    template_hash = canonical_hash(OperatorTemplate.SCHEMA_ID, template)
    rewrites_by_address = {
        rewrite.raw_address: rewrite
        for rewrite in frame_rewrites
        if rewrite.template_hash == template_hash and rewrite.anchor == anchor
    }
    targets = []
    for term in template.terms:
        raw = _raw_address(anchor, term)
        resolved = region.resolve(raw)
        mapped = None
        rewrite_ids = ()
        if resolved is not None:
            map_ = resolved.frame
            rewrite = rewrites_by_address.get(raw)
            if rewrite is not None:
                if rewrite.frame.invariant_factors != map_.invariant_factors:
                    raise GeometryCompilationError("frame rewrite has incompatible local factors")
                map_ = rewrite.frame.forward.then(map_)
                rewrite_ids = (rewrite.rewrite_id,)
            mapped = map_.apply(term.x_exponents, term.z_exponents)
        targets.append(CompiledTarget(term, raw, resolved, mapped, rewrite_ids))
    targets = tuple(targets)
    missing = tuple(target.raw_address for target in targets if target.resolved is None)
    aliases = _alias_site_ids(targets)
    if aliases and support_alias_policy == SupportAliasPolicy.REJECT_SUPPORT_ALIAS:
        raise SupportAliasError(
            f"template {template_index} at {anchor} aliases support on sites {aliases}"
        )
    if missing:
        if force_remove:
            provenance = GeneratorInstanceProvenance(
                template_index,
                template_hash,
                anchor,
                targets,
                missing,
                aliases,
                crossing_policy,
                support_alias_policy,
                "removed_by_local_modification",
            )
            return None, provenance
        if crossing_policy == CrossingPolicy.ERROR_ON_CROSSING:
            raise CrossingTermError(
                f"template {template_index} at {anchor} crosses the finite region"
            )
        if crossing_policy == CrossingPolicy.REQUIRE_LOCAL_REWRITE:
            raise LocalRewriteRequired(
                f"template {template_index} at {anchor} requires an explicit local rewrite"
            )
        if crossing_policy == CrossingPolicy.OMIT_WHOLE_INSTANCE:
            provenance = GeneratorInstanceProvenance(
                template_index,
                template_hash,
                anchor,
                targets,
                missing,
                aliases,
                crossing_policy,
                support_alias_policy,
                "omitted_crossing_instance",
            )
            return None, provenance

    if force_remove:
        provenance = GeneratorInstanceProvenance(
            template_index,
            template_hash,
            anchor,
            targets,
            missing,
            aliases,
            crossing_policy,
            support_alias_policy,
            "removed_by_local_modification",
        )
        return None, provenance

    operator = module.identity(template.phase)
    for target in targets:
        if target.resolved is None:
            continue
        image = target.mapped_image
        local_operator = module.operator(
            (
                LocalPauliTerm(
                    target.resolved.physical_site_id,
                    image.x_exponents,
                    image.z_exponents,
                ),
            ),
            phase=image.phase,
        )
        operator = operator * local_operator
    disposition = "compiled_full_support" if not missing else "compiled_truncated"
    operator_hash = canonical_hash(PauliOperator.SCHEMA_ID, operator)
    provenance = GeneratorInstanceProvenance(
        template_index,
        template_hash,
        anchor,
        targets,
        missing,
        aliases,
        crossing_policy,
        support_alias_policy,
        disposition,
        operator_hash,
    )
    return operator, provenance


def compile_periodic_code(
    periodic_code: PeriodicCode,
    region: FiniteRegion,
    *,
    crossing_policy: CrossingPolicy,
    support_alias_policy: SupportAliasPolicy,
    backend: FiniteIntegerBackend,
    modifications: Sequence[LocalModification] = (),
) -> FiniteCode:
    if periodic_code.translation_group != region.translation_group:
        raise ValueError("periodic code and finite region use different translation groups")
    if periodic_code.species != region.source_species:
        raise ValueError("periodic code and finite region declare different source species")
    if not isinstance(crossing_policy, CrossingPolicy):
        raise TypeError("crossing_policy must be an explicit CrossingPolicy")
    if not isinstance(support_alias_policy, SupportAliasPolicy):
        raise TypeError("support_alias_policy must be an explicit SupportAliasPolicy")
    modifications = tuple(sorted(tuple(modifications), key=lambda item: item.modification_id))
    if len({item.modification_id for item in modifications}) != len(modifications):
        raise ValueError("local modification IDs must be unique")
    additional_systems = tuple(
        system for modification in modifications for system in modification.additional_systems
    )
    all_systems = tuple(region.physical_systems) + additional_systems
    if len({system.site_id for system in all_systems}) != len(all_systems):
        raise ValueError("local modifications introduce a duplicate physical site ID")
    module = PauliModule(all_systems)
    remove_selectors = tuple(
        selector for modification in modifications for selector in modification.remove_instances
    )
    if len(set(remove_selectors)) != len(remove_selectors):
        raise ValueError("multiple local modifications remove the same generator instance")
    remove_set = set(remove_selectors)
    frame_rewrites = tuple(
        rewrite for modification in modifications for rewrite in modification.frame_rewrites
    )
    rewrite_keys = tuple(
        (rewrite.template_hash, rewrite.anchor, rewrite.raw_address) for rewrite in frame_rewrites
    )
    if len(set(rewrite_keys)) != len(rewrite_keys):
        raise ValueError("overlapping term frame rewrites are ambiguous")
    operator_ids = tuple(
        operator.operator_id
        for modification in modifications
        for operator in modification.add_operators
    )
    if len(set(operator_ids)) != len(operator_ids):
        raise ValueError("explicit local operator IDs must be unique")
    compiled_by_hash = {}
    omitted = []
    compiled_instances = 0
    for anchor in region.anchor_coordinates:
        for template_index, template in enumerate(periodic_code.stabilizer_templates):
            operator, provenance = _instantiate(
                template,
                template_index,
                anchor,
                region,
                module,
                crossing_policy,
                support_alias_policy,
                frame_rewrites,
                InstanceSelector(
                    canonical_hash(OperatorTemplate.SCHEMA_ID, template), anchor
                )
                in remove_set,
            )
            if operator is None:
                omitted.append(provenance)
                continue
            compiled_instances += 1
            key = canonical_json(operator)
            if key not in compiled_by_hash:
                compiled_by_hash[key] = [operator, []]
            compiled_by_hash[key][1].append(provenance)
    for modification in modifications:
        for operator_spec in modification.add_operators:
            operator = module.operator(operator_spec.terms, phase=operator_spec.phase)
            key = canonical_json(operator)
            if key not in compiled_by_hash:
                compiled_by_hash[key] = [operator, []]
            compiled_by_hash[key][1].append(
                LocalGeneratorProvenance(
                    modification.modification_id,
                    operator_spec.operator_id,
                    canonical_hash(PauliOperator.SCHEMA_ID, operator),
                )
            )
    records = tuple(
        CompiledGenerator(
            compiled_by_hash[key][0],
            tuple(
                sorted(
                    compiled_by_hash[key][1],
                    key=canonical_json,
                )
            ),
        )
        for key in sorted(compiled_by_hash)
    )
    generators = tuple(record.operator for record in records)
    validation = validate_stabilizer_generators(module, generators, backend)
    expected = len(region.anchor_coordinates) * len(periodic_code.stabilizer_templates)
    certificate = CompilationCertificate(
        expected,
        compiled_instances,
        tuple(omitted),
        crossing_policy,
        support_alias_policy,
    )
    return FiniteCode(
        region,
        module,
        records,
        validation,
        certificate,
        modifications,
        tuple(sorted(set(periodic_code.assumptions + region.assumptions))),
    )


__all__ = [
    "CompilationCertificate",
    "CompiledGenerator",
    "CompiledTarget",
    "CrossingPolicy",
    "CrossingTermError",
    "FiniteCode",
    "GeneratorInstanceProvenance",
    "GeometryCompilationError",
    "LocalRewriteRequired",
    "LocalGeneratorProvenance",
    "LocalModification",
    "ExplicitOperatorSpec",
    "InstanceSelector",
    "SupportAliasError",
    "SupportAliasPolicy",
    "TermFrameRewrite",
    "compile_periodic_code",
]
