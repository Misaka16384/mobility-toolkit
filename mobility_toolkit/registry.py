import os
import glob
import sqlite3
import json
from typing import List, Dict, Any

# Define the database path relative to this file for self-contained distribution
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mobility_models.db")

def seed_database(cursor):
    """Seed the database with standard models."""
    seed_models = [
        {
            "name": "Toric Code",
            "qudit_dim": 2,
            "spatial_dim": 2,
            "stabilizer_matrix": "[[\"1 - x\", \"1 - y\", \"0\", \"0\"], [\"0\", \"0\", \"1 - y\", \"1 - x\"]]",
            "d0": 0,
            "d1": -1,
            "gsd_val": 4,
            "l_x": 1,
            "l_y": 1,
            "is_topological": True,
            "description": "2D Toric Code point-like excitations"
        },
        {
            "name": "X-Cube Model",
            "qudit_dim": 2,
            "spatial_dim": 3,
            "stabilizer_matrix": "[[\"1 - x\", \"1 - y\", \"1 - z\", \"0\"], [\"0\", \"1 - y\", \"1 - z\", \"1 - x\"]]",
            "d0": 2,
            "d1": 1,
            "gsd_val": None,
            "l_x": 1,
            "l_y": 1,
            "is_topological": False,
            "description": "3D X-Cube model"
        },
        {
            "name": "WCF Code",
            "qudit_dim": 12,
            "spatial_dim": 2,
            "stabilizer_matrix": "[[\"t - 5\", \"u - 5\", \"0\", \"0\"], [\"0\", \"0\", \"y - 5\", \"5 - x\"]]",
            "d0": 0,
            "d1": -1,
            "gsd_val": 144,
            "l_x": 2,
            "l_y": 2,
            "is_topological": True,
            "description": "WCF Code bivariate bicycle code"
        },
        {
            "name": "DCY Code",
            "qudit_dim": 12,
            "spatial_dim": 2,
            "stabilizer_matrix": "[[\"t^2 - 11*t + 10\", \"u^2 - 11*u + 10\", \"0\", \"0\"], [\"0\", \"0\", \"y^2 - 11*y + 10\", \"-x^2 + 11*x - 10\"]]",
            "d0": 0,
            "d1": -1,
            "gsd_val": 104976,
            "l_x": 3,
            "l_y": 3,
            "is_topological": True,
            "description": "DCY Code bivariate bicycle code"
        },
        {
            "name": "Chamon's Cubic Code",
            "qudit_dim": 2,
            "spatial_dim": 3,
            "stabilizer_matrix": "[[\"y + z + x*y + x*z\", \"x + z + x*y + y*z\"]]",
            "d0": 1,
            "d1": -1,
            "gsd_val": None,
            "l_x": 1,
            "l_y": 1,
            "is_topological": False,
            "description": "Chamon's Cubic Code commuting representation"
        }
    ]
    
    for m in seed_models:
        cursor.execute("""
            INSERT OR REPLACE INTO models 
            (name, qudit_dim, spatial_dim, stabilizer_matrix, d0, d1, gsd_val, l_x, l_y, is_topological, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m["name"], m["qudit_dim"], m["spatial_dim"], m["stabilizer_matrix"],
            m["d0"], m["d1"], m["gsd_val"], m["l_x"], m["l_y"], m["is_topological"], m["description"]
        ))

def query_vector_db(action: str, params: dict = None) -> dict:
    """Manages the mobility models database.
    
    Args:
        action: Database action to perform ('init', 'seed', 'sync', 'query').
        params: Additional parameters for the query action (e.g. {'query': 'SELECT * FROM models'}).
        
    Returns:
        A dictionary containing the status and results of the query or action.
    """
    if params is None:
        params = {}
        
    db_dir = os.path.dirname(DB_PATH)
    os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Create table schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                qudit_dim INTEGER NOT NULL,
                spatial_dim INTEGER NOT NULL,
                stabilizer_matrix TEXT NOT NULL,
                d0 INTEGER,
                d1 INTEGER,
                gsd_val INTEGER,
                l_x INTEGER,
                l_y INTEGER,
                is_topological BOOLEAN,
                description TEXT
            );
        """)
        
        if action in ("init", "seed"):
            seed_database(cursor)
            conn.commit()
            return {"status": "success", "message": "Database initialized and seeded."}
            
        elif action == "sync":
            # Determine project root dynamically relative to this file
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            discoveries_dirs = [
                os.path.join(project_root, "output", "discoveries"),
                os.path.join(project_root, "mobility_toolkit", "output", "discoveries")
            ]
            json_files = []
            for d_dir in discoveries_dirs:
                if os.path.exists(d_dir):
                    json_files.extend(glob.glob(os.path.join(d_dir, "*.json")))
            synced_count = 0
            
            for file_path in json_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    required_fields = ["name", "qudit_dim", "spatial_dim", "stabilizer_matrix"]
                    if all(field in data for field in required_fields):
                        cursor.execute("""
                            INSERT OR REPLACE INTO models 
                            (name, qudit_dim, spatial_dim, stabilizer_matrix, d0, d1, gsd_val, l_x, l_y, is_topological, description)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            data["name"], data["qudit_dim"], data["spatial_dim"], data["stabilizer_matrix"],
                            data.get("d0"), data.get("d1"), data.get("gsd_val"), data.get("l_x"), data.get("l_y"),
                            data.get("is_topological"), data.get("description")
                        ))
                        synced_count += 1
                except Exception:
                    pass
            conn.commit()
            return {"status": "success", "message": f"Synced {synced_count} models from discoveries."}
            
        elif action == "query":
            query_str = params.get("query", "SELECT * FROM models")
            cursor.execute(query_str)
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            return {"status": "success", "results": results}
            
        else:
            raise ValueError(f"Unknown action: {action}")
            
    finally:
        conn.close()


class ModelRegistry:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Ensure tables exist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    qudit_dim INTEGER NOT NULL,
                    spatial_dim INTEGER NOT NULL,
                    stabilizer_matrix TEXT NOT NULL,
                    d0 INTEGER,
                    d1 INTEGER,
                    gsd_val INTEGER,
                    l_x INTEGER,
                    l_y INTEGER,
                    is_topological BOOLEAN,
                    description TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS computations (
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
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def get_cached_annihilator(self, stabilizer_matrix: List[List[str]], qudit_dim: int, p_ext: int) -> Dict[str, Any]:
        """Query computations table for matching qudit_dim, stabilizer_matrix, and p_ext.
        If found, return dictionary containing krull_dimension, ext_modules, and annihilator_generators.
        Otherwise return None.
        """
        matrix_str = json.dumps(stabilizer_matrix)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT krull_dimension, ext_modules, annihilator_generators 
                FROM computations 
                WHERE qudit_dim = ? AND stabilizer_matrix = ? AND p_ext = ?
            """, (qudit_dim, matrix_str, p_ext))
            row = cursor.fetchone()
            if row is not None:
                krull_dimension, ext_modules_str, annihilator_generators_str = row
                ext_modules = json.loads(ext_modules_str) if ext_modules_str else None
                annihilator_generators = json.loads(annihilator_generators_str) if annihilator_generators_str else None
                return {
                    "krull_dimension": krull_dimension,
                    "ext_modules": ext_modules,
                    "annihilator_generators": annihilator_generators
                }
            return None
        finally:
            conn.close()

    def cache_annihilator(self, stabilizer_matrix: List[List[str]], qudit_dim: int, p_ext: int, krull_dimension: int, ext_modules: List[str], annihilator_generators: List[str]) -> None:
        """Insert/replace row in computations table."""
        matrix_str = json.dumps(stabilizer_matrix)
        ext_modules_str = json.dumps(ext_modules)
        annihilator_generators_str = json.dumps(annihilator_generators)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id FROM computations 
                WHERE qudit_dim = ? AND stabilizer_matrix = ? AND p_ext = ?
            """, (qudit_dim, matrix_str, p_ext))
            row = cursor.fetchone()
            if row is not None:
                cursor.execute("""
                    UPDATE computations 
                    SET krull_dimension = ?, ext_modules = ?, annihilator_generators = ?
                    WHERE id = ?
                """, (krull_dimension, ext_modules_str, annihilator_generators_str, row[0]))
            else:
                cursor.execute("""
                    INSERT INTO computations 
                    (qudit_dim, stabilizer_matrix, p_ext, krull_dimension, ext_modules, annihilator_generators)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (qudit_dim, matrix_str, p_ext, krull_dimension, ext_modules_str, annihilator_generators_str))
            conn.commit()
        finally:
            conn.close()

    def get_cached_properties(self, generators: List[str], qudit_dim: int) -> Dict[str, Any]:
        """Query computations table for matching qudit_dim and annihilator_generators (sorted).
        If found and mobility_dimension is not null, return dictionary containing
        mobility_dimension, valuation_matrix, and kernel_basis. Otherwise return None.
        """
        sorted_gens = sorted(generators)
        gens_str = json.dumps(sorted_gens)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT mobility_dimension, valuation_matrix, kernel_basis 
                FROM computations 
                WHERE qudit_dim = ? AND annihilator_generators = ?
            """, (qudit_dim, gens_str))
            rows = cursor.fetchall()
            for row in rows:
                mobility_dimension, valuation_matrix_str, kernel_basis_str = row
                if mobility_dimension is not None:
                    valuation_matrix = json.loads(valuation_matrix_str) if valuation_matrix_str else None
                    kernel_basis = json.loads(kernel_basis_str) if kernel_basis_str else None
                    return {
                        "mobility_dimension": mobility_dimension,
                        "valuation_matrix": valuation_matrix,
                        "kernel_basis": kernel_basis
                    }
            return None
        finally:
            conn.close()

    def cache_properties(self, generators: List[str], qudit_dim: int, mobility_dimension: int, valuation_matrix: List[List[int]], kernel_basis: List[List[int]]) -> None:
        """Insert or update the matching computations row. If no row exists matching qudit_dim and generators, insert a new one."""
        sorted_gens = sorted(generators)
        gens_str = json.dumps(sorted_gens)
        val_matrix_str = json.dumps(valuation_matrix)
        ker_basis_str = json.dumps(kernel_basis)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id FROM computations 
                WHERE qudit_dim = ? AND annihilator_generators = ?
            """, (qudit_dim, gens_str))
            row = cursor.fetchone()
            if row is not None:
                cursor.execute("""
                    UPDATE computations 
                    SET mobility_dimension = ?, valuation_matrix = ?, kernel_basis = ?
                    WHERE id = ?
                """, (mobility_dimension, val_matrix_str, ker_basis_str, row[0]))
            else:
                cursor.execute("""
                    INSERT INTO computations 
                    (qudit_dim, stabilizer_matrix, p_ext, annihilator_generators, krull_dimension, ext_modules, mobility_dimension, valuation_matrix, kernel_basis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (qudit_dim, "[]", -1, gens_str, None, None, mobility_dimension, val_matrix_str, ker_basis_str))
            conn.commit()
        finally:
            conn.close()
