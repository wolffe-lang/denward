# Contributing

Start from the implementation plan and write the expected behavior before changing it. Add tests with each feature. A failing row must be seen before its fix; keep deliberate breaks off the working branch. Use small unsigned commits with imperative messages and no attribution trailers.

All tracked text is suitable for public distribution: plain prose, no private repository identities, personal data, credentials, machine names or workstation-specific paths. Do not track local environment rules or machine configuration. Source files, tests, fixtures and specifications are the reviewable contract.

## Clean room

Use published specifications, manuals, public test-vector data and black-box interoperability runs. Never read the implementation of another backup tool, archiver, filesystem tool, kernel or encryption tool. The organization's own explicitly approved shared components can be audited for reuse at exact pins; an unpublished dependency is not named or copied into this tree before publication is confirmed. Do not derive expected outcomes from an implementation under test.

## Tests and safety

Unit tests are not sufficient. Keep CLI integration, native Linux/macOS endpoint tests, independent archive-format contrasts, QEMU file/disk tests and power-cut recovery tests as separate gates. A skipped row is not evidence that its capability works. Record every step's exit code. Fail missing prerequisites loudly.

Build from committed snapshots. Bound memory, CPU use and output before running size/fuzz workloads. Temporary fixtures belong in a caller-provided workspace, never a fixed system temporary path. Tests touch only files, devices, child processes and network fixtures that they created. A PAX capability test uses QEMU, never an installed machine. End only child processes owned by that test, by recorded pid, and wait for them.

Never expose a listener on a public interface for testing. Use throwaway credentials, prevent secret values from appearing in arguments, environment dumps or logs, and scan captures with independently generated sentinels. Do not weaken host-key verification to make an SSH test pass.

## Review

Changes to formats, pins, workflows or shared tooling are cross-cutting. A pull request identifies its footprint, commits and test checklist. A new workflow requires a real PR-event failing witness as well as its green run. Do not infer hosted results from local success. Keep the README's implemented/planned boundary current. No release, deployment or destructive hardware action is implied by merging code.
