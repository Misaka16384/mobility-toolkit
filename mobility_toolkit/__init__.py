# mobility_toolkit package

# Single source of truth for the version. `pyproject.toml` derives the package
# version from this attribute (dynamic = ["version"]), and `tools/release.py`
# bumps this line. Keep it a plain string literal so setuptools can read it
# statically at build time without importing the package.
__version__ = "0.1.6"

import sys
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(1000000)

from mobility_toolkit.services import (
    ServiceExecutor,
    ServiceExecution,
    ServiceRequest,
    default_service_catalog,
    execute_service_payload,
    execute_service_request,
    stream_service_payload,
    streamable_operations,
)

__all__ = [
    "__version__",
    "ServiceExecutor",
    "ServiceExecution",
    "ServiceRequest",
    "default_service_catalog",
    "execute_service_payload",
    "execute_service_request",
    "stream_service_payload",
    "streamable_operations",
]
