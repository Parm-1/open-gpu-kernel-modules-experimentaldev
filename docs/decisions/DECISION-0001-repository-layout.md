# DECISION-0001: repository layout

Status: Accepted — 2026-08-17

## Decision

Keep `main` aligned with NVIDIA release snapshots. Put research infrastructure, diagnostics, and implementation patches on narrow branches. Avoid unrelated refactoring so changes can be reviewed or upstreamed independently.

## Consequences

- The fork can be resynchronized with NVIDIA releases.
- Research documents may live beside source, but production-source edits remain separate commits and PRs.
- Generated artifacts and machine-specific logs are not committed unless intentionally reduced and redacted.
