# spine

> **⚠ DEPRECATED — `maelspine` is frozen at 0.3.0. Use [`ghostspine`](https://github.com/adam-scott-thomas/ghostspine) instead.**
>
> The two packages are byte-identical (both ship the same `spine/` module). They cannot be installed side-by-side. Going forward, all GhostLogic SDK consumers depend on `ghostspine`. `maelspine` 0.3.0 stays on PyPI for existing installs but receives no further releases. See [DEPRECATED.md](./DEPRECATED.md).

Minimal runtime coordination layer for Python projects.

One registry. One freeze. One place where reality gets decided.

> **This README is for humans browsing GitHub.** The complete technical reference lives as inline comments at the top of each `.py` file — that's where AI assistants should look. Open `core.py` or `observers.py` and read the comment block before the imports.

## The problem

Every Python project past ~5 files ends up with the same mess. File A imports a path from file B, file C hardcodes a different path, file D assumes the working directory, file E does its own config loading, and file F has no idea what file E decided. Nothing agrees on where things are, how things are loaded, or what things are called.

## The fix

A single coordination layer every file reads from. Two rules: before boot, register capabilities. After boot, registry is frozen and read-only for the entire run. No dependency injection. No plugin forest. No abstract factories.

## Install

```bash
pip install maelspine
```

## Quick start

```python
from spine import Core

c = Core()
c.register("paths.data", Path("./data").resolve())
c.register("paths.logs", Path("./logs").resolve())
c.register("db.backend", SQLiteBackend())
c.boot(env="dev")

data_dir = c.get("paths.data")    # always the same answer
backend  = c.get("db.backend")    # always the same instance
run_id   = c.context.run_id       # unique per run
```

After `boot()`, calling `register()` raises `CoreFrozen`. That's the entire point.

## Full documentation

Open `core.py`. The first 160 lines are a complete reference — API, design decisions, error types, hit counter usage, file layout, and future split strategy. All as comments. You can't miss it.

## Observer (fully detachable)

`observers.py` watches the core's hit counter and error diagnostics, then sends formatted messages through pluggable backends (Slack, WhatsApp, stdout, custom callbacks). The core has zero knowledge it exists. Delete the file and nothing breaks.

Open `observers.py` for its full inline documentation.

## File layout

```
spine/
├── __init__.py      re-exports (the stable contract)
├── core.py          Core, RunContext, errors, test harness
└── observers.py     detachable: Observer + backends
```

## License

MIT
