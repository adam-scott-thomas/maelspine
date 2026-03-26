import pytest
from spine import Core, CoreFrozen, CoreNotBooted, CapabilityNotFound


class TestRegistration:
    def test_register_and_get(self):
        c = Core()
        c.register("paths.data", "/tmp/data")
        c.boot()
        assert c.get("paths.data") == "/tmp/data"

    def test_register_after_boot_raises(self):
        c = Core()
        c.boot()
        with pytest.raises(CoreFrozen):
            c.register("late", "value")

    def test_get_missing_raises(self):
        c = Core()
        c.register("paths.data", "/tmp")
        c.boot()
        with pytest.raises(CapabilityNotFound):
            c.get("paths.nope")

    def test_has(self):
        c = Core()
        c.register("x", 1)
        assert c.has("x")
        assert not c.has("y")


class TestBoot:
    def test_double_boot_raises(self):
        c = Core()
        c.boot()
        with pytest.raises(CoreFrozen):
            c.boot()

    def test_context_before_boot_raises(self):
        c = Core()
        with pytest.raises(CoreNotBooted):
            _ = c.context

    def test_context_after_boot(self):
        c = Core()
        c.boot(env="prod", session="s1")
        assert c.context.env == "prod"
        assert c.context.session == "s1"
        assert c.context.run_id  # non-empty


class TestHits:
    def test_hit_tracking(self):
        c = Core()
        c.register("a", 1)
        c.register("b", 2)
        c.boot()
        c.get("a")
        c.get("a")
        c.get("b")
        assert c.hits_for("a") == 2
        assert c.hits_for("b") == 1
        assert c.hits_total() == 3

    def test_unused(self):
        c = Core()
        c.register("used", 1)
        c.register("unused", 2)
        c.boot()
        c.get("used")
        assert c.hits_unused() == ["unused"]


class TestTestHarness:
    def test_core_test(self):
        c = Core.test(paths_data="/tmp", db_backend="sqlite")
        assert c.get("paths.data") == "/tmp"
        assert c.get("db.backend") == "sqlite"
        assert c.context.env == "test"
        assert c.is_frozen


class TestSingleton:
    def setup_method(self):
        Core._reset_instance()

    def teardown_method(self):
        Core._reset_instance()

    def test_boot_once(self):
        def setup(c):
            c.register("x", 42)
            c.boot()
        Core.boot_once(setup)
        assert Core.instance().get("x") == 42

    def test_boot_once_idempotent(self):
        def setup(c):
            c.register("x", 1)
            c.boot()
        c1 = Core.boot_once(setup)
        c2 = Core.boot_once(lambda c: None)  # ignored
        assert c1 is c2

    def test_instance_before_boot_raises(self):
        with pytest.raises(CoreNotBooted):
            Core.instance()

    def test_boot_once_without_boot_raises(self):
        with pytest.raises(CoreNotBooted):
            Core.boot_once(lambda c: None)


class TestErrorHooks:
    def test_error_hook_fires(self):
        captured = []
        c = Core()
        c.on_error(lambda d: captured.append(d))
        c.register("a", 1)
        c.boot()
        with pytest.raises(CapabilityNotFound):
            c.get("b")
        assert len(captured) == 1
        assert captured[0]["error_type"] == "capability_not_found"

    def test_close_matches(self):
        captured = []
        c = Core()
        c.on_error(lambda d: captured.append(d))
        c.register("paths.audit", "/audit")
        c.boot()
        with pytest.raises(CapabilityNotFound):
            c.get("paths.audi")
        assert "paths.audit" in captured[0]["close_matches"]
