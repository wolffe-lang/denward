# denward

A backup and restore tool in wolf for carrying personal data and system identity across a fresh PAX installation.

**Status: refusal-only command, internal archive framing and test-only codec.** No complete backup, keyed verification, receiver or restore operation is enabled. `version` and help work; every data operation still refuses before opening a source, destination or network connection. The internal [safe-object framing layer](docs/SAFE-OBJECT-FRAMING.md) borrows the pinned public paxage writer/reader and checks physical member shape and object digests; that is not logical-manifest verification or recoverability. An internal age v1 X25519 codec is reachable only through tests and a non-installed test driver. Independent reading identified required corrections; it is not qualified for real data, and real use remains blocked on wolf-std#151, requalification and controller review. **Do not use this version for a real backup**, to protect data or to authorize a reinstall.

The primary store is an SSH receiver on macOS arm64, reached through macOS's OpenSSH server, with an ordinary destination directory on an encrypted volume. The same endpoint will run on Linux. A separate physical disk holds the second verified copy. A successful SSH transfer alone will not establish a complete backup.

The pipeline is **archive → ordinary age v1 encryption → store**, initially native X25519 with two independently generated recovery identities. Public recipients go on PAX; private halves stay on the Mac and offline media. Encryption is the default selection, but its provider is unavailable in this scaffold. The held-local-media exception requires both `--plaintext` and `--ack-plaintext-owner-held`, and is never permitted over SSH. Every real primary-store backup is encrypted from its first stored byte. No cipher or encrypted container is invented here; first use waits for qualified entropy, independent review, interoperability and key-recovery rehearsal.

## Contract

- Preserve homes, account identity, selected persistent local data and manifest-derived configuration changes, not the old kernel or base filesystem.
- Restore onto a freshly installed, qualified journalled root in maintenance mode.
- Verify complete stored ciphertext against an independently held digest before any restore. Without a key this is integrity, not decryption or archive validation.
- With a key, additionally authenticate the encryption envelope and verify the complete archive and logical files before applying a declared restore plan.
- Show unsupported metadata and unresolved account/configuration choices by name; never silently omit them.
- Keep web hosting, same-disk partition preservation and installer integration out of the first implementation.

See [the implementation plan](docs/IMPLEMENTATION.md), [CLI](spec/cli-v1.md), [backup format](spec/backup-v1.md), [manifest](spec/manifest-v1.md), [stores](spec/stores-v1.md), [stream boundary](spec/stream-v1.md), [recovery](spec/restore-state-v1.md) and [compatibility](spec/compatibility-v1.md). The archive, command and store contracts are versioned; the ordinary age profile is defined in [encryption](spec/encryption-v1.md), not a custom envelope.

## Development

Supported initial hosts are x86-64 Linux and macOS arm64. Builds use the exact wolf, lupin and standard-library identities in `wolf-toolchain.toml` as one review set. Shipped denward binaries are release builds; the test-only codec runs rows in both default and release builds. Neither build has a timing certification. No global toolchain installation is needed. The codec's required independent reading and remaining claim limits are in [the review packet](docs/AGE-REVIEW.txt).

```sh
python3 tools/fetch-toolchain.py
python3 tools/gate.py --suite core
python3 tools/gate.py --suite native
```

`core` checks specifications, pins, publication boundaries, fixtures and failure witnesses without a compiler, including exact upstream archive provenance and corruption mutations. `native` builds the refusal shell with the pinned compiler, retains the codec's default/release gates and Linux admission/fuzz checks, and runs CLI and safe-object archive end-to-end rows in isolated fake fixtures. Archive rows include independent exact bytes, hostile physical members, source-digest failures, short/ragged input, backpressure and sink failures; both hosted platforms must pass. No production inventory capacity or encrypted backup is enabled. Every row names its outcome; missing required tools fail rather than pass as skipped work. PAX storage capability rows are opt-in and require an explicitly supplied, digest-pinned test ISO, an isolated Linux runner and throwaway images. They never inspect an installed machine.

The first hosted PR must exercise the workflow and its deliberate failing witness. A workflow that has not executed is unrun, not implicitly green. The refusal command has a 53-row CLI end-to-end matrix and separate pure-validation units. Native macOS/Linux execution and macOS's actual SSH receiver are distinct gates; a command build is not a receiver implementation.

Contributing rules and the clean-room boundary are in [CONTRIBUTING](CONTRIBUTING.md). No production credentials or personal data belong in fixtures.

## Licence

GPL-3.0-or-later with the additional [wolf Training Data Permission](LICENSE-TRAINING-DATA). The licence pair is copied byte-for-byte from the public warren repository; [provenance](docs/LICENSE-PROVENANCE.md) records its revision and hashes.
