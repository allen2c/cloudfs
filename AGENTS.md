# AGENTS.md

## Style

- No bar/section-divider comments (e.g. `# --- #`, `# ===`). Let structure speak for itself.
- Line length: 88 (Black default). Enforced by flake8 + isort via `pyproject.toml`.

## Code Organization

### File Structure Order

Follow this module-level layout order:

1. **Docstring** — module-level docstring at the top
2. **Imports** — standard lib → third-party → local
3. **Constants** — module-level constants and config values
4. **Public functions** — functions intended for external use
5. **Public classes** — classes intended for external use
6. **Private functions / classes** — prefixed with `_`, internal use only

### Boy Scout Rule

Leave the code cleaner than you found it. When touching a file, fix small issues nearby (naming, dead code, formatting) without scope-creeping into unrelated areas.

## Architecture

### CloudPath

`CloudPath` (exported as `Path`) is the abstract base for all backends. It:

- Dispatches to the correct backend via `__new__` based on URI scheme (`gs://`, etc.)
- Defines the full `pathlib.Path`-compatible interface as abstract methods
- Raises `CloudOperationError` for operations with no meaningful cloud equivalent (symlinks, chmod, cwd, etc.)

### Backends

Each backend lives in `cloudfs/backend/<name>.py` and subclasses `CloudPath`. Backends are responsible for their own implementation — no shared logic is forced at the base level.

Backend-specific caveats (e.g. GCS directory simulation) must be documented in the module docstring.

### Conformance Tests

`tests/conformance.py` defines the behavioral contract all backends must satisfy. To add a new backend test, subclass `CloudPathConformance` and provide a `root` fixture. Backend-specific tests go in a separate class in the same file.

## Design Principles

- **Interface consistency over implementation sharing** — backends implement the same contract independently; tests enforce consistency.
- **No silent failures** — unsupported operations raise `CloudOperationError` explicitly, never silently no-op.
- **pathlib parity** — the goal is that code written for `pathlib.Path` works with `CloudPath` without modification.
