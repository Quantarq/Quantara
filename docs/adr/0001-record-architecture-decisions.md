# ADR-0001: Record Architecture Decisions

**Status:** Accepted

**Deciders:** Engineering Team

**Date:** 2026-06-17 (initial adoption)

## Context

The Quantara protocol has undergone significant architectural changes — migration from Starknet to Stellar, adoption of adapter patterns for blockchain integration, and selection of caching infrastructure — without any formal record of why these decisions were made. New contributors lack the context behind past decisions, creating risk that decisions will be unknowingly reversed or that onboarding will require excessive tribal knowledge transfer.

## Decision

We will document every architecturally significant decision using Michael Nygard's lightweight ADR format. Each ADR is a short markdown file capturing:

- **Title** — A short noun phrase describing the decision.
- **Status** — Proposed, Accepted, Deprecated, or Superseded.
- **Context** — The forces, constraints, and background that motivated the decision.
- **Decision** — The chosen approach.
- **Consequences** — The trade-offs, both positive and negative.

ADRs are stored in `docs/adr/` and numbered sequentially (`NNNN-descriptive-title.md`). A decision is "architecturally significant" when it affects the structure, non-functional properties, dependencies, interfaces, or construction techniques of the system.

## Consequences

**Positive:**

- New contributors can read the rationale behind past decisions without requiring verbal handoff.
- Decisions are explicitly revisited when their context changes; superseded ADRs are marked rather than lost.
- Reviewers have concrete context for evaluating whether a new proposal aligns with or intentionally diverges from prior decisions.

**Negative:**

- Requires discipline to write ADRs alongside the changes they describe.
- ADRs must be kept up to date; an abandoned ADR directory creates more confusion than none at all.

**Neutral:**

- ADRs document *why*, not *how* — implementation details live in code comments and READMEs.
