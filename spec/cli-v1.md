# CLI v1

The current build is refusal-only: only help/version succeed. Data operations return a named unsupported outcome before opening any source, destination, identity or network connection. No successful verification is implemented.

```text
denward version | --version
denward help | --help
denward stores [--json]
denward store mount --device DEVICE --expect-serial SERIAL --at DIR [--read-only]
denward store unmount --at DIR
denward inspect --source ROOT [--baseline FILE] [--json]
denward backup --source ROOT --to STORE --offline [--format encrypted]
denward backup --source ROOT --to LOCAL_FILE --offline --plaintext --ack-plaintext-owner-held
denward verify FILE --expect-sha256 HEX [--expect-bytes N]
denward verify FILE --expect-sha256 HEX [--expect-bytes N] --decrypt (--identity FILE | --identity-fd FD)
denward list FILE --expect-sha256 HEX (--identity FILE | --identity-fd FD) [--json]
denward receive --directory DIR --id ID [--format encrypted]
denward receive --directory DIR --id ID --commit --expect-sha256 HEX --expect-bytes N
denward send --directory DIR --id ID [--receipt]
denward restore STORE --target ROOT --expect-sha256 HEX [--preview] [--decisions FILE] [--resume ID] [--identity-fd FD]
denward status [--target ROOT] [--json]
denward compare STORE --target ROOT --expect-sha256 HEX [--identity-fd FD]
```

STORE is a local file or `ssh:ALIAS/ID`. A trusted alias binds destination/user/port, strict host-key pin, identity reference and fixed endpoint/directory, never arbitrary shell. Backup recipients are public X25519 recipients, provisioned independently; private recovery identities stay off the source machine. Identity paths/descriptors may be arguments; their contents, passwords and phrases may not. The scaffold reads none of them. Passphrase mode is not part of the first release.

Ordinary binary age v1 with native X25519 recipients is the selected encrypted profile. Encryption is the default. `--format encrypted` selects it explicitly; no other format value is accepted in this scaffold. The exceptional local-media creation mode requires both `--plaintext` and `--ack-plaintext-owner-held`. An acknowledgement alone never changes the default. Plaintext is forbidden over SSH, including an encrypted-at-rest receiver volume. The receive endpoint rejects a plaintext request even with both flags. No automatic fallback or remote plaintext-then-encrypt operation exists.

Without `--decrypt`, verify checks only complete ciphertext identity and bounded syntax, with the eventual claim `ciphertext_verified; contents_not_checked`. Identity input without `--decrypt` is a usage error. With `--decrypt`, exactly one identity input is required, and the eventual successful claim is `contents_verified` only after full envelope/chunk/final-EOF and logical archive verification. Missing identity for decrypt/list refuses `identity-required`. No-key list never reveals inventory. Neither claim is implemented yet.

The receive endpoint's first phase creates uncommitted received state; commit binds stored ciphertext digest/length before publishing. `send --receipt` returns its bounded receipt; ordinary send returns raw complete ciphertext. No receiver holds a recovery identity. See stores-v1 and encryption-v1.

Options are command-specific and unique. Unknown/duplicate options, missing or empty values, unexpected operands and missing required options are usage errors; no argument values are echoed. `--` ends option parsing. There are at most 256 arguments and 4096 UTF-8 bytes per argument. HEX is exactly 64 lowercase hexadecimal characters. N/FD are canonical nonnegative decimal integers within signed 64-bit range; no overflowing arithmetic is evaluated. ID is 1–128 ASCII letters/digits/underscore/hyphen, starting with a letter/digit. A value beginning `--` is not consumed as an option value.

Exit codes: 0 complete; 1 I/O/integrity/validation failure; 2 usage/unsupported; 3 unresolved decisions; 4 interrupted/recovery required; 5 cancelled. No partial success is 0. Version is `denward 0.0.0-dev (refusal-only)` at this milestone.

A future restore first verifies the entire backup without target writes, previews and resolves choices, and confirms `RESTORE <backup-id> <target-identity> <plan-digest>`. The apply pass authenticates the stream again. Decisions are versioned data, not scripts. No force option bypasses integrity, confinement, identity or journal qualification.
