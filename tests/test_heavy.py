import json
from pathlib import Path

import pytest
from spine import Core, CoreFrozen, CapabilityNotFound, ValidationError


# ── Typed retrieval ───────────────────────────────────────

class TestTypedGet:
    def test_correct_type(self):
        c = Core.test(paths_data="/tmp")
        assert c.get("paths.data", str) == "/tmp"

    def test_wrong_type_raises(self):
        c = Core.test(paths_data="/tmp")
        with pytest.raises(TypeError, match="expected type int, got str"):
            c.get("paths.data", int)

    def test_no_type_still_works(self):
        c = Core.test(paths_data="/tmp")
        assert c.get("paths.data") == "/tmp"

    def test_type_check_increments_hits(self):
        c = Core.test(x=42)
        c.get("x", int)
        assert c.hits_for("x") == 1

    def test_subclass_passes(self):
        c = Core()
        c.register("p", Path("/tmp"))
        c.boot()
        assert c.get("p", Path) == Path("/tmp")


# ── Boot expectations ─────────────────────────────────────

class TestExpectations:
    def test_required_present_passes(self):
        c = Core()
        c.expect("x", required=True)
        c.register("x", 1)
        c.boot()
        assert c.get("x") == 1

    def test_required_missing_raises(self):
        c = Core()
        c.expect("x", required=True)
        with pytest.raises(ValidationError, match="'x' not registered"):
            c.boot()

    def test_type_passes(self):
        c = Core()
        c.expect("x", expected_type=int)
        c.register("x", 42)
        c.boot()

    def test_type_fails(self):
        c = Core()
        c.expect("x", expected_type=int)
        c.register("x", "not an int")
        with pytest.raises(ValidationError, match="expected int, got str"):
            c.boot()

    def test_requires_present(self):
        c = Core()
        c.expect("svc.a", requires=["db.conn"])
        c.register("svc.a", "svc")
        c.register("db.conn", "conn")
        c.boot()

    def test_requires_missing(self):
        c = Core()
        c.expect("svc.a", requires=["db.conn"])
        c.register("svc.a", "svc")
        with pytest.raises(ValidationError, match="requires 'db.conn'"):
            c.boot()

    def test_expect_after_boot_raises(self):
        c = Core()
        c.boot()
        with pytest.raises(CoreFrozen):
            c.expect("x")

    def test_optional_missing_ok(self):
        c = Core()
        c.expect("x", required=False)
        c.boot()

    def test_optional_wrong_type_still_raises(self):
        c = Core()
        c.expect("x", required=False, expected_type=int)
        c.register("x", "str")
        with pytest.raises(ValidationError, match="expected int"):
            c.boot()

    def test_multiple_errors_reported(self):
        c = Core()
        c.expect("a", required=True)
        c.expect("b", required=True)
        with pytest.raises(ValidationError) as exc_info:
            c.boot()
        msg = str(exc_info.value)
        assert "'a'" in msg
        assert "'b'" in msg


# ── Snapshot + fingerprint ────────────────────────────────

class TestSnapshot:
    def test_structure(self):
        c = Core.test(paths_data="/tmp", db_backend="sqlite")
        snap = c.snapshot()
        assert snap["frozen"] is True
        assert snap["env"] == "test"
        assert "run_id" in snap
        assert "booted_at" in snap
        assert snap["capabilities"]["paths.data"] == "/tmp"

    def test_non_serializable_uses_repr(self):
        c = Core()
        obj = object()
        c.register("thing", obj)
        c.boot()
        snap = c.snapshot()
        assert snap["capabilities"]["thing"] == repr(obj)

    def test_includes_zone_name(self):
        Core._reset_zones()
        c = Core.zone("myzone")
        c.boot()
        snap = c.snapshot()
        assert snap["zone"] == "myzone"
        Core._reset_zones()

    def test_fingerprint_deterministic(self):
        c1 = Core.test(a=1, b="two")
        c2 = Core.test(a=1, b="two")
        assert c1.fingerprint() == c2.fingerprint()

    def test_fingerprint_changes(self):
        c1 = Core.test(a=1)
        c2 = Core.test(a=1, b=2)
        assert c1.fingerprint() != c2.fingerprint()

    def test_fingerprint_length(self):
        c = Core.test(x=1)
        assert len(c.fingerprint()) == 16

    def test_to_json_valid(self):
        c = Core.test(paths_data="/tmp")
        parsed = json.loads(c.to_json())
        assert parsed["capabilities"]["paths.data"] == "/tmp"

    def test_snapshot_before_boot(self):
        c = Core()
        c.register("x", 1)
        snap = c.snapshot()
        assert snap["frozen"] is False
        assert snap["env"] is None


# ── Groups + introspection ────────────────────────────────

class TestGroups:
    def test_matching(self):
        c = Core.test(paths_data="/data", paths_logs="/logs",
                      db_backend="sqlite")
        assert c.group("paths") == {
            "paths.data": "/data",
            "paths.logs": "/logs",
        }

    def test_no_match(self):
        c = Core.test(x=1)
        assert c.group("paths") == {}

    def test_dot_boundary(self):
        c = Core.test(pathsdata="/data", paths_real="/real")
        result = c.group("paths")
        assert "pathsdata" not in result
        assert result == {"paths.real": "/real"}


class TestIntrospection:
    def test_names_sorted(self):
        c = Core.test(b=2, a=1, c=3)
        assert c.names() == ["a", "b", "c"]

    def test_names_empty(self):
        c = Core()
        c.boot()
        assert c.names() == []

    def test_describe(self):
        c = Core.test(paths_data="/tmp")
        c.get("paths.data")
        c.get("paths.data")
        info = c.describe("paths.data")
        assert info["name"] == "paths.data"
        assert info["type"] == "str"
        assert info["hits"] == 2

    def test_describe_missing_raises(self):
        c = Core.test(x=1)
        with pytest.raises(CapabilityNotFound):
            c.describe("nope")

    def test_describe_includes_zone(self):
        Core._reset_zones()
        c = Core.zone("myzone")
        c.register("x", 1)
        c.boot()
        assert c.describe("x")["zone"] == "myzone"
        Core._reset_zones()
