# ADR-006 — GitHub as the single project-management platform; Jira evaluated and not adopted

- **Status:** Accepted · **Date:** 2026-10-29 · **Owner:** P1 (Ankit)

## Context

The brief mandates Agile and names GitHub as the primary platform, while saying Jira may be
evaluated but execution must not depend on it.

## Decision

GitHub only: Issues for stories and tasks, labels for epic/owner/type/size, one Project board
(Backlog → Sprint → In Progress → In Review → Done), PRs for review, Discussions for
standups, and `docs/agile/sprint-N.md` for reviews and retrospectives. **Jira not adopted.**

## Consequences

- One source of truth. An issue id appears in the branch name, the commit trailer and the PR,
  so work is traceable from a line of code to a story.
- No cross-tool sync to maintain or to explain in the viva.
- We lose Jira-style burndown and velocity charts; velocity is tracked by hand in the sprint
  reports instead, which for a 4-person one-week project is less work than the integration.

## Note on this project's actual execution

The build ran as one compressed week (`scripts/TIMELINE.md`) rather than nine one-week
sprints. The backlog in `docs/phase-0/03-agile-backlog.md` is the planned structure and the
sprint reports must describe what actually happened, including the compression. Presenting the
nine-sprint plan as the real history would be a fabrication, and the sprint reports are
required to say so.
