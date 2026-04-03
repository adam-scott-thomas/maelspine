import json
import os
import tempfile

import pytest
from spine import Core, CoreFrozen, CapabilityNotFound


# ── Audit trail + provenance ──────────────────────────────

class TestAudit:
    def test_off_by_default(self):
        c = Core()
        assert c._audit is False
        assert c._audit_log == []
        assert c._provenance == {}

    def test_provenance_on_register(self):
        c = Core(audit=True)
        c.register("x", 1)
        assert "x" in c._provenance
        prov = c._provenance["x"]
        assert "source" in prov
        assert "registered_at" in prov
        assert "test_heavy_plus" in prov["source"]

    def test_audit_log_on_get(self):
        c = Core(audit=True)
        c.register("x", 1)
        c.boot()
        c.get("x")
        assert len(c._audit_log) == 1
        entry = c._audit_log[0]
        assert entry["cap"] == "x"
        assert "caller" in entry
        assert "at" in entry
        assert "test_heavy_plus" in entry["caller"]

    def test_multiple_gets(self):
        c = Core(audit=True)
        c.register("a", 1)
        c.register("b", 2)
        c.boot()
        c.get("a")
        c.get("b")
        c.get("a")
        assert len(c._audit_log) == 3
        assert c._audit_log[0]["cap"] == "a"
        assert c._audit_log[1]["cap"] == "b"
        assert c._audit_log[2]["cap"] == "a"

    def test_no_audit_when_off(self):
        c = Core(audit=False)
        c.register("x", 1)
        c.boot()
        c.get("x")
        assert c._audit_log == []
        assert c._provenance == {}

    def test_audit_via_zone(self):
        Core._reset_zones()
        c = Core.zone("forensic", audit=True)
        c.register("x", 1)
        c.boot()
        c.get("x")
        assert len(c._audit_log) == 1
        assert "x" in c._provenance
        Core._reset_zones()

    def test_audit_via_test_harness(self):
        c = Core.test(audit=True, x=1)
        c.get("x")
        assert len(c._audit_log) == 1


# ── On-boot hooks ────────────────────────────────────────

class TestOnBootHooks:
    def test_fires_at_boot(self):
        captured = []
        c = Core()
        c.on_boot(lambda core: captured.append(core.context.env))
        c.boot(env="prod")
        assert captured == ["prod"]

    def test_receives_frozen_core(self):
        captured = []
        c = Core()
        c.register("x", 42)
        c.on_boot(lambda core: captured.append(core.is_frozen))
        c.boot()
        assert captured == [True]

    def test_cannot_register_in_hook(self):
        c = Core()
        c.on_boot(lambda core: core.register("sneaky", "value"))
        c.boot()  # hook crash caught, boot succeeds
        assert c.is_frozen

    def test_multiple_hooks_in_order(self):
        order = []
        c = Core()
        c.on_boot(lambda core: order.append("first"))
        c.on_boot(lambda core: order.append("second"))
        c.boot()
        assert order == ["first", "second"]

    def test_after_boot_raises(self):
        c = Core()
        c.boot()
        with pytest.raises(CoreFrozen):
            c.on_boot(lambda core: None)

    def test_crash_doesnt_block(self):
        reached = []
        c = Core()
        c.on_boot(lambda core: 1 / 0)
        c.on_boot(lambda core: reached.append(True))
        c.boot()
        assert reached == [True]


# ── Cross-spine bridges ──────────────────────────────────

class TestBridges:
    def setup_method(self):
        Core._reset_zones()

    def teardown_method(self):
        Core._reset_zones()

    def test_bridge_exposes_capability(self):
        core = Core.zone("core")
        core.register("paths.root", "/app")
        core.boot()
        shell = Core.zone("shell")
        shell.boot()
        core.bridge("paths.root", to="shell")
        assert shell.get("paths.root") == "/app"

    def test_bridge_only_named_cap(self):
        core = Core.zone("core")
        core.register("paths.root", "/app")
        core.register("secret.key", "shhh")
        core.boot()
        shell = Core.zone("shell")
        shell.boot()
        core.bridge("paths.root", to="shell")
        assert shell.get("paths.root") == "/app"
        with pytest.raises(CapabilityNotFound):
            shell.get("secret.key")

    def test_bridge_before_boot_raises(self):
        core = Core.zone("core")
        core.register("x", 1)
        with pytest.raises(Exception):
            core.bridge("x", to="shell")

    def test_bridge_missing_cap_raises(self):
        core = Core.zone("core")
        core.boot()
        with pytest.raises(CapabilityNotFound):
            core.bridge("nope", to="shell")

    def test_bridge_missing_zone_raises(self):
        core = Core.zone("core")
        core.register("x", 1)
        core.boot()
        with pytest.raises(ValueError, match="does not exist"):
            core.bridge("x", to="nowhere")

    def test_bridged_tracks_hits(self):
        core = Core.zone("core")
        core.register("x", 1)
        core.boot()
        shell = Core.zone("shell")
        shell.boot()
        core.bridge("x", to="shell")
        shell.get("x")
        shell.get("x")
        assert shell.hits_for("x") == 2

    def test_bridge_respects_typed_get(self):
        core = Core.zone("core")
        core.register("count", 42)
        core.boot()
        shell = Core.zone("shell")
        shell.boot()
        core.bridge("count", to="shell")
        assert shell.get("count", int) == 42
        with pytest.raises(TypeError):
            shell.get("count", str)

    def test_has_sees_bridged(self):
        core = Core.zone("core")
        core.register("x", 1)
        core.boot()
        shell = Core.zone("shell")
        shell.boot()
        assert not shell.has("x")
        core.bridge("x", to="shell")
        assert shell.has("x")


# ── Forensics module ─────────────────────────────────────

class TestForensics:
    def test_audit_log_unfiltered(self):
        from spine.forensics import audit_log
        c = Core(audit=True)
        c.register("a", 1)
        c.register("b", 2)
        c.boot()
        c.get("a")
        c.get("b")
        c.get("a")
        log = audit_log(c)
        assert len(log) == 3

    def test_audit_log_filter_by_cap(self):
        from spine.forensics import audit_log
        c = Core(audit=True)
        c.register("a", 1)
        c.register("b", 2)
        c.boot()
        c.get("a")
        c.get("b")
        c.get("a")
        assert len(audit_log(c, cap="a")) == 2

    def test_audit_log_filter_by_caller(self):
        from spine.forensics import audit_log
        c = Core(audit=True)
        c.register("x", 1)
        c.boot()
        c.get("x")
        assert len(audit_log(c, caller="test_heavy_plus")) == 1

    def test_provenance_all(self):
        from spine.forensics import provenance
        c = Core(audit=True)
        c.register("x", 1)
        c.register("y", 2)
        c.boot()
        prov = provenance(c)
        assert "x" in prov
        assert "y" in prov

    def test_provenance_single(self):
        from spine.forensics import provenance
        c = Core(audit=True)
        c.register("x", 1)
        c.boot()
        prov = provenance(c, name="x")
        assert "source" in prov

    def test_boot_graph(self):
        from spine.forensics import boot_graph
        c = Core()
        c.expect("svc.a", requires=["db.conn", "cache"])
        c.expect("svc.b", requires=["db.conn"])
        c.register("svc.a", "a")
        c.register("svc.b", "b")
        c.register("db.conn", "conn")
        c.register("cache", "c")
        c.boot()
        graph = boot_graph(c)
        assert set(graph["nodes"]) == {"svc.a", "svc.b", "db.conn", "cache"}
        assert {"from": "svc.a", "to": "db.conn"} in graph["edges"]
        assert {"from": "svc.a", "to": "cache"} in graph["edges"]
        assert {"from": "svc.b", "to": "db.conn"} in graph["edges"]

    def test_boot_graph_no_expectations(self):
        from spine.forensics import boot_graph
        c = Core.test(x=1)
        graph = boot_graph(c)
        assert graph["nodes"] == ["x"]
        assert graph["edges"] == []


# ── Replay ────────────────────────────────────────────────

class TestReplay:
    def test_creates_frozen_core(self):
        from spine.forensics import replay
        c = Core.test(x=1, y="two")
        replayed = replay(c.snapshot())
        assert replayed.is_frozen
        assert replayed.get("x") == 1
        assert replayed.get("y") == "two"

    def test_preserves_env(self):
        from spine.forensics import replay
        c = Core()
        c.register("x", 1)
        c.boot(env="prod", session="s1")
        replayed = replay(c.snapshot())
        assert replayed.context.env == "prod"
        assert replayed.context.session == "s1"

    def test_preserves_zone_name(self):
        from spine.forensics import replay
        Core._reset_zones()
        c = Core.zone("myzone")
        c.register("x", 1)
        c.boot()
        replayed = replay(c.snapshot())
        assert replayed._zone_name == "myzone"
        Core._reset_zones()

    def test_non_serializable_stored_as_repr(self):
        from spine.forensics import replay
        c = Core()
        c.register("thing", object())
        c.boot()
        replayed = replay(c.snapshot())
        assert isinstance(replayed.get("thing"), str)
        assert "object" in replayed.get("thing")

    def test_from_export(self):
        from spine.forensics import from_export
        c = Core.test(x=42, y="hello")
        path = os.path.join(tempfile.gettempdir(), "spine_test.json")
        try:
            with open(path, "w") as f:
                f.write(c.to_json())
            replayed = from_export(path)
            assert replayed.is_frozen
            assert replayed.get("x") == 42
            assert replayed.get("y") == "hello"
        finally:
            os.unlink(path)

    def test_hits_start_at_zero(self):
        from spine.forensics import replay
        c = Core.test(x=1)
        c.get("x")
        c.get("x")
        assert c.hits_for("x") == 2
        replayed = replay(c.snapshot())
        assert replayed.hits_for("x") == 0
