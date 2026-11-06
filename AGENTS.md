# AGENTS.md

Project overview is available in `README.md` and under `Documentation/`.

This project aims to be clean, elegant, modern, with security as a first-class
principle.

## General guidelines

- Make changes carefully with security hardening in mind.
- Do not add unnecessary features or useless/redundant code.
- We always target the latest software/system/tools.
- Do not preserve backward compatibility.
- Compatibility and migrations for persisted user data must be considered case by case
  with explicit approval. Any retained migration must be narrow, documented, and tested.
- Remove obsolete paths instead of adding compatibility layers, fallbacks, or
  migrations.
- Choose the simplest and cleanest implementation that fully meets the current
  requirements.
- Make architectural decisions for the long term. Do not accept a stopgap that
  only works for now.
- Avoid piling up hacks: always prefer a clean systemic fix.
- When asked to review, never make changes without explicit approval.

Exceptions to the following rules must be narrow, documented, and tested.

### Diagnostics

Project code must be usable without warnings and pass the configured lint. Warnings are errors. Do not disable diagnostics globally or use broad
suppressions. A local suppression must cover the smallest possible region,
explain why the operation is correct, and receive verification appropriate to
its risk.
