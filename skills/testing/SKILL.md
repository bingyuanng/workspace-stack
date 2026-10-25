---
name: testing
description: Choose and write high-value tests when implementing behavior changes, fixing bugs, or reviewing tests. Prefer TDD and focused unit tests; avoid low-value coverage.
---

# Testing

Apply when changing behavior or designing and reviewing tests. Follow project
requirements and scale verification to the risk of the change.

- Prefer TDD for behavior changes: write a focused test, confirm it fails for the
  expected reason, implement the change, then refactor with tests passing. For a
  bug, reproduce it in a regression test before fixing it when practical.
- Prefer fast, focused unit tests for business logic. Add integration or
  end-to-end tests when the risk involves boundaries, persistence, wiring, or a
  user workflow that unit tests cannot adequately verify.
- Choose tests by the failures they can catch. Prioritize important behavior,
  realistic regressions, meaningful edge cases, and failure paths. Coverage
  numbers and test counts are not goals by themselves.
- Assert observable results and contracts. Tests should survive refactoring that
  preserves behavior. Avoid duplicating the implementation inside the test.
- Do not add low-value tests: trivial getters or assignments, framework behavior,
  assertions that only confirm a mock's configured return value, redundant cases,
  or snapshots that freeze incidental markup. Test these only when they protect a
  meaningful contract or known regression.
- Mock external or nondeterministic boundaries when needed. Avoid mocking the
  behavior under test or asserting internal call sequences unless the sequence
  is itself a requirement. Keep tests deterministic and independent.
- Follow the project's test framework and conventions. For documentation, copy,
  or other low-risk changes, use an appropriate check instead of forcing a new
  automated test.
- Run relevant tests and required project checks. Broaden testing when the
  change's risk or a failure warrants it. Report what ran and any verification
  gaps; do not claim success for tests that were not run.

High value: verify that an unauthorized request is rejected without changing
stored data, or that retrying a payment does not create a second charge.

Low value: verify that a private helper was called exactly once when its call
count has no effect on the required behavior.
