import pytest
from spine import Core, CoreNotBooted, CapabilityNotFound


class TestZones:
    def setup_method(self):
        Core._reset_zones()

    def teardown_method(self):
        Core._reset_zones()

    def test_zone_creates_core(self):
        c = Core.zone("core")
        assert isinstance(c, Core)
        assert c._zone_name == "core"

    def test_zone_returns_same_instance(self):
        c1 = Core.zone("core")
        c2 = Core.zone("core")
        assert c1 is c2

    def test_zones_are_isolated(self):
        core = Core.zone("core")
        shell = Core.zone("shell")
        core.register("core.x", 1)
        core.boot()
        shell.register("shell.y", 2)
        shell.boot()
        assert core.get("core.x") == 1
        assert shell.get("shell.y") == 2
        with pytest.raises(CapabilityNotFound):
            core.get("shell.y")
        with pytest.raises(CapabilityNotFound):
            shell.get("core.x")

    def test_three_zones_fully_isolated(self):
        core = Core.zone("core")
        shell = Core.zone("shell")
        runtime = Core.zone("runtime")
        core.register("core.l0", "legality")
        shell.register("shell.token", "tok")
        runtime.register("runtime.limiter", "lim")
        core.boot()
        shell.boot()
        runtime.boot()
        assert core.get("core.l0") == "legality"
        assert shell.get("shell.token") == "tok"
        assert runtime.get("runtime.limiter") == "lim"
        with pytest.raises(CapabilityNotFound):
            runtime.get("core.l0")
        with pytest.raises(CapabilityNotFound):
            core.get("runtime.limiter")

    def test_zone_passes_kwargs(self):
        c = Core.zone("forensic", audit=True)
        assert c._audit is True

    def test_reset_zones_clears_all(self):
        Core.zone("a")
        Core.zone("b")
        Core._reset_zones()
        c = Core.zone("a")
        assert not c.is_frozen


class TestBackwardCompat:
    def setup_method(self):
        Core._reset_zones()

    def teardown_method(self):
        Core._reset_zones()

    def test_boot_once_still_works(self):
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
        c2 = Core.boot_once(lambda c: None)
        assert c1 is c2

    def test_instance_before_boot_raises(self):
        with pytest.raises(CoreNotBooted):
            Core.instance()

    def test_boot_once_stores_in_default_zone(self):
        def setup(c):
            c.boot()
        Core.boot_once(setup)
        assert Core.zone("default") is Core.instance()

    def test_reset_instance_clears_default_zone(self):
        def setup(c):
            c.boot()
        Core.boot_once(setup)
        Core._reset_instance()
        with pytest.raises(CoreNotBooted):
            Core.instance()

    def test_boot_once_without_boot_raises(self):
        with pytest.raises(CoreNotBooted):
            Core.boot_once(lambda c: None)
