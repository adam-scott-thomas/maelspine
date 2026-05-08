# maelspine — DEPRECATED

**Date deprecated:** 2026-05-08
**Final version:** 0.3.0
**Successor:** [`ghostspine`](https://github.com/adam-scott-thomas/ghostspine) (currently at 0.3.0)

## What happened

`maelspine` and `ghostspine` evolved as parallel names for the same package — both ship a top-level `spine/` module with byte-identical source. Installing both into the same environment causes a directory collision on `spine/`. To resolve the namespace fungus, the GhostLogic SDK has standardized on **ghostspine** as canonical.

## What this means for you

- **Existing installs of `maelspine` ≤ 0.3.0 keep working.** No yank, no breakage.
- **`maelspine` will not be released past 0.3.0.** No 0.3.1, no 1.0.0.
- **New projects should `pip install ghostspine`** and import from `spine` exactly as before — the public API is identical.
- **Existing projects** can migrate by changing only their dependency pin: `maelspine>=X` → `ghostspine>=0.3.0`. Imports (`from spine import ...`) need no changes.

## Internal consumers migrated 2026-05-08

These packages migrated their pyproject.toml dependency from `maelspine` to `ghostspine`:

- ghostpipe
- ghostprompt
- ghostrouter
- ghostseal

Out-of-family consumers still on `maelspine` as of 2026-05-08 (not migrated by this commit):

- ghostjury (orphaned — no git remote, see workspace memory)
- mcpghost
- maelstrom-heavy-proto
- proofofaiwork-v4
- transcript-pipeline

These will install fine against `maelspine` 0.3.0 indefinitely; they should migrate at their own next release cycle.

## If you need to install both

You can't. Both ship the same top-level `spine/` package and pip will install whichever you ask for last (or fail, depending on resolver order). Pick `ghostspine`.
