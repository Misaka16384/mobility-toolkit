"""Small model registry for examples and tests."""

from mobility_toolkit.boundary_gauge.models.models_2d import (
    get_Z4_double_semion_params,
    get_Z4_toric_code_params,
    get_fish_toric_code_params,
    get_toric_code_params,
)
from mobility_toolkit.boundary_gauge.models.models_3d import (
    get_3d_toric_code_params,
    get_haah_cubic_code_params,
    get_xcube_code_params,
)

_REGISTRY = {
    "toric_2d": get_toric_code_params,
    "fish_toric_2d": get_fish_toric_code_params,
    "z4_toric_2d": get_Z4_toric_code_params,
    "z4_double_semion_2d": get_Z4_double_semion_params,
    "toric_3d": get_3d_toric_code_params,
    "xcube_3d": get_xcube_code_params,
    "haah_3d": get_haah_cubic_code_params,
}


def get_model_params(name: str):
    """Return generator params by registry name."""
    try:
        return _REGISTRY[name]()
    except KeyError as exc:
        choices = ", ".join(sorted(_REGISTRY))
        raise KeyError(f"unknown model {name!r}; choices: {choices}") from exc


__all__ = ["get_model_params"]
