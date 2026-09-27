## 1. Regression Tests

- [x] 1.1 Add the six named deterministic M0 regression tests and confirm they expose the current defects.

## 2. Scientific Gate Corrections

- [x] 2.1 Preserve `KILL` for fatal plus human-review objections.
- [x] 2.2 Prevent non-continuation scientific decisions from entering the autonomous experiment program.

## 3. Evidence Semantics

- [x] 3.1 Implement four-state experiment evaluation with execution failures classified as `INVALID`.
- [x] 3.2 Propagate verdicts consistently through normal and ablation evidence graph paths and hypothesis evidence lists.

## 4. Boundary Repairs

- [x] 4.1 Validate path-form executables by resolved trusted identity while preserving supported commands.
- [x] 4.2 Preserve parsed arXiv authors and categories.

## 5. Verification and Reporting

- [x] 5.1 Run targeted M0 tests, compileall, the complete pytest suite, legacy regression scripts, and benchmark/discovery tests.
- [x] 5.2 Generate `reports/research_os_v2_m0_report.md` with actual results and validate the OpenSpec change.
- [x] 5.3 Review and commit only M0 changes on `research-os-v2`.
