import sqlite3

from mobility_toolkit.registry import ModelRegistry


def test_homology_cache_key_covers_the_invariant_contract(tmp_path):
    registry = ModelRegistry(str(tmp_path / "models.db"))
    matrix = [["1 - t", "1 - u", "0", "0"], ["0", "0", "y - 1", "1 - x"]]
    key = {
        "spatial_dim": 2,
        "validate_stabilizer": True,
        "convention": "generator-rows-x-then-z",
        "invariant_version": "ruba-yang-qbar-v2",
    }

    registry.cache_annihilator(
        matrix,
        2,
        0,
        0,
        ["Q0"],
        ["x - 1", "y - 1"],
        **key,
    )
    assert registry.get_cached_annihilator(matrix, 2, 0, **key)["krull_dimension"] == 0

    variants = [
        {**key, "spatial_dim": 3},
        {**key, "validate_stabilizer": False},
        {**key, "convention": "legacy-raw-coker"},
        {**key, "invariant_version": "ruba-yang-v2"},
    ]
    for variant in variants:
        assert registry.get_cached_annihilator(matrix, 2, 0, **variant) is None
    assert registry.get_cached_annihilator(matrix, 2, 1, **key) is None


def test_legacy_cache_rows_are_not_reused_by_new_invariant(tmp_path):
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE computations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qudit_dim INTEGER NOT NULL,
            stabilizer_matrix TEXT NOT NULL,
            p_ext INTEGER NOT NULL,
            annihilator_generators TEXT,
            krull_dimension INTEGER,
            ext_modules TEXT,
            mobility_dimension INTEGER,
            valuation_matrix TEXT,
            kernel_basis TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO computations
            (qudit_dim, stabilizer_matrix, p_ext, krull_dimension, ext_modules,
             annihilator_generators)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (2, '[["legacy"]]', 0, 99, '["legacy"]', "[]"),
    )
    conn.commit()
    conn.close()

    registry = ModelRegistry(str(db_path))
    conn = sqlite3.connect(db_path)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(computations)")}
    conn.close()
    assert {"spatial_dim", "validate_stabilizer", "convention", "invariant_version"} <= columns
    assert registry.get_cached_annihilator([["legacy"]], 2, 0) is None
