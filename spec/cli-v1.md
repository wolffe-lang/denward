# CLI v1

This is the command grammar. The current build is refusal-only: only help/version succeed; every data operation returns 2 with a named unsupported capability before I/O. It does not claim to have validated an archive or destination.

```text
denward version | --version
denward help | --help
denward stores [--json]
denward store mount --device DEVICE --expect-serial SERIAL --at DIR [--read-only]
denward store unmount --at DIR
denward inspect --source ROOT [--baseline FILE] [--json]
denward backup --source ROOT --to STORE --offline [--format encrypted]
denward backup --source ROOT --to STORE --offline --format plaintext --ack-plaintext-owner-held
denward verify FILE --expect-sha256 HEX [--expect-bytes N] [--identity-fd FD]
denward list FILE --expect-sha256 HEX [--identity-fd FD] [--json]
denward receive --directory DIR --id ID
denward receive --directory DIR --id ID --commit --expect-sha256 HEX --expect-bytes N
denward send --directory DIR --id ID [--receipt]
denward restore STORE --target ROOT --expect-sha256 HEX [--preview] [--decisions FILE] [--resume ID] [--identity-fd FD]
denward status [--target ROOT] [--json]
denward compare STORE --target ROOT --expect-sha256 HEX [--identity-fd FD]
```

STORE is a local file or `ssh:ALIAS/ID`. A configured SSH alias binds destination, user, host-key pin, identity reference and fixed endpoint path; it is not arbitrary shell. Key bytes, passwords and passphrases are never arguments. FD is a nonnegative decimal descriptor, not secret material. The separately specified encryption provider determines the private key/prompt flow. The scaffold never reads that descriptor.

Encryption is selected when `--format` is absent. No `auto` mode or failed-encryption plaintext fallback exists. Plaintext requires both explicit `--format plaintext` and `--ack-plaintext-owner-held`. The acknowledgement without explicit plaintext is a usage error. Missing encryption support is a named refusal before archive or store work.

The receive endpoint's first phase creates only uncommitted received state; `--commit` binds the locally computed stored-byte digest and length before publishing. `send --receipt` returns the bounded receipt; ordinary `send` returns raw stored bytes. The store protocol is in stores-v1. None of these phases is implemented yet.

Options are command-specific, unique and never silently ignored. Values must be nonempty. Unknown options, duplicate options, missing values, unexpected operands or missing required options are usage errors. `--` ends option parsing; operands beginning `--` then remain operands. Limits: at most 256 arguments, each at most 4096 UTF-8 bytes. HEX is exactly 64 lowercase hexadecimal characters. N/FD are canonical nonnegative decimal integers within signed 64-bit range; zero is permitted and no overflow is evaluated. ID is 1–128 ASCII letters/digits/underscore/hyphen, starting with a letter/digit; ALIAS is selected from trusted configuration, not evaluated as a URL or shell string.

Exit codes: 0 complete; 1 I/O/integrity/validation failure; 2 usage/unsupported; 3 unresolved decisions; 4 interrupted/recovery required; 5 cancelled. No partial success is encoded as 0. Diagnostics use fixed reason names and never echo argument values. Version is `denward 0.0.0-dev (refusal-only)` at this milestone. Help explicitly says data operations are unsupported.

A future ordinary restore verifies, previews decisions and confirms `RESTORE <backup-id> <target-identity> <plan-digest>` before applying. `--preview` writes no target state. Decisions are versioned data bound to those identities, not scripts. No force option bypasses integrity, confinement or journal qualification.
