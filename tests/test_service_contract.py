import pytest

from mobility_toolkit.core import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
)
from mobility_toolkit.services import (
    BackendFingerprint,
    InMemoryServiceCache,
    ServiceCapability,
    ServiceRegistration,
    ServiceRegistry,
    ServiceRequest,
)


def _fingerprint(version="1"):
    return BackendFingerprint(
        "exact-test-backend",
        version,
        "integer-reference",
        (("composite", True), ("mixed", True)),
    )


def _handler(request):
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value={"answer": 4},
        exactness=Exactness.CERTIFIED_EXACT,
        assumptions=request.assumptions,
        certificate_level=CertificateLevel.FULL,
        certificate={"replay": "2+2"},
        backend_provenance=BackendProvenance(
            "exact-test-backend", "integer-reference", "1"
        ),
    )


def _capability(request):
    return ServiceCapability(
        request.operation,
        True,
        Exactness.CERTIFIED_EXACT,
        request.backend_fingerprint,
        "test operation is exact",
    )


def test_registry_dispatches_one_canonical_request_without_global_state():
    registry = ServiceRegistry(
        (ServiceRegistration("finite.test", _handler, _capability),)
    )
    request = ServiceRequest(
        "finite.test",
        {"left": 2, "right": 2},
        CertificateLevel.STANDARD,
        ("integer arithmetic",),
        _fingerprint(),
        "raw",
        {"finite_bound": 4},
    )
    result = registry.dispatch(request)
    assert result.value == {"answer": 4}
    assert result.canonical_input_hash == request.canonical_input_hash
    assert registry.operations == ("finite.test",)


def test_dispatch_rejects_result_contract_drift():
    request = ServiceRequest("bad", {"x": 1}, CertificateLevel.FULL)

    def wrong_operation(_):
        return ComputationResult(
            "other",
            {"x": 1},
            None,
            Exactness.EXPERIMENTAL,
            certificate_level=CertificateLevel.FULL,
        )

    with pytest.raises(ArithmeticError, match="operation differs"):
        ServiceRegistry((ServiceRegistration("bad", wrong_operation),)).dispatch(
            request
        )

    def weak_certificate(req):
        return ComputationResult(
            req.operation,
            req.input_data,
            None,
            Exactness.EXPERIMENTAL,
            certificate_level=CertificateLevel.NONE,
        )

    with pytest.raises(ArithmeticError, match="certificate level"):
        ServiceRegistry(
            (ServiceRegistration("bad", weak_certificate),)
        ).dispatch(request)


def test_unsupported_capability_blocks_handler_execution():
    called = []

    def handler(request):
        called.append(request)
        return _handler(request)

    def unsupported(request):
        return ServiceCapability(
            request.operation,
            False,
            Exactness.UNSUPPORTED,
            None,
            "coefficient domain is unsupported",
        )

    registry = ServiceRegistry(
        (ServiceRegistration("periodic.ext", handler, unsupported),)
    )
    with pytest.raises(ValueError, match="unsupported"):
        registry.dispatch(ServiceRequest("periodic.ext", {"orders": [2, 4]}))
    assert called == []


def test_cache_key_covers_backend_assumptions_certificate_and_search_domain():
    base = ServiceRequest(
        "boundary.enumerate",
        {"algebra": "A"},
        CertificateLevel.STANDARD,
        ("finite domain",),
        _fingerprint(),
        "raw",
        {"period": [2], "depth": 3},
    )
    variants = (
        ServiceRequest(
            base.operation,
            base.input_data,
            CertificateLevel.FULL,
            base.assumptions,
            base.backend_fingerprint,
            base.equivalence_relation,
            base.search_domain,
        ),
        ServiceRequest(
            base.operation,
            base.input_data,
            base.requested_certificate_level,
            ("different assumption",),
            base.backend_fingerprint,
            base.equivalence_relation,
            base.search_domain,
        ),
        ServiceRequest(
            base.operation,
            base.input_data,
            base.requested_certificate_level,
            base.assumptions,
            _fingerprint("2"),
            base.equivalence_relation,
            base.search_domain,
        ),
        ServiceRequest(
            base.operation,
            base.input_data,
            base.requested_certificate_level,
            base.assumptions,
            base.backend_fingerprint,
            "local_clifford",
            base.search_domain,
        ),
        ServiceRequest(
            base.operation,
            base.input_data,
            base.requested_certificate_level,
            base.assumptions,
            base.backend_fingerprint,
            base.equivalence_relation,
            {"period": [2], "depth": 4},
        ),
    )
    assert len({base.cache_key, *(item.cache_key for item in variants)}) == 6

    cache = InMemoryServiceCache()
    result = _handler(base)
    cache.put(base, result)
    assert cache.get(base) == result
    assert all(cache.get(item) is None for item in variants)
