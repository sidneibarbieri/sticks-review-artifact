# Procedural Measurement Boundary

This directory is the write surface for measurement code, tests, generated
outputs, and runtime scratch documentation.

The surrounding `sticks-docker/` tree is treated as frozen input. Measurement
scripts consume that input and write only under this boundary or a temporary
runtime directory.

## Scope

- `scripts/`: single-purpose measurement and replay orchestration code.
- `tests/`: unit tests for the measurement boundary.
- `results/`: generated outputs that support the study claims.
- `runtime/`: local scratch area for optional Docker replay preparation.

## Source-of-Truth Rule

If a number, table, or claim depends on the Docker-backed artifact semantics,
the code that produced it should live here. The artifact must validate released
results; it must not modify private writing files.
