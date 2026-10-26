# Viva Questions — P1 — Platform, API & Release Engineer

Target ≈13 of the team's 50. Write the answers **in your own words** after you have built the
thing. An answer copied from an AI is worth zero marks in the room.

Rehearsal rule: another team member quizzes you on these, and you get quizzed on *their*
module too. Gaps found there are the real audit.

1. Why Postgres with JSONB instead of a document store, or instead of normalising scores into tables?
2. Why 202 + polling for `/analyze` but synchronous `/verify`?
3. What exactly breaks if two modules import each other instead of importing `contracts`?
4. Walk through what happens when the NLI stage raises mid-run.
5. How does API versioning work here, and what would v2 change?
6. How are secrets handled, and prove nothing sensitive is in git history.
7. What does each CI job gate, and what happens on a failure?
8. How is SQL injection prevented, concretely, in this codebase?
9. Why rate limiting, and what limit did you pick and why?
10. What is in the error response, and what is deliberately absent?
11. How do migrations work and how would you roll one back?
12. Where is the orchestrator's state kept and why there?
13. What is the single biggest integration risk you managed, and how?

## Answers

(Fill in. One short paragraph each, plus the file you would open to show it.)
