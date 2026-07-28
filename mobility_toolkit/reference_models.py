"""Validated reference presentations used by examples and regression tests.

Every row is one stabilizer generator in ``[X_1,...,X_q,Z_1,...,Z_q]``
coordinates.  Keep algebra-only toy presentations out of this module.
"""

# A translation-equivalent orientation of the conventional 2D toric-code map.
TORIC_CODE_2D = [
    ["1 - t", "1 - u", "0", "0"],
    ["0", "0", "y - 1", "1 - x"],
]

# Ruba--Yang Eq. (98): the paper's 6 x 3 sigma, transposed into generator rows.
XCUBE_EQ98 = [
    [
        "1 + t + u + t*u",
        "1 + u + w + u*w",
        "1 + t + w + t*w",
        "0",
        "0",
        "0",
    ],
    ["0", "0", "0", "1 + z", "1 + x", "0"],
    ["0", "0", "0", "0", "1 + x", "1 + y"],
]

CHAMON_CUBIC = [[
    "y + z + x*y + x*z",
    "x + z + x*y + y*z",
]]

__all__ = ["TORIC_CODE_2D", "XCUBE_EQ98", "CHAMON_CUBIC"]
