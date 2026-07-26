import copy
import json
import sqlite3

import pytest

pytest.importorskip("flint")

from mobility_toolkit.services import (
    SQLiteCheckpointStore,
    execute_service_payload,
    stream_service_payload,
)


_FINGERPRINT = {
    "backend": "python-flint",
    "version": "",
    "algorithm_family": "finite-integer",
}


def _request(checkpoint=None):
    input_data = {
        "model": "z2-toric",
        "budget": {
            "max_work_units": 1,
            "max_results": 100,
            "max_elements": 100,
            "max_subgroups": 100,
        },
    }
    if checkpoint is not None:
        input_data["checkpoint"] = checkpoint
    return {
        "operation": "boundary.completion2d.enumerate",
        "input_data": input_data,
        "requested_certificate_level": "full",
        "backend_fingerprint": _FINGERPRINT,
    }


def _first_page():
    return next(stream_service_payload(_request(), max_pages=1))


def test_store_is_explicit_and_resume_survives_reopen(tmp_path):
    database = tmp_path / "checkpoints.sqlite3"
    assert not database.exists()

    first = _first_page()
    with SQLiteCheckpointStore(database) as store:
        assert database.exists()
        record = store.save_page("research-run", first)
        assert record.sequence == 1
        assert store.list() == (record,)

    with SQLiteCheckpointStore(database) as reopened:
        resume_payload = reopened.load_resume_payload("research-run")
        assert "max_pages" not in resume_payload["input_data"]
        assert (
            resume_payload["input_data"]["checkpoint"]
            == first["result"]["value"]["next_checkpoint"]
        )
        completed = list(
            stream_service_payload(resume_payload, max_pages=100)
        )
        assert completed
        assert completed[-1]["result"]["value"]["next_checkpoint"] is None
        assert reopened.clear("research-run") == 1
        assert reopened.list() == ()


def test_updates_require_a_monotonic_contiguous_checkpoint_chain(tmp_path):
    first = _first_page()
    with SQLiteCheckpointStore(tmp_path / "chain.sqlite3") as store:
        record = store.save_page("chain", first, sequence=1)
        resume = store.load_resume_payload("chain")
        second = next(stream_service_payload(resume, max_pages=1))
        record = store.save_page("chain", second, sequence=2)
        assert record.sequence == 2
        assert store.list("chain")[0].sequence == 2

        with pytest.raises(ValueError, match="regression"):
            store.save_page("chain", first)
        with pytest.raises(ValueError, match="expected 3"):
            third_resume = store.load_resume_payload("chain")
            third = next(stream_service_payload(third_resume, max_pages=1))
            store.save_page("chain", third, sequence=2)


def test_rejects_completed_malformed_nonstreamable_and_tampered_pages(tmp_path):
    first = _first_page()
    with SQLiteCheckpointStore(tmp_path / "invalid.sqlite3") as store:
        malformed = copy.deepcopy(first)
        malformed["result"]["value"]["next_checkpoint"] = "opaque"
        with pytest.raises(TypeError, match="next_checkpoint"):
            store.save_page("malformed", malformed)

        nonstreamable = copy.deepcopy(first)
        nonstreamable = execute_service_payload(
            {
                "operation": "finite.code.capabilities",
                "input_data": {},
            }
        )
        with pytest.raises(ValueError, match="not streamable"):
            store.save_page("nonstreamable", nonstreamable)

        bad_request_hash = copy.deepcopy(first)
        bad_request_hash["request"]["canonical_input_hash"] = "0" * 64
        with pytest.raises(ValueError, match="canonical_input_hash"):
            store.save_page("bad-hash", bad_request_hash)

        store.save_page("bound", first)
        foreign = _request()
        foreign["input_data"]["model"] = "double-semion"
        foreign_page = next(stream_service_payload(foreign, max_pages=1))
        with pytest.raises(ValueError, match="foreign operation or base request"):
            store.save_page("bound", foreign_page)

        completed = list(stream_service_payload(_request(), max_pages=100))[-1]
        assert completed["result"]["value"]["next_checkpoint"] is None
        with pytest.raises(ValueError, match="no checkpoint"):
            store.save_page("completed", completed)


def test_load_rejects_tampered_database_identity(tmp_path):
    database = tmp_path / "tampered.sqlite3"
    first = _first_page()
    with SQLiteCheckpointStore(database) as store:
        store.save_page("tampered", first)

    connection = sqlite3.connect(str(database))
    with connection:
        connection.execute(
            """
            UPDATE service_checkpoints
            SET base_request_hash = ?
            WHERE session_id = ?
            """,
            ("0" * 64, "tampered"),
        )
    connection.close()

    with SQLiteCheckpointStore(database) as store:
        with pytest.raises(ValueError, match="base request hash"):
            store.load_resume_payload("tampered")


def test_execution_schema_and_canonical_json_are_strict(tmp_path):
    first = _first_page()
    with SQLiteCheckpointStore(tmp_path / "strict.sqlite3") as store:
        extra = copy.deepcopy(first)
        extra["legacy"] = True
        with pytest.raises(ValueError, match="invalid service execution"):
            store.save_page("extra", extra)

        floating = copy.deepcopy(first)
        floating["result"]["value"]["next_checkpoint"]["legacy_score"] = 0.5
        with pytest.raises(TypeError, match="floating-point"):
            store.save_page("float", floating)

        store.save_page("json", json.loads(json.dumps(first)))
