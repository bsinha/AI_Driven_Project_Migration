# EuroSA Bank — Problem Statement

## Context

EuroSA Bank is a European bank with retail operations in South Africa. Its systems were decomposed into **granular microservices** along technical lines rather than business capabilities (bounded contexts).

## Problem

- High coupling between fine-grained services (e.g. five customer services sharing one database)
- Synchronous call chains spanning 6+ services for a single payment
- Poor cohesion: lifecycle and domain rules split across services
- False cohesion: services sharing "customer" in the name but belonging to different domains

## Objective

Build an **AI-assisted migration framework** that:

1. Collects architectural evidence (code, APIs, DB, traces, teams)
2. Diagnoses smells deterministically
3. Proposes bounded contexts with evidence and confidence
4. Requires human validation before migration planning
5. Guides developers through manual migration (no auto-merge)

## Thesis

> Technology-oriented decomposition → business-capability-oriented decomposition

Evidence → Hypothesis → Recommendation → Human validation → Migration
