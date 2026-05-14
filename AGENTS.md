# AGENTS.md

## Style

- No bar/section-divider comments (e.g. `# --- #`, `# ===`). Let structure speak for itself.

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
